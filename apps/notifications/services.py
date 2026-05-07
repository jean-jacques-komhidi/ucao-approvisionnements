"""Service centralise pour creer/envoyer des notifications."""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .models import NiveauNotification, Notification

logger = logging.getLogger(__name__)


def creer_notification(
    destinataire,
    type_notif,
    sujet,
    message,
    expediteur=None,
    niveau=NiveauNotification.INFO,
    entite=None,
    entite_id=None,
    url_action="",
):
    """Cree une notification in-app."""
    notif = Notification.objects.create(
        destinataire=destinataire,
        expediteur=expediteur,
        type_notif=type_notif,
        niveau=niveau,
        sujet=sujet,
        message=message,
        entite=entite or "",
        entite_id=entite_id,
        url_action=url_action,
    )
    logger.info(
        "Notification creee : %s -> %s (type: %s)",
        notif.id, destinataire.identifiant, type_notif,
    )
    return notif


def envoyer_email(destinataire_email, sujet, template_html, contexte=None, pieces_jointes=None):
    """Envoie un email HTML avec template."""
    if not destinataire_email:
        logger.warning("Tentative d'envoi email sans destinataire.")
        return False

    contexte = contexte or {}
    contexte["site_url"] = "http://127.0.0.1:8000"

    try:
        html_content = render_to_string(template_html, contexte)
        texte_brut = (
            f"{sujet}\n\n"
            f"Cet email contient du HTML.\n\n"
            f"UCAO Approvisionnements"
        )

        email = EmailMultiAlternatives(
            subject=f"[UCAO Approvisionnements] {sujet}",
            body=texte_brut,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinataire_email],
        )
        email.attach_alternative(html_content, "text/html")

        if pieces_jointes:
            for filename, content, mimetype in pieces_jointes:
                email.attach(filename, content, mimetype)

        email.send(fail_silently=False)
        logger.info("Email envoye a %s : %s", destinataire_email, sujet)
        return True

    except Exception as exc:
        logger.exception(
            "Erreur envoi email a %s (%s) : %s",
            destinataire_email, sujet, exc,
        )
        return False


def notifier(
    destinataires,
    type_notif,
    sujet,
    message,
    template_email=None,
    contexte_email=None,
    pieces_jointes=None,
    expediteur=None,
    niveau=NiveauNotification.INFO,
    entite=None,
    entite_id=None,
    url_action="",
):
    """Cree une notif in-app ET envoie un email a chaque destinataire."""
    if not isinstance(destinataires, (list, tuple)):
        destinataires = [destinataires]

    notifications = []

    for destinataire in destinataires:
        notif = creer_notification(
            destinataire=destinataire,
            type_notif=type_notif,
            sujet=sujet,
            message=message,
            expediteur=expediteur,
            niveau=niveau,
            entite=entite,
            entite_id=entite_id,
            url_action=url_action,
        )

        if template_email and destinataire.email:
            contexte = contexte_email or {}
            contexte["destinataire"] = destinataire
            contexte["notification"] = notif

            email_ok = envoyer_email(
                destinataire_email=destinataire.email,
                sujet=sujet,
                template_html=template_email,
                contexte=contexte,
                pieces_jointes=pieces_jointes,
            )

            if email_ok:
                notif.email_envoye = True
                notif.save(update_fields=["email_envoye"])

        notifications.append(notif)

    return notifications


def get_users_par_role(role):
    """Retourne tous les utilisateurs actifs ayant un role donne."""
    from apps.comptes.models import Utilisateur

    return list(Utilisateur.objects.filter(role=role, est_actif=True))


def url_absolue(chemin_relatif):
    """Construit une URL absolue (utile pour les emails)."""
    site_url = "http://127.0.0.1:8000"
    return f"{site_url}{chemin_relatif}"