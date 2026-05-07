"""
Modeles de l'app approvisionnements — FEB / BC / Paiements.

Workflow :
    FEB DRAFT -> EN_INSTANCE -> VALIDEE (>50k) -> BC genere -> VALIDE -> Paiement
                                CLOTUREE (<=50k, signature physique)

Numerotation : FEB-AAAA-NNNN, BC-AAAA-NNNN.
"""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.referentiels.models import Article, Fournisseur, ServiceExterieur

from .managers import (
    BonCommandeManager,
    FicheExpressionManager,
    LigneFicheManager,
)


# ═══════════════════════════════════════════════════════════════════
# ENUMERATIONS
# ═══════════════════════════════════════════════════════════════════
class StatutFEB(models.TextChoices):
    """Statuts du workflow FEB."""

    DRAFT = "DRAFT", "Brouillon"
    EN_INSTANCE = "EN_INSTANCE", "En instance"
    VALIDEE = "VALIDEE", "Validee"
    MODIFIEE = "MODIFIEE", "Modifiee"
    REJETEE = "REJETEE", "Rejetee"
    SUPPRIMEE = "SUPPRIMEE", "Supprimee"
    CLOTUREE = "CLOTUREE", "Cloturee"


class StatutBC(models.TextChoices):
    """Statuts du workflow Bon de Commande."""

    EN_INSTANCE = "EN_INSTANCE", "En instance"
    VALIDE = "VALIDE", "Valide"
    SUPPRIME = "SUPPRIME", "Supprime"


class StatutOrdrePaiement(models.TextChoices):
    """Statuts de l'ordre de paiement."""

    EN_ATTENTE_VISA = "EN_ATTENTE_VISA", "En attente du visa DG"
    VISA_OK = "VISA_OK", "Visa accorde"
    REJETE_DG = "REJETE_DG", "Rejete par DG"


class StatutPaiement(models.TextChoices):
    """Statuts du paiement final."""

    EN_ATTENTE = "EN_ATTENTE", "En attente d'execution"
    ACOMPTE = "ACOMPTE", "Acompte verse"
    PAYE = "PAYE", "Paye integralement"
    REJETE = "REJETE", "Rejete (montant incorrect)"


class ModePaiement(models.TextChoices):
    """Mode de paiement."""

    ESPECES = "ESPECES", "Especes"
    CHEQUE = "CHEQUE", "Cheque"
    VIREMENT = "VIREMENT", "Virement bancaire"
    MOBILE_MONEY = "MOBILE_MONEY", "Mobile Money (Orange/Wave)"


class NaturePaiement(models.TextChoices):
    """Nature du paiement."""

    INTEGRAL = "INTEGRAL", "Paiement integral"
    ACOMPTE = "ACOMPTE", "Acompte"
    SOLDE = "SOLDE", "Solde"


class OrigineFEB(models.TextChoices):
    """Origine de creation d'une FEB."""

    MANUELLE = "MANUELLE", "Saisie manuelle"
    PREDICTION = "PREDICTION", "Generation automatique (prediction)"


class TypeLigne(models.TextChoices):
    """Une ligne de FEB peut concerner un Article ou un Service."""

    ARTICLE = "ARTICLE", "Article"
    SERVICE = "SERVICE", "Service"


