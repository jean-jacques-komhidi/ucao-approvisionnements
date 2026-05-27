"""Signaux IoT - notifications automatiques."""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.comptes.models import RoleUtilisateur
from apps.notifications.models import NiveauNotification, TypeNotification
from apps.notifications.services import get_users_par_role, notifier

from .models import AlerteIoT

logger = logging.getLogger(__name__)


@receiver(post_save, sender=AlerteIoT, dispatch_uid="notif_alerte_iot")
def notifier_alerte_iot(sender, instance, created, **kwargs):
    """Notifie l'admin et le resp.appro sur creation d'alerte IoT."""
    if not created:
        return

    destinataires = (
        get_users_par_role(RoleUtilisateur.ADMIN)
        + get_users_par_role(RoleUtilisateur.RESP_APPRO)
    )

    if destinataires:
        url_alerte = f"/iot/alertes/{instance.pk}/"

        notifier(
            destinataires=destinataires,
            type_notif=TypeNotification.AVERTISSEMENT,
            niveau=NiveauNotification.DANGER,
            sujet=f"🚨 ALERTE IoT : {instance.equipement.designation}",
            message=instance.message,
            entite="AlerteIoT",
            entite_id=instance.pk,
            url_action=url_alerte,
        )

        logger.warning(
            "Notification IoT envoyee a %d destinataires pour alerte %s",
            len(destinataires), instance.pk,
        )