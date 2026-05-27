"""
Modeles de l'app referentiels — UCAO-ISG-CSM.

Quatre entites principales :
- Article         : produits/biens commandables (avec image)
- ServiceExterieur: prestations externes
- Fournisseur     : entreprises fournissant articles ou services
- Devise          : monnaies + taux TVA
"""
from django.conf import settings
from django.db import models
from django.utils.text import slugify

from .managers import (
    ArticleManager,
    DeviseManager,
    FournisseurManager,
    ServiceExterieurManager,
)


# ═══════════════════════════════════════════════════════════════════
# ENUMERATIONS
# ═══════════════════════════════════════════════════════════════════
class UniteArticle(models.TextChoices):
    """Unites de mesure d'un article."""

    UNITE = "unite", "Unite"
    PIECE = "piece", "Piece"
    KILO = "kilo", "Kilogramme (kg)"
    LITRE = "litre", "Litre (L)"
    METRE = "metre", "Metre (m)"
    METRE_CARRE = "metre_carre", "Metre carre (m²)"
    BOITE = "boite", "Boite"
    PAQUET = "paquet", "Paquet"
    LOT = "lot", "Lot"
    HEURE = "heure", "Heure"


class NatureArticle(models.TextChoices):
    """Nature/famille d'un article."""

    FOURNITURE_BUREAU = "fourniture_bureau", "Fourniture de bureau"
    EQUIPEMENT_INFO = "equipement_info", "Equipement informatique"
    MOBILIER = "mobilier", "Mobilier"
    CONSOMMABLE = "consommable", "Consommable"
    MATERIEL_TECH = "materiel_tech", "Materiel technique"
    PRODUIT_ENTRETIEN = "produit_entretien", "Produit d'entretien"
    AUTRE = "autre", "Autre"


class TypePersonneFournisseur(models.TextChoices):
    """Type juridique du fournisseur."""

    PHYSIQUE = "physique", "Personne physique"
    MORALE = "morale", "Personne morale"


# ═══════════════════════════════════════════════════════════════════
# ARTICLE — CHEMIN D'IMAGE
# ═══════════════════════════════════════════════════════════════════
def chemin_image_article(instance, nom_fichier):
    """
    Genere le chemin de stockage d'une image d'article.

    Format : articles/<designation-slugifiee>.<extension>
    Exemple : articles/ramette-papier-a4.png
    """
    extension = nom_fichier.split(".")[-1].lower()
    nom_propre = slugify(instance.designation)[:50] or "article"
    return f"articles/{nom_propre}.{extension}"


# ═══════════════════════════════════════════════════════════════════
# ARTICLE
# ═══════════════════════════════════════════════════════════════════
class Article(models.Model):
    """
    Article catalogable et commandable via FEB.

    Regle metier : un article reference dans une FEB ne peut etre
    supprime physiquement (controle dans les vues + admin).
    """

    designation = models.CharField(
        max_length=200,
        unique=True,
        verbose_name="Designation",
        help_text="Nom unique de l'article",
    )
    unite = models.CharField(
        max_length=20,
        choices=UniteArticle.choices,
        default=UniteArticle.UNITE,
        verbose_name="Unite de mesure",
    )
    nature = models.CharField(
        max_length=30,
        choices=NatureArticle.choices,
        default=NatureArticle.AUTRE,
        verbose_name="Nature",
        db_index=True,
    )
    description = models.TextField(
        blank=True, default="",
        verbose_name="Description complementaire",
    )
    image = models.ImageField(
        upload_to=chemin_image_article,
        blank=True, null=True,
        verbose_name="Image de l'article",
        help_text="Format JPG, PNG ou WebP. Max 5 Mo.",
    )
    est_actif = models.BooleanField(
        default=True,
        verbose_name="Actif",
        help_text="Faux = article retire du catalogue (suppression logique).",
    )

    # ═══════════════════════════════════════════════════════════════
    # GESTION DE STOCK
    # ═══════════════════════════════════════════════════════════════
    gestion_stock_active = models.BooleanField(
        default=False,
        verbose_name="Gestion stock activee",
        help_text="Si False, l'article n'est pas gere en stock (services, equipements uniques)",
    )

    quantite_stock = models.IntegerField(
        default=0,
        verbose_name="Quantite en stock",
    )

    seuil_alerte = models.IntegerField(
        default=0,
        verbose_name="Seuil d'alerte",
        help_text="Si quantite_stock <= seuil_alerte, alerte declenchee",
    )

    quantite_a_commander = models.IntegerField(
        default=0,
        verbose_name="Quantite a commander",
        help_text="Quantite suggeree lors d'une commande automatique",
    )

    derniere_alerte = models.DateTimeField(
        null=True, blank=True,
        help_text="Derniere fois qu'une alerte a ete declenchee (evite spam)",
    )

    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="articles_crees",
        verbose_name="Cree par",
    )
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de creation",
    )
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name="Date de derniere modification",
    )

    objects = ArticleManager()

    class Meta:
        db_table = "article"
        verbose_name = "Article"
        verbose_name_plural = "Articles"
        ordering = ["designation"]
        indexes = [
            models.Index(fields=["nature", "est_actif"]),
            models.Index(fields=["designation"]),
        ]

    def __str__(self):
        return f"{self.designation} ({self.get_unite_display()})"

    @property
    def url_image(self):
        """Retourne l'URL de l'image, ou None si absente."""
        if self.image and hasattr(self.image, "url"):
            try:
                return self.image.url
            except ValueError:
                return None
        return None


    @property
    def est_en_rupture(self):
        """True si le stock est a zero."""
        return self.gestion_stock_active and self.quantite_stock <= 0

    @property
    def est_sous_seuil(self):
        """True si le stock est en dessous du seuil d'alerte."""
        return (
            self.gestion_stock_active
            and self.seuil_alerte > 0
            and self.quantite_stock <= self.seuil_alerte
        )

    @property
    def statut_stock(self):
        """Retourne 'rupture', 'sous_seuil', 'ok' ou 'non_geres'."""
        if not self.gestion_stock_active:
            return "non_geres"
        if self.est_en_rupture:
            return "rupture"
        if self.est_sous_seuil:
            return "sous_seuil"
        return "ok"

    @property
    def couleur_stock(self):
        """Couleur badge selon le statut de stock."""
        return {
            "rupture": "error",
            "sous_seuil": "warning",
            "ok": "success",
            "non_geres": "neutre",
        }.get(self.statut_stock, "neutre")