# ═══════════════════════════════════════════════════════════════════
# FICHE D'EXPRESSION DES BESOINS (FEB)
# ═══════════════════════════════════════════════════════════════════
class FicheExpression(models.Model):
    """Fiche d'Expression des Besoins (FEB)."""

    numero = models.CharField(max_length=20, unique=True, editable=False)
    objet = models.CharField(max_length=255)

    demandeur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="feb_demandees",
    )
    fournisseur = models.ForeignKey(
        Fournisseur,
        on_delete=models.PROTECT,
        related_name="feb_recues",
    )
    validateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="feb_validees",
        null=True, blank=True,
    )

    statut = models.CharField(
        max_length=20,
        choices=StatutFEB.choices,
        default=StatutFEB.DRAFT,
        db_index=True,
    )
    origine = models.CharField(
        max_length=20,
        choices=OrigineFEB.choices,
        default=OrigineFEB.MANUELLE,
    )
    est_auto = models.BooleanField(default=False)

    montant_ht = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    taux_tva = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("18.00"))
    montant_tva = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    montant_ttc = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    motif_action = models.TextField(blank=True, default="")
    est_supprimee = models.BooleanField(default=False, db_index=True)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    date_suppression = models.DateTimeField(null=True, blank=True)

    objects = FicheExpressionManager()

    class Meta:
        db_table = "fiche_expression"
        verbose_name = "FEB"
        verbose_name_plural = "FEB"
        ordering = ["-date_creation"]
        indexes = [
            models.Index(fields=["statut", "est_supprimee"]),
            models.Index(fields=["demandeur", "statut"]),
            models.Index(fields=["fournisseur"]),
            models.Index(fields=["-date_creation"]),
        ]

    def __str__(self):
        return f"{self.numero} — {self.objet[:40]}"

    def calculer_totaux(self, sauvegarder=True):
        total_ht = sum(
            (ligne.montant_ligne for ligne in self.lignes.all()),
            Decimal("0.00"),
        )
        self.montant_ht = total_ht
        self.montant_tva = (total_ht * self.taux_tva / Decimal("100")).quantize(
            Decimal("0.01")
        )
        self.montant_ttc = self.montant_ht + self.montant_tva

        if sauvegarder:
            self.save(update_fields=["montant_ht", "montant_tva", "montant_ttc"])

    @property
    def est_au_dela_du_seuil(self):
        seuil = Decimal(str(getattr(settings, "SEUIL_BC_AUTOMATIQUE", 50000)))
        return self.montant_ttc > seuil

    @property
    def peut_etre_validee(self):
        return self.statut == StatutFEB.EN_INSTANCE

    @property
    def peut_etre_modifiee(self):
        return self.statut in (
            StatutFEB.DRAFT, StatutFEB.EN_INSTANCE, StatutFEB.MODIFIEE,
        )

    @property
    def couleur_statut(self):
        return {
            StatutFEB.DRAFT: "neutre",
            StatutFEB.EN_INSTANCE: "warning",
            StatutFEB.VALIDEE: "success",
            StatutFEB.MODIFIEE: "info",
            StatutFEB.REJETEE: "error",
            StatutFEB.SUPPRIMEE: "neutre",
            StatutFEB.CLOTUREE: "success",
        }.get(self.statut, "neutre")


# ═══════════════════════════════════════════════════════════════════
# LIGNE DE FEB
# ═══════════════════════════════════════════════════════════════════
class LigneFiche(models.Model):
    """Ligne de detail d'une FEB."""

    fiche = models.ForeignKey(
        FicheExpression,
        on_delete=models.CASCADE,
        related_name="lignes",
    )
    type_ligne = models.CharField(max_length=10, choices=TypeLigne.choices)
    article = models.ForeignKey(
        Article, on_delete=models.PROTECT,
        related_name="lignes_feb", null=True, blank=True,
    )
    service = models.ForeignKey(
        ServiceExterieur, on_delete=models.PROTECT,
        related_name="lignes_feb", null=True, blank=True,
    )
    designation_libre = models.CharField(max_length=255, blank=True, default="")
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=2)
    montant_ligne = models.DecimalField(max_digits=14, decimal_places=2)

    objects = LigneFicheManager()

    class Meta:
        db_table = "ligne_fiche"
        verbose_name = "Ligne de FEB"
        verbose_name_plural = "Lignes de FEB"
        ordering = ["id"]

    def __str__(self):
        return f"{self.designation} — {self.quantite} x {self.prix_unitaire}"

    @property
    def designation(self):
        if self.article:
            return self.article.designation
        if self.service:
            return self.service.designation
        return self.designation_libre or "—"

    def clean(self):
        super().clean()
        if self.type_ligne == TypeLigne.ARTICLE and not (self.article or self.designation_libre):
            raise ValidationError({"article": "Selectionner un article ou saisir une designation libre."})
        if self.type_ligne == TypeLigne.SERVICE and not (self.service or self.designation_libre):
            raise ValidationError({"service": "Selectionner un service ou saisir une designation libre."})
        if self.quantite is not None and self.quantite <= 0:
            raise ValidationError({"quantite": "La quantite doit etre superieure a 0."})
        if self.prix_unitaire is not None and self.prix_unitaire < 0:
            raise ValidationError({"prix_unitaire": "Le prix unitaire ne peut etre negatif."})

    def save(self, *args, **kwargs):
        self.montant_ligne = (
            Decimal(str(self.quantite or 0)) * Decimal(str(self.prix_unitaire or 0))
        ).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════════
