"""
Modeles de l'extension IoT - suivi en temps reel des equipements.

Architecture :
- Equipement : un actif physique avec un tag RFID/BLE
- ZoneGeographique : une zone autorisee dans un batiment
- Localisation : historique des positions detectees par capteurs
- AlerteIoT : alerte declenchee si equipement sort de zone autorisee
"""
import secrets
from decimal import Decimal

from django.conf import settings
from django.db import models


class TypeZone(models.TextChoices):
    """Type de zone."""

    BUREAU = "BUREAU", "Bureau"
    SALLE_INFORMATIQUE = "SALLE_INFORMATIQUE", "Salle informatique"
    SALLE_REUNION = "SALLE_REUNION", "Salle de reunion"
    ENTREPOT = "ENTREPOT", "Entrepot"
    SECURISE = "SECURISE", "Zone securisee"
    EXTERIEUR = "EXTERIEUR", "Exterieur"


class StatutEquipement(models.TextChoices):
    """Statut operationnel de l'equipement."""

    EN_SERVICE = "EN_SERVICE", "En service"
    EN_PANNE = "EN_PANNE", "En panne"
    EN_MAINTENANCE = "EN_MAINTENANCE", "En maintenance"
    SORTI_ZONE = "SORTI_ZONE", "Sorti de zone autorisee"
    INACTIF = "INACTIF", "Inactif"


class TypeAlerte(models.TextChoices):
    """Type d'alerte IoT."""

    GEOFENCING = "GEOFENCING", "Sortie de zone non autorisee"
    SIGNAL_PERDU = "SIGNAL_PERDU", "Signal capteur perdu"
    BATTERIE_FAIBLE = "BATTERIE_FAIBLE", "Batterie capteur faible"
    NON_AUTORISE = "NON_AUTORISE", "Mouvement non autorise"


# ═══════════════════════════════════════════════════════════════════
# ZONE GEOGRAPHIQUE
# ═══════════════════════════════════════════════════════════════════
class ZoneGeographique(models.Model):
    """
    Zone geographique du campus UCAO.

    Exemples :
    - Salle Info A, Batiment principal, RDC
    - Bureau DG, Batiment direction, etage 2
    """

    nom = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nom de la zone",
    )

    batiment = models.CharField(max_length=100, verbose_name="Batiment")
    etage = models.CharField(
        max_length=20,
        blank=True, default="",
        help_text="Ex : RDC, 1er, 2eme",
    )

    type_zone = models.CharField(
        max_length=25,
        choices=TypeZone.choices,
        default=TypeZone.BUREAU,
    )

    # Coordonnees pour la carte (optionnelles)
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7,
        null=True, blank=True,
        help_text="Coordonnees GPS",
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7,
        null=True, blank=True,
    )

    est_zone_autorisee = models.BooleanField(
        default=True,
        help_text="Si False, tout equipement detecte ici declenche une alerte",
    )

    description = models.TextField(blank=True, default="")
    est_active = models.BooleanField(default=True, db_index=True)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "iot_zone_geographique"
        verbose_name = "Zone geographique"
        verbose_name_plural = "Zones geographiques"
        ordering = ["batiment", "etage", "nom"]

    def __str__(self):
        return f"{self.nom} ({self.batiment} - {self.etage})"


# ═══════════════════════════════════════════════════════════════════
# EQUIPEMENT
# ═══════════════════════════════════════════════════════════════════
def _generer_token_capteur():
    """Genere un token securise pour authentification capteur."""
    return secrets.token_urlsafe(32)