# ═══════════════════════════════════════════════════════════════════
# SERVICE EXTERIEUR
# ═══════════════════════════════════════════════════════════════════
class ServiceExterieur(models.Model):
    """Prestation/service externe (entretien, transport, conseil...)."""

    designation = models.CharField(
        max_length=200,
        unique=True,
        verbose_name="Designation du service",
    )
    description = models.TextField(
        blank=True, default="",
        verbose_name="Description detaillee",
    )
    est_actif = models.BooleanField(
        default=True,
        verbose_name="Actif",
    )

    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="services_crees",
        verbose_name="Cree par",
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    objects = ServiceExterieurManager()

    class Meta:
        db_table = "service_exterieur"
        verbose_name = "Service exterieur"
        verbose_name_plural = "Services exterieurs"
        ordering = ["designation"]

    def __str__(self):
        return self.designation


# ═══════════════════════════════════════════════════════════════════
# FOURNISSEUR
# ═══════════════════════════════════════════════════════════════════
class Fournisseur(models.Model):
    """
    Entreprise ou personne fournissant articles ou services.

    Code automatique au format F0001 (cf. signal pre_save).
    Le code n'est jamais modifiable apres creation.
    """

    code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name="Code fournisseur",
        help_text="Genere automatiquement (F0001, F0002...).",
        editable=False,
    )
    nom = models.CharField(
        max_length=200,
        verbose_name="Nom / Raison sociale",
    )
    type_personne = models.CharField(
        max_length=10,
        choices=TypePersonneFournisseur.choices,
        default=TypePersonneFournisseur.MORALE,
        verbose_name="Type de personne",
    )
    telephone = models.CharField(
        max_length=20,
        blank=True, default="",
        verbose_name="Telephone",
    )
    email = models.EmailField(
        blank=True, default="",
        verbose_name="Email",
        help_text="Utilise pour l'envoi des Bons de Commande.",
    )
    adresse = models.TextField(
        blank=True, default="",
        verbose_name="Adresse postale",
    )
    ninea = models.CharField(
        max_length=50,
        blank=True, default="",
        verbose_name="NINEA",
        help_text="Numero d'Identification Nationale des Entreprises et Associations.",
    )
    rccm = models.CharField(
        max_length=50,
        blank=True, default="",
        verbose_name="RCCM",
        help_text="Registre du Commerce et du Credit Mobilier.",
    )
    est_actif = models.BooleanField(
        default=True,
        verbose_name="Actif",
    )

    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="fournisseurs_crees",
        verbose_name="Cree par",
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    objects = FournisseurManager()

    class Meta:
        db_table = "fournisseur"
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["nom"]),
            models.Index(fields=["est_actif"]),
        ]

    def __str__(self):
        return f"{self.code} — {self.nom}"


# ═══════════════════════════════════════════════════════════════════
# DEVISE
# ═══════════════════════════════════════════════════════════════════
class Devise(models.Model):
    """
    Devise et taux TVA — gestion exclusive DFC.

    Au Senegal, TVA autorisees : 0%, 10%, 18%.
    """

    code = models.CharField(
        max_length=5,
        unique=True,
        verbose_name="Code ISO",
        help_text="Ex : XOF, EUR, USD",
    )
    libelle = models.CharField(
        max_length=100,
        verbose_name="Libelle",
        help_text="Ex : Franc CFA BCEAO",
    )
    symbole = models.CharField(
        max_length=10,
        blank=True, default="",
        verbose_name="Symbole",
        help_text="Ex : F CFA, €, $",
    )
    taux_tva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=18.00,
        verbose_name="Taux TVA applicable (%)",
        help_text="Taux Senegal autorises : 0, 10, 18.",
    )
    est_devise_principale = models.BooleanField(
        default=False,
        verbose_name="Devise principale",
        help_text="Une seule devise peut etre principale.",
    )
    est_active = models.BooleanField(
        default=True,
        verbose_name="Active",
    )

    gere_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="devises_gerees",
        verbose_name="Geree par (DFC)",
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    objects = DeviseManager()

    class Meta:
        db_table = "devise"
        verbose_name = "Devise"
        verbose_name_plural = "Devises"
        ordering = ["-est_devise_principale", "code"]

    def __str__(self):
        return f"{self.code} ({self.libelle}) — TVA {self.taux_tva}%"