# BON DE COMMANDE (BC)
# ═══════════════════════════════════════════════════════════════════
class BonCommande(models.Model):
    """
    Bon de Commande genere automatiquement depuis une FEB validee > 50 000 F.

    Numerotation : BC-AAAA-NNNN (ex : BC-2025-0001).

    Regles metier :
    - Genere via @transaction.atomic depuis la validation FEB
    - Verrouille des creation (est_verrouille=True) : aucune modification metier
    - Validation par DG (ou DFC en PO si DG absent : signe_en_po=True)
    - Suppression logique uniquement
    """

    numero = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name="Numero de BC",
    )

    fiche = models.OneToOneField(
        FicheExpression,
        on_delete=models.PROTECT,
        related_name="bon_commande",
        verbose_name="FEB liee",
    )
    fournisseur = models.ForeignKey(
        Fournisseur,
        on_delete=models.PROTECT,
        related_name="bc_recus",
        verbose_name="Fournisseur",
    )

    statut = models.CharField(
        max_length=15,
        choices=StatutBC.choices,
        default=StatutBC.EN_INSTANCE,
        db_index=True,
    )

    montant_ht = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    taux_tva = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("18.00"))
    montant_tva = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    montant_ttc = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    validateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bc_valides",
        null=True, blank=True,
        verbose_name="Validateur (DG ou DFC en PO)",
    )
    signe_en_po = models.BooleanField(
        default=False,
        verbose_name="Signe en Pour Ordre (DFC pour DG)",
        help_text="True si le DFC a signe a la place du DG.",
    )

    est_verrouille = models.BooleanField(
        default=True,
        verbose_name="Verrouille",
        help_text="True : champs metier non modifiables.",
    )
    est_envoye_fournisseur = models.BooleanField(
        default=False,
        verbose_name="BC envoye au fournisseur",
    )
    date_envoi_fournisseur = models.DateTimeField(null=True, blank=True)

    motif_suppression = models.TextField(blank=True, default="")
    est_supprime = models.BooleanField(default=False, db_index=True)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    date_suppression = models.DateTimeField(null=True, blank=True)

    objects = BonCommandeManager()

    class Meta:
        db_table = "bon_commande"
        verbose_name = "Bon de Commande"
        verbose_name_plural = "Bons de Commande"
        ordering = ["-date_creation"]
        indexes = [
            models.Index(fields=["statut", "est_supprime"]),
            models.Index(fields=["fournisseur"]),
            models.Index(fields=["-date_creation"]),
        ]

    def __str__(self):
        return f"{self.numero} — {self.fournisseur.nom}"

    @property
    def peut_etre_valide(self):
        """Vrai si le BC peut passer EN_INSTANCE -> VALIDE."""
        return self.statut == StatutBC.EN_INSTANCE and not self.est_supprime

    @property
    def peut_etre_supprime(self):
        """Vrai si le BC peut etre supprime (logique)."""
        return not self.est_supprime and self.statut != StatutBC.VALIDE

    @property
    def couleur_statut(self):
        """Badge CSS associe au statut."""
        return {
            StatutBC.EN_INSTANCE: "warning",
            StatutBC.VALIDE: "success",
            StatutBC.SUPPRIME: "neutre",
        }.get(self.statut, "neutre")

    @property
    def lignes(self):
        """Lignes du BC = lignes de la FEB liee (relation indirecte)."""
        return self.fiche.lignes.all()
    

# ═══════════════════════════════════════════════════════════════════
# ORDRE DE PAIEMENT (DFC ordonne, DG vise)
# ═══════════════════════════════════════════════════════════════════
class OrdrePaiement(models.Model):
    """
    Ordre de paiement emis par le DFC, vise par le DG.

    Workflow : EN_ATTENTE_VISA -> VISA_OK / REJETE_DG
    """

    numero = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name="Numero ordre de paiement",
    )

    bc = models.ForeignKey(
        BonCommande,
        on_delete=models.PROTECT,
        related_name="ordres_paiement",
        verbose_name="Bon de Commande",
    )

    dfc = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ordres_emis",
        verbose_name="DFC emetteur",
    )

    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Montant a payer",
    )

    nature = models.CharField(
        max_length=15,
        choices=NaturePaiement.choices,
        default=NaturePaiement.INTEGRAL,
    )

    mode = models.CharField(
        max_length=15,
        choices=ModePaiement.choices,
        default=ModePaiement.VIREMENT,
    )

    statut = models.CharField(
        max_length=20,
        choices=StatutOrdrePaiement.choices,
        default=StatutOrdrePaiement.EN_ATTENTE_VISA,
        db_index=True,
    )

    motif = models.TextField(
        blank=True, default="",
        help_text="Motif de l'ordre (ou motif de rejet si statut REJETE_DG).",
    )

    # Visa DG
    dg = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="visas_donnes",
        null=True, blank=True,
        verbose_name="DG visa",
    )
    date_visa = models.DateTimeField(null=True, blank=True)

    # Horodatage
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ordre_paiement"
        verbose_name = "Ordre de paiement"
        verbose_name_plural = "Ordres de paiement"
        ordering = ["-date_creation"]
        indexes = [
            models.Index(fields=["statut"]),
            models.Index(fields=["bc"]),
            models.Index(fields=["-date_creation"]),
        ]

    def __str__(self):
        return f"{self.numero} — {self.bc.numero} ({self.montant} F)"

    @property
    def couleur_statut(self):
        return {
            StatutOrdrePaiement.EN_ATTENTE_VISA: "warning",
            StatutOrdrePaiement.VISA_OK: "success",
            StatutOrdrePaiement.REJETE_DG: "error",
        }.get(self.statut, "neutre")

    @property
    def peut_etre_vise(self):
        return self.statut == StatutOrdrePaiement.EN_ATTENTE_VISA


# ═══════════════════════════════════════════════════════════════════
# PAIEMENT (Comptable execute)
# ═══════════════════════════════════════════════════════════════════
class Paiement(models.Model):
    """
    Paiement execute par le Comptable apres visa DG.

    Verification automatique : montant_verse <= bc.montant_ttc
    Calcul automatique : solde_restant = bc.montant_ttc - somme_payee
    """

    numero = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name="Numero de paiement",
    )

    bc = models.ForeignKey(
        BonCommande,
        on_delete=models.PROTECT,
        related_name="paiements",
        verbose_name="Bon de Commande",
    )

    ordre = models.ForeignKey(
        OrdrePaiement,
        on_delete=models.PROTECT,
        related_name="paiements",
        verbose_name="Ordre de paiement lie",
    )

    comptable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="paiements_executes",
        verbose_name="Comptable executeur",
    )

    montant_verse = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Montant verse",
    )

    nature = models.CharField(
        max_length=15,
        choices=NaturePaiement.choices,
        default=NaturePaiement.INTEGRAL,
    )

    mode = models.CharField(
        max_length=15,
        choices=ModePaiement.choices,
        default=ModePaiement.VIREMENT,
    )

    reference = models.CharField(
        max_length=100,
        blank=True, default="",
        help_text="N° cheque, ID transaction, ref virement, etc.",
    )

    est_acompte = models.BooleanField(default=False)

    solde_restant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Solde restant a payer (calcule auto).",
    )

    statut = models.CharField(
        max_length=15,
        choices=StatutPaiement.choices,
        default=StatutPaiement.EN_ATTENTE,
        db_index=True,
    )

    motif_rejet = models.TextField(blank=True, default="")

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    date_execution = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "paiement"
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ["-date_creation"]
        indexes = [
            models.Index(fields=["statut"]),
            models.Index(fields=["bc"]),
            models.Index(fields=["-date_creation"]),
        ]

    def __str__(self):
        return f"{self.numero} — {self.bc.numero} ({self.montant_verse} F)"

    @property
    def couleur_statut(self):
        return {
            StatutPaiement.EN_ATTENTE: "warning",
            StatutPaiement.ACOMPTE: "info",
            StatutPaiement.PAYE: "success",
            StatutPaiement.REJETE: "error",
        }.get(self.statut, "neutre")

    @property
    def total_deja_paye(self):
        """Somme des paiements PAYE/ACOMPTE pour ce BC (hors le paiement courant)."""
        from django.db.models import Sum

        return (
            Paiement.objects
            .filter(bc=self.bc)
            .exclude(pk=self.pk)
            .filter(statut__in=[StatutPaiement.PAYE, StatutPaiement.ACOMPTE])
            .aggregate(total=Sum("montant_verse"))["total"]
            or Decimal("0.00")
        )