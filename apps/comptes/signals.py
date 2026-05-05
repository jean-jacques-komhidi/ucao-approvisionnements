"""
Signaux de l'app comptes.

Regle critique du CDC :
    5 echecs de connexion consecutifs -> blocage automatique du compte
    + alerte Administrateur par email.
"""
import logging

from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import RoleUtilisateur, Utilisateur

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 1. Detection du seuil de tentatives -> blocage automatique
# ═══════════════════════════════════════════════════════════════════
@receiver(pre_save, sender=Utilisateur, dispatch_uid="bloquer_si_seuil_tentatives")
def bloquer_si_seuil_tentatives_atteint(sender, instance, **kwargs):
    """
    Bloque automatiquement le compte si tentatives_echecs >= seuil.

    Ce signal s'execute AVANT la sauvegarde en base.
    On ne bloque jamais un compte Admin (eviterait de se bloquer soi-meme).
    """
    seuil = getattr(settings, "NB_TENTATIVES_AVANT_BLOCAGE", 5)

    if (
        instance.est_actif
        and instance.tentatives_echecs >= seuil
        and instance.role != RoleUtilisateur.ADMIN
    ):
        instance.est_actif = False
        instance.date_blocage = timezone.now()
        instance.motif_blocage = (
            f"Blocage automatique apres {seuil} tentatives "
            f"de connexion echouees consecutives."
        )
        # Marque l'instance pour que le post_save sache declencher l'email
        instance._declenche_alerte_blocage = True

        logger.error(
            "Compte %s bloque automatiquement (%d tentatives echouees)",
            instance.identifiant,
            instance.tentatives_echecs,
        )


# ═══════════════════════════════════════════════════════════════════
# 2. Envoi de l'alerte aux administrateurs
# ═══════════════════════════════════════════════════════════════════
@receiver(post_save, sender=Utilisateur, dispatch_uid="alerter_admin_blocage")
def alerter_admin_apres_blocage(sender, instance, created, **kwargs):
    """Envoie un email aux administrateurs lorsqu'un compte vient d'etre bloque."""
    if not getattr(instance, "_declenche_alerte_blocage", False):
        return

    instance._declenche_alerte_blocage = False

    # Liste des emails des admins actifs
    emails_admins = list(
        Utilisateur.objects.filter(
            role=RoleUtilisateur.ADMIN,
            est_actif=True,
        ).values_list("email", flat=True)
    )

    if not emails_admins:
        logger.warning("Aucun administrateur actif — alerte non envoyee")
        return

    sujet = f"[UCAO Appro] Compte bloque : {instance.identifiant}"
    message = (
        f"Bonjour Administrateur,\n\n"
        f"Le compte de l'utilisateur ci-dessous vient d'etre bloque automatiquement :\n\n"
        f"  - Identifiant  : {instance.identifiant}\n"
        f"  - Nom complet  : {instance.nom_complet}\n"
        f"  - Role         : {instance.get_role_display()}\n"
        f"  - Email        : {instance.email}\n"
        f"  - Date blocage : {instance.date_blocage}\n"
        f"  - Motif        : {instance.motif_blocage}\n\n"
        f"Veuillez verifier l'origine de la tentative et debloquer le compte "
        f"si la demande est legitime.\n\n"
        f"— Systeme d'Approvisionnements UCAO-ISG-CSM"
    )

    try:
        send_mail(
            subject=sujet,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=emails_admins,
            fail_silently=False,
        )
        logger.info(
            "Alerte de blocage envoyee a %d administrateur(s) pour %s",
            len(emails_admins),
            instance.identifiant,
        )
    except Exception as exc:
        logger.exception("Echec envoi email blocage : %s", exc)


# ═══════════════════════════════════════════════════════════════════
# 3. Trace des connexions reussies (audit leger)
# ═══════════════════════════════════════════════════════════════════
@receiver(user_logged_in, dispatch_uid="tracer_connexion_reussie")
def tracer_connexion_reussie(sender, request, user, **kwargs):
    """Met a jour la date de derniere connexion reussie."""
    if hasattr(user, "date_derniere_connexion_reussie"):
        user.date_derniere_connexion_reussie = timezone.now()
        user.save(update_fields=["date_derniere_connexion_reussie"])
        logger.info(
            "Connexion enregistree pour %s (IP=%s)",
            user.identifiant,
            request.META.get("REMOTE_ADDR", "?"),
        )


@receiver(user_logged_out, dispatch_uid="tracer_deconnexion")
def tracer_deconnexion(sender, request, user, **kwargs):
    """Invalide les sessions actives liees a cet utilisateur."""
    if user and hasattr(user, "sessions"):
        user.sessions.filter(est_active=True).update(est_active=False)
        logger.info("Deconnexion de %s", user.identifiant)