class Equipement(models.Model):
    """
    Equipement physique suivi par capteur RFID/BLE.

    Identifie de maniere unique par son rfid_tag.
    """

    designation = models.CharField(
        max_length=200,
        verbose_name="Designation",
    )

    numero_serie = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numero de serie",
    )

    rfid_tag = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="Tag RFID/BLE",
        help_text="Identifiant unique du tag",
    )

    valeur_acquisition = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Valeur d'acquisition (F CFA)",
    )

    fournisseur = models.ForeignKey(
        "referentiels.Fournisseur",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="equipements_iot",
    )

    zone_actuelle = models.ForeignKey(
        ZoneGeographique,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="equipements_presents",
        verbose_name="Zone actuelle",
    )

    statut = models.CharField(
        max_length=20,
        choices=StatutEquipement.choices,
        default=StatutEquipement.EN_SERVICE,
        db_index=True,
    )

    est_suivi_iot = models.BooleanField(
        default=True,
        help_text="Activer le suivi IoT en temps reel",
    )

    acces_bloque = models.BooleanField(
        default=False,
        help_text="Bloquer l'equipement (anti-vol)",
    )

    # Token pour authentifier les capteurs
    token_capteur = models.CharField(
        max_length=64,
        unique=True,
        default=_generer_token_capteur,
        help_text="Token secret pour API capteur",
    )

    description = models.TextField(blank=True, default="")
    derniere_detection = models.DateTimeField(null=True, blank=True)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "iot_equipement"
        verbose_name = "Equipement IoT"
        verbose_name_plural = "Equipements IoT"
        ordering = ["-date_creation"]
        indexes = [
            models.Index(fields=["statut"]),
            models.Index(fields=["est_suivi_iot"]),
        ]

    def __str__(self):
        return f"{self.designation} (S/N: {self.numero_serie})"

    @property
    def couleur_statut(self):
        return {
            StatutEquipement.EN_SERVICE: "success",
            StatutEquipement.EN_PANNE: "error",
            StatutEquipement.EN_MAINTENANCE: "warning",
            StatutEquipement.SORTI_ZONE: "error",
            StatutEquipement.INACTIF: "neutre",
        }.get(self.statut, "neutre")

    @property
    def alertes_actives(self):
        """Retourne les alertes non traitees."""
        return self.alertes.filter(est_traitee=False)


# ═══════════════════════════════════════════════════════════════════
# LOCALISATION (historique)
# ═══════════════════════════════════════════════════════════════════
class Localisation(models.Model):
    """Position detectee d'un equipement a un instant T."""

    equipement = models.ForeignKey(
        Equipement,
        on_delete=models.CASCADE,
        related_name="localisations",
    )

    zone = models.ForeignKey(
        ZoneGeographique,
        on_delete=models.PROTECT,
        related_name="localisations",
    )

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    signal_force = models.IntegerField(
        default=100,
        help_text="Force du signal (0-100)",
    )

    capteur_id = models.CharField(
        max_length=50, blank=True, default="",
        help_text="ID du capteur ayant detecte",
    )

    est_alerte = models.BooleanField(
        default=False,
        help_text="True si zone non autorisee",
    )

    class Meta:
        db_table = "iot_localisation"
        verbose_name = "Localisation"
        verbose_name_plural = "Localisations"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["equipement", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.equipement.designation} @ {self.zone.nom} ({self.timestamp})"


# ═══════════════════════════════════════════════════════════════════
# ALERTE IoT
# ═══════════════════════════════════════════════════════════════════
class AlerteIoT(models.Model):
    """Alerte declenchee par le systeme IoT."""

    equipement = models.ForeignKey(
        Equipement,
        on_delete=models.CASCADE,
        related_name="alertes",
    )

    zone_quittee = models.ForeignKey(
        ZoneGeographique,
        on_delete=models.PROTECT,
        related_name="alertes_zone_quittee",
        null=True, blank=True,
    )

    zone_actuelle = models.ForeignKey(
        ZoneGeographique,
        on_delete=models.PROTECT,
        related_name="alertes_zone_actuelle",
        null=True, blank=True,
    )

    type_alerte = models.CharField(
        max_length=20,
        choices=TypeAlerte.choices,
        default=TypeAlerte.GEOFENCING,
    )

    message = models.TextField()

    est_traitee = models.BooleanField(default=False, db_index=True)
    traite_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="alertes_iot_traitees",
        null=True, blank=True,
    )
    commentaire_traitement = models.TextField(blank=True, default="")
    date_traitement = models.DateTimeField(null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "iot_alerte"
        verbose_name = "Alerte IoT"
        verbose_name_plural = "Alertes IoT"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["est_traitee"]),
            models.Index(fields=["-timestamp"]),
        ]

    def __str__(self):
        return f"[{self.get_type_alerte_display()}] {self.equipement.designation}"

    @property
    def couleur_niveau(self):
        return {
            TypeAlerte.GEOFENCING: "error",
            TypeAlerte.SIGNAL_PERDU: "warning",
            TypeAlerte.BATTERIE_FAIBLE: "warning",
            TypeAlerte.NON_AUTORISE: "error",
        }.get(self.type_alerte, "neutre")