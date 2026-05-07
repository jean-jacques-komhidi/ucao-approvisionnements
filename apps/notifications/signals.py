"""Signaux automatiques pour declencher les notifications."""
import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.approvisionnements.models import (
    BonCommande,
    FicheExpression,
    StatutBC,
    StatutFEB,
)
from apps.comptes.models import RoleUtilisateur

from .models import NiveauNotification, TypeNotification
from .services import get_users_par_role, notifier, url_absolue

logger = logging.getLogger(__name__)

_statuts_precedents = {}


@receiver(pre_save, sender=FicheExpression)
def memoriser_statut_feb(sender, instance, **kwargs):
    if instance.pk:
        try:
            ancien = FicheExpression.objects.get(pk=instance.pk)
            _statuts_precedents[f"feb_{instance.pk}"] = ancien.statut
        except FicheExpression.DoesNotExist:
            _statuts_precedents[f"feb_{instance.pk}"] = None
    else:
        _statuts_precedents[f"feb_{instance.pk}"] = None


@receiver(pre_save, sender=BonCommande)
def memoriser_statut_bc(sender, instance, **kwargs):
    if instance.pk:
        try:
            ancien = BonCommande.objects.get(pk=instance.pk)
            _statuts_precedents[f"bc_{instance.pk}"] = ancien.statut
        except BonCommande.DoesNotExist:
            _statuts_precedents[f"bc_{instance.pk}"] = None
    else:
        _statuts_precedents[f"bc_{instance.pk}"] = None


@receiver(post_save, sender=FicheExpression, dispatch_uid="notif_feb")
def notifier_changement_feb(sender, instance, created, **kwargs):
    statut_precedent = _statuts_precedents.pop(f"feb_{instance.pk}", None)
    statut_actuel = instance.statut

    if statut_precedent == statut_actuel and not created:
        return

    url_feb = f"/feb/{instance.pk}/"

    # FEB SOUMISE
    if statut_actuel == StatutFEB.EN_INSTANCE and statut_precedent != StatutFEB.EN_INSTANCE:
        valideurs = (
            get_users_par_role(RoleUtilisateur.CG)
            + get_users_par_role(RoleUtilisateur.DFC)
            + get_users_par_role(RoleUtilisateur.ADMIN)
        )
        if valideurs:
            notifier(
                destinataires=valideurs,
                type_notif=TypeNotification.FEB_SOUMISE,
                niveau=NiveauNotification.AVERTISSEMENT,
                sujet=f"Nouvelle FEB a valider : {instance.numero}",
                message=(
                    f"{instance.demandeur.nom_complet} a soumis la FEB "
                    f"{instance.numero}. Montant TTC : {instance.montant_ttc} F CFA."
                ),
                expediteur=instance.demandeur,
                entite="FicheExpression",
                entite_id=instance.pk,
                url_action=url_feb,
                template_email="notifications/emails/feb_soumise.html",
                contexte_email={"feb": instance, "url_feb": url_absolue(url_feb)},
            )
            logger.info("Notif FEB soumise envoyee pour %s (%d destinataires)",
                        instance.numero, len(valideurs))

    # FEB VALIDEE
    elif statut_actuel == StatutFEB.VALIDEE and statut_precedent != StatutFEB.VALIDEE:
        notifier(
            destinataires=instance.demandeur,
            type_notif=TypeNotification.FEB_VALIDEE,
            niveau=NiveauNotification.SUCCES,
            sujet=f"FEB {instance.numero} validee",
            message=(
                f"Votre FEB {instance.numero} a ete validee. "
                f"Un BC va etre genere automatiquement."
            ),
            expediteur=instance.validateur,
            entite="FicheExpression",
            entite_id=instance.pk,
            url_action=url_feb,
            template_email="notifications/emails/feb_validee.html",
            contexte_email={"feb": instance, "url_feb": url_absolue(url_feb)},
        )
        logger.info("Notif FEB validee envoyee pour %s", instance.numero)

    # FEB CLOTUREE
    elif statut_actuel == StatutFEB.CLOTUREE and statut_precedent != StatutFEB.CLOTUREE:
        notifier(
            destinataires=instance.demandeur,
            type_notif=TypeNotification.FEB_CLOTUREE,
            niveau=NiveauNotification.SUCCES,
            sujet=f"FEB {instance.numero} cloturee",
            message=(
                f"Votre FEB {instance.numero} a ete cloturee directement "
                f"(montant <= 50 000 F)."
            ),
            expediteur=instance.validateur,
            entite="FicheExpression",
            entite_id=instance.pk,
            url_action=url_feb,
            template_email="notifications/emails/feb_cloturee.html",
            contexte_email={"feb": instance, "url_feb": url_absolue(url_feb)},
        )
        logger.info("Notif FEB cloturee envoyee pour %s", instance.numero)

    # FEB REJETEE
    elif statut_actuel == StatutFEB.REJETEE and statut_precedent != StatutFEB.REJETEE:
        notifier(
            destinataires=instance.demandeur,
            type_notif=TypeNotification.FEB_REJETEE,
            niveau=NiveauNotification.DANGER,
            sujet=f"FEB {instance.numero} rejetee",
            message=(
                f"Votre FEB {instance.numero} a ete rejetee. "
                f"Motif : {instance.motif_action}"
            ),
            expediteur=instance.validateur,
            entite="FicheExpression",
            entite_id=instance.pk,
            url_action=url_feb,
            template_email="notifications/emails/feb_rejetee.html",
            contexte_email={"feb": instance, "url_feb": url_absolue(url_feb)},
        )
        logger.info("Notif FEB rejetee envoyee pour %s", instance.numero)


@receiver(post_save, sender=BonCommande, dispatch_uid="notif_bc")
def notifier_changement_bc(sender, instance, created, **kwargs):
    statut_precedent = _statuts_precedents.pop(f"bc_{instance.pk}", None)
    statut_actuel = instance.statut
    url_bc = f"/bc/{instance.pk}/"

    if created:
        destinataires = (
            get_users_par_role(RoleUtilisateur.DG)
            + get_users_par_role(RoleUtilisateur.DFC)
            + get_users_par_role(RoleUtilisateur.ADMIN)
        )
        if destinataires:
            notifier(
                destinataires=destinataires,
                type_notif=TypeNotification.BC_GENERE,
                niveau=NiveauNotification.AVERTISSEMENT,
                sujet=f"Nouveau BC a valider : {instance.numero}",
                message=(
                    f"Le BC {instance.numero} a ete genere depuis "
                    f"la FEB {instance.fiche.numero}. "
                    f"Montant TTC : {instance.montant_ttc} F CFA."
                ),
                entite="BonCommande",
                entite_id=instance.pk,
                url_action=url_bc,
                template_email="notifications/emails/bc_genere.html",
                contexte_email={"bc": instance, "url_bc": url_absolue(url_bc)},
            )
            logger.info("Notif BC genere envoyee pour %s (%d destinataires)",
                        instance.numero, len(destinataires))

    elif statut_actuel == StatutBC.VALIDE and statut_precedent != StatutBC.VALIDE:
        comptables = get_users_par_role(RoleUtilisateur.COMPTABLE)
        if comptables:
            notifier(
                destinataires=comptables,
                type_notif=TypeNotification.BC_VALIDE,
                niveau=NiveauNotification.SUCCES,
                sujet=f"BC {instance.numero} valide - Paiement a preparer",
                message=(
                    f"Le BC {instance.numero} a ete valide. "
                    f"Vous pouvez preparer le paiement de "
                    f"{instance.montant_ttc} F CFA au fournisseur "
                    f"{instance.fournisseur.nom}."
                ),
                expediteur=instance.validateur,
                entite="BonCommande",
                entite_id=instance.pk,
                url_action=url_bc,
                template_email="notifications/emails/bc_valide.html",
                contexte_email={"bc": instance, "url_bc": url_absolue(url_bc)},
            )

        notifier(
            destinataires=instance.fiche.demandeur,
            type_notif=TypeNotification.BC_VALIDE,
            niveau=NiveauNotification.SUCCES,
            sujet=f"Votre commande {instance.numero} est validee",
            message=(
                f"Le BC {instance.numero} (issu de votre FEB "
                f"{instance.fiche.numero}) a ete valide."
            ),
            entite="BonCommande",
            entite_id=instance.pk,
            url_action=url_bc,
        )
        logger.info("Notif BC valide envoyee pour %s", instance.numero)