"""Services metier IoT - geofencing + creation alertes."""
import logging

from django.db import transaction
from django.utils import timezone

from .models import (
    AlerteIoT,
    Equipement,
    Localisation,
    StatutEquipement,
    TypeAlerte,
    ZoneGeographique,
)

logger = logging.getLogger(__name__)


@transaction.atomic
def enregistrer_signal_capteur(equipement, zone, signal_force=100, capteur_id=""):
    """
    Enregistre un signal capteur et applique le geofencing.

    Args:
        equipement: instance Equipement
        zone: instance ZoneGeographique detectee
        signal_force: 0-100
        capteur_id: identifiant du capteur

    Returns:
        tuple : (Localisation, AlerteIoT|None)
    """
    # Mise a jour timestamp
    equipement.derniere_detection = timezone.now()

    # Verification geofencing
    alerte = None
    est_alerte = not zone.est_zone_autorisee

    if est_alerte:
        # Zone non autorisee -> creer alerte
        alerte = _creer_alerte_geofencing(equipement, zone)
        equipement.statut = StatutEquipement.SORTI_ZONE

    # Mise a jour zone actuelle
    zone_precedente = equipement.zone_actuelle
    equipement.zone_actuelle = zone
    equipement.save(update_fields=["zone_actuelle", "derniere_detection", "statut"])

    # Cree l'enregistrement de localisation
    localisation = Localisation.objects.create(
        equipement=equipement,
        zone=zone,
        signal_force=signal_force,
        capteur_id=capteur_id,
        est_alerte=est_alerte,
    )

    if est_alerte:
        logger.warning(
            "ALERTE GEOFENCING : %s detecte en zone non autorisee '%s'",
            equipement.designation, zone.nom,
        )
    else:
        logger.info(
            "Signal IoT : %s @ %s",
            equipement.designation, zone.nom,
        )

    return localisation, alerte


def _creer_alerte_geofencing(equipement, zone_actuelle):
    """Cree une alerte de geofencing."""
    return AlerteIoT.objects.create(
        equipement=equipement,
        zone_quittee=equipement.zone_actuelle,
        zone_actuelle=zone_actuelle,
        type_alerte=TypeAlerte.GEOFENCING,
        message=(
            f"L'equipement {equipement.designation} (S/N {equipement.numero_serie}) "
            f"a ete detecte dans la zone NON AUTORISEE '{zone_actuelle.nom}'. "
            f"Action immediate requise !"
        ),
    )


def traiter_alerte(alerte, utilisateur, commentaire=""):
    """Marque une alerte comme traitee."""
    alerte.est_traitee = True
    alerte.traite_par = utilisateur
    alerte.commentaire_traitement = commentaire
    alerte.date_traitement = timezone.now()
    alerte.save()

    # Si plus d'alerte active, remettre l'equipement en service
    if not alerte.equipement.alertes.filter(est_traitee=False).exists():
        alerte.equipement.statut = StatutEquipement.EN_SERVICE
        alerte.equipement.save(update_fields=["statut"])

    logger.info(
        "Alerte %s traitee par %s",
        alerte.pk, utilisateur.identifiant,
    )