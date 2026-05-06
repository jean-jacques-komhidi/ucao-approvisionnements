"""
Modeles de l'app approvisionnements — FEB / BC / Paiements.

Ce module contient le coeur metier du systeme :
- FicheExpression : Fiche d'Expression des Besoins (FEB)
- LigneFiche      : ligne de detail d'une FEB (Article ou Service)

La FEB suit le workflow :
    DRAFT -> EN_INSTANCE -> VALIDEE / MODIFIEE / REJETEE / SUPPRIMEE

Numerotation automatique : FEB-AAAA-NNNN (ex : FEB-2025-0001).
"""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.referentiels.models import Article, Fournisseur, ServiceExterieur

from .managers import FicheExpressionManager, LigneFicheManager


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
    CLOTUREE = "CLOTUREE", "Cloturee (BC creee)"


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
    """
    Fiche d'Expression des Besoins (FEB).

    Numero genere automatiquement : FEB-AAAA-NNNN (ex : FEB-2025-0001).
    """

    # ─── Identification ───────────────────────────────────────────
    numero = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name="Numero de FEB",
        help_text="Format : FEB-AAAA-NNNN (genere automatiquement).",
    )
    objet = models.CharField(
        max_length=255,
        verbose_name="Objet de la demande",
        help_text="Description courte de ce qui est demande.",
    )

    # ─── Acteurs ──────────────────────────────────────────────────
    demandeur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="feb_demandees",
        verbose_name="Demandeur",
    )
    fournisseur = models.ForeignKey(
        Fournisseur,
        on_delete=models.PROTECT,
        related_name="feb_recues",
        verbose_name="Fournisseur",
    )
    validateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="feb_validees",
        null=True, blank=True,
        verbose_name="Validateur (CG ou DFC)",
    )

    # ─── Statut & origine ─────────────────────────────────────────
    statut = models.CharField(
        max_length=20,
        choices=StatutFEB.choices,
        default=StatutFEB.DRAFT,
        verbose_name="Statut",
        db_index=True,
    )
    origine = models.CharField(
        max_length=20,
        choices=OrigineFEB.choices,
        default=OrigineFEB.MANUELLE,
        verbose_name="Origine",
    )
    est_auto = models.BooleanField(
        default=False,
        verbose_name="Generee automatiquement",
        help_text="True si issue de la prediction des besoins.",
    )

    # ─── Montants (calcules automatiquement via les lignes) ───────
    montant_ht = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Montant HT",
    )
    taux_tva = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal("18.00"),
        verbose_name="Taux TVA (%)",
    )
    montant_tva = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Montant TVA",
    )
    montant_ttc = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Montant TTC",
    )

    # ─── Suppression logique & motif ──────────────────────────────
    motif_action = models.TextField(
        blank=True, default="",
        verbose_name="Motif de la derniere action",
        help_text="Obligatoire pour les modifications, suppressions, rejets.",
    )
    est_supprimee = models.BooleanField(
        default=False,
        verbose_name="Supprimee (suppression logique)",
        db_index=True,
    )

    # ─── Horodatage ───────────────────────────────────────────────
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de creation",
    )
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name="Date de derniere modification",
    )
    date_validation = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Date de validation",
    )
    date_suppression = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Date de suppression",
    )

    objects = FicheExpressionManager()

    class Meta:
        db_table = "fiche_expression"
        verbose_name = "FEB - Fiche d'Expression des Besoins"
        verbose_name_plural = "FEB - Fiches d'Expression des Besoins"
        ordering = ["-date_creation"]
        indexes = [
            models.Index(fields=["statut", "est_supprimee"]),
            models.Index(fields=["demandeur", "statut"]),
            models.Index(fields=["fournisseur"]),
            models.Index(fields=["-date_creation"]),
        ]

    def __str__(self):
        return f"{self.numero} — {self.objet[:40]}"

    # ─── Methodes metier ─────────────────────────────────────────
    def calculer_totaux(self, sauvegarder=True):
        """
        Recalcule HT, TVA, TTC a partir des lignes.

        Utilise apres ajout/modification/suppression d'une ligne.
        """
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
        """
        Vrai si le montant TTC depasse le seuil de generation BC.

        Seuil par defaut : 50 000 F CFA (configurable Admin).
        """
        seuil = Decimal(str(getattr(settings, "SEUIL_BC_AUTOMATIQUE", 50000)))
        return self.montant_ttc > seuil

    @property
    def peut_etre_validee(self):
        """Vrai si la FEB peut passer EN_INSTANCE -> VALIDEE."""
        return self.statut == StatutFEB.EN_INSTANCE

    @property
    def peut_etre_modifiee(self):
        """Vrai si la FEB peut encore etre modifiee."""
        return self.statut in (
            StatutFEB.DRAFT,
            StatutFEB.EN_INSTANCE,
            StatutFEB.MODIFIEE,
        )

    @property
    def couleur_statut(self):
        """Retourne le badge CSS associe au statut."""
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
    """
    Ligne de detail d'une FEB.

    Chaque ligne reference SOIT un Article SOIT un Service (jamais les deux).
    Le montant_ligne est calcule automatiquement : quantite * prix_unitaire.
    """

    fiche = models.ForeignKey(
        FicheExpression,
        on_delete=models.CASCADE,
        related_name="lignes",
        verbose_name="FEB liee",
    )
    type_ligne = models.CharField(
        max_length=10,
        choices=TypeLigne.choices,
        verbose_name="Type",
    )
    article = models.ForeignKey(
        Article,
        on_delete=models.PROTECT,
        related_name="lignes_feb",
        null=True, blank=True,
        verbose_name="Article",
    )
    service = models.ForeignKey(
        ServiceExterieur,
        on_delete=models.PROTECT,
        related_name="lignes_feb",
        null=True, blank=True,
        verbose_name="Service",
    )
    designation_libre = models.CharField(
        max_length=255,
        blank=True, default="",
        verbose_name="Designation libre",
        help_text="Si l'article/service n'est pas dans le catalogue.",
    )
    quantite = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Quantite",
    )
    prix_unitaire = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Prix unitaire HT",
    )
    montant_ligne = models.DecimalField(
        max_digits=14, decimal_places=2,
        verbose_name="Montant ligne (qte * prix)",
    )

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
        """Retourne la designation effective (catalogue ou libre)."""
        if self.article:
            return self.article.designation
        if self.service:
            return self.service.designation
        return self.designation_libre or "—"

    def clean(self):
        """Valide la coherence article/service selon type_ligne."""
        super().clean()

        if self.type_ligne == TypeLigne.ARTICLE and not (self.article or self.designation_libre):
            raise ValidationError({
                "article": "Selectionner un article ou saisir une designation libre."
            })
        if self.type_ligne == TypeLigne.SERVICE and not (self.service or self.designation_libre):
            raise ValidationError({
                "service": "Selectionner un service ou saisir une designation libre."
            })
        if self.quantite is not None and self.quantite <= 0:
            raise ValidationError({"quantite": "La quantite doit etre superieure a 0."})
        if self.prix_unitaire is not None and self.prix_unitaire < 0:
            raise ValidationError({"prix_unitaire": "Le prix unitaire ne peut etre negatif."})

    def save(self, *args, **kwargs):
        """Calcule automatiquement montant_ligne avant sauvegarde."""
        self.montant_ligne = (
            Decimal(str(self.quantite or 0)) * Decimal(str(self.prix_unitaire or 0))
        ).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)