"""Signaux automatiques pour declencher les notifications."""
import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.approvisionnements.models import (
    BonCommande,
    FicheExpression,
    OrdrePaiement,
    Paiement,
    StatutBC,
    StatutFEB,
    StatutOrdrePaiement,
    StatutPaiement,
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


@receiver(pre_save, sender=OrdrePaiement)
def memoriser_statut_ordre(sender, instance, **kwargs):
    if instance.pk:
        try:
            ancien = OrdrePaiement.objects.get(pk=instance.pk)
            _statuts_precedents[f"ordre_{instance.pk}"] = ancien.statut
        except OrdrePaiement.DoesNotExist:
            _statuts_precedents[f"ordre_{instance.pk}"] = None
    else:
        _statuts_precedents[f"ordre_{instance.pk}"] = None


@receiver(pre_save, sender=Paiement)
def memoriser_statut_paiement(sender, instance, **kwargs):
    if instance.pk:
        try:
            ancien = Paiement.objects.get(pk=instance.pk)
            _statuts_precedents[f"paiement_{instance.pk}"] = ancien.statut
        except Paiement.DoesNotExist:
            _statuts_precedents[f"paiement_{instance.pk}"] = None
    else:
        _statuts_precedents[f"paiement_{instance.pk}"] = None


@receiver(post_save, sender=FicheExpression, dispatch_uid="notif_feb")
def notifier_changement_feb(sender, instance, created, **kwargs):
    statut_precedent = _statuts_precedents.pop(f"feb_{instance.pk}", None)
    statut_actuel = instance.statut

    if statut_precedent == statut_actuel and not created:
        return

    url_feb = f"/feb/{instance.pk}/"

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
                message=f"{instance.demandeur.nom_complet} a soumis la FEB {instance.numero}.",
                expediteur=instance.demandeur,
                entite="FicheExpression",
                entite_id=instance.pk,
                url_action=url_feb,
                template_email="notifications/emails/feb_soumise.html",
                contexte_email={"feb": instance, "url_feb": url_absolue(url_feb)},
            )

    elif statut_actuel == StatutFEB.VALIDEE and statut_precedent != StatutFEB.VALIDEE:
        notifier(
            destinataires=instance.demandeur,
            type_notif=TypeNotification.FEB_VALIDEE,
            niveau=NiveauNotification.SUCCES,
            sujet=f"FEB {instance.numero} validee",
            message=f"Votre FEB {instance.numero} a ete validee.",
            expediteur=instance.validateur,
            entite="FicheExpression",
            entite_id=instance.pk,
            url_action=url_feb,
            template_email="notifications/emails/feb_validee.html",
            contexte_email={"feb": instance, "url_feb": url_absolue(url_feb)},
        )

    elif statut_actuel == StatutFEB.CLOTUREE and statut_precedent != StatutFEB.CLOTUREE:
        notifier(
            destinataires=instance.demandeur,
            type_notif=TypeNotification.FEB_CLOTUREE,
            niveau=NiveauNotification.SUCCES,
            sujet=f"FEB {instance.numero} cloturee",
            message=f"Votre FEB {instance.numero} a ete cloturee.",
            expediteur=instance.validateur,
            entite="FicheExpression",
            entite_id=instance.pk,
            url_action=url_feb,
            template_email="notifications/emails/feb_cloturee.html",
            contexte_email={"feb": instance, "url_feb": url_absolue(url_feb)},
        )

    elif statut_actuel == StatutFEB.REJETEE and statut_precedent != StatutFEB.REJETEE:
        notifier(
            destinataires=instance.demandeur,
            type_notif=TypeNotification.FEB_REJETEE,
            niveau=NiveauNotification.DANGER,
            sujet=f"FEB {instance.numero} rejetee",
            message=f"Votre FEB {instance.numero} a ete rejetee. Motif : {instance.motif_action}",
            expediteur=instance.validateur,
            entite="FicheExpression",
            entite_id=instance.pk,
            url_action=url_feb,
            template_email="notifications/emails/feb_rejetee.html",
            contexte_email={"feb": instance, "url_feb": url_absolue(url_feb)},
        )


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
                message=f"BC {instance.numero} genere depuis FEB {instance.fiche.numero}.",
                entite="BonCommande",
                entite_id=instance.pk,
                url_action=url_bc,
                template_email="notifications/emails/bc_genere.html",
                contexte_email={"bc": instance, "url_bc": url_absolue(url_bc)},
            )

    elif statut_actuel == StatutBC.VALIDE and statut_precedent != StatutBC.VALIDE:
        comptables = get_users_par_role(RoleUtilisateur.COMPTABLE)
        if comptables:
            notifier(
                destinataires=comptables,
                type_notif=TypeNotification.BC_VALIDE,
                niveau=NiveauNotification.SUCCES,
                sujet=f"BC {instance.numero} valide - Paiement a preparer",
                message=f"BC {instance.numero} valide. Preparer paiement {instance.montant_ttc} F.",
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
            message=f"Le BC {instance.numero} (FEB {instance.fiche.numero}) a ete valide.",
            entite="BonCommande",
            entite_id=instance.pk,
            url_action=url_bc,
        )


# ═══════════════════════════════════════════════════════════════════
# ORDRE DE PAIEMENT — NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════
@receiver(post_save, sender=OrdrePaiement, dispatch_uid="notif_ordre")
def notifier_changement_ordre(sender, instance, created, **kwargs):
    statut_precedent = _statuts_precedents.pop(f"ordre_{instance.pk}", None)
    statut_actuel = instance.statut
    url_ordre = f"/paiements/ordre/{instance.pk}/"

    # Ordre de paiement cree -> notifier DG
    if created:
        destinataires = (
            get_users_par_role(RoleUtilisateur.DG)
            + get_users_par_role(RoleUtilisateur.ADMIN)
        )
        if destinataires:
            notifier(
                destinataires=destinataires,
                type_notif=TypeNotification.AVERTISSEMENT,
                niveau=NiveauNotification.AVERTISSEMENT,
                sujet=f"Visa requis : ordre {instance.numero}",
                message=(
                    f"{instance.dfc.nom_complet} a emis l'ordre de paiement "
                    f"{instance.numero} pour {instance.montant} F CFA "
                    f"(BC {instance.bc.numero}). Visa requis."
                ),
                expediteur=instance.dfc,
                entite="OrdrePaiement",
                entite_id=instance.pk,
                url_action=url_ordre,
                template_email="notifications/emails/ordre_paiement_emis.html",
                contexte_email={"ordre": instance, "url_ordre": url_absolue(url_ordre)},
            )
            logger.info("Notif ordre paiement %s emise (%d destinataires)",
                        instance.numero, len(destinataires))

    # Ordre vise par DG -> notifier comptable + DFC
    elif statut_actuel == StatutOrdrePaiement.VISA_OK and statut_precedent != StatutOrdrePaiement.VISA_OK:
        destinataires = (
            get_users_par_role(RoleUtilisateur.COMPTABLE)
            + [instance.dfc]
        )
        notifier(
            destinataires=destinataires,
            type_notif=TypeNotification.INFO,
            niveau=NiveauNotification.SUCCES,
            sujet=f"Visa accorde : ordre {instance.numero}",
            message=(
                f"Le DG a accorde le visa a l'ordre {instance.numero}. "
                f"Le paiement de {instance.montant} F CFA peut etre execute."
            ),
            expediteur=instance.dg,
            entite="OrdrePaiement",
            entite_id=instance.pk,
            url_action=url_ordre,
            template_email="notifications/emails/ordre_paiement_vise.html",
            contexte_email={"ordre": instance, "url_ordre": url_absolue(url_ordre)},
        )

    # Ordre rejete par DG -> notifier DFC
    elif statut_actuel == StatutOrdrePaiement.REJETE_DG and statut_precedent != StatutOrdrePaiement.REJETE_DG:
        notifier(
            destinataires=instance.dfc,
            type_notif=TypeNotification.AVERTISSEMENT,
            niveau=NiveauNotification.DANGER,
            sujet=f"Ordre {instance.numero} rejete par DG",
            message=(
                f"Le DG a rejete l'ordre {instance.numero}. "
                f"Motif : {instance.motif}"
            ),
            expediteur=instance.dg,
            entite="OrdrePaiement",
            entite_id=instance.pk,
            url_action=url_ordre,
        )


# ═══════════════════════════════════════════════════════════════════
# PAIEMENT EXECUTE — NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════
@receiver(post_save, sender=Paiement, dispatch_uid="notif_paiement")
def notifier_paiement_execute(sender, instance, created, **kwargs):
    statut_precedent = _statuts_precedents.pop(f"paiement_{instance.pk}", None)
    statut_actuel = instance.statut

    # Paiement nouvellement execute (PAYE ou ACOMPTE)
    if statut_actuel in (StatutPaiement.PAYE, StatutPaiement.ACOMPTE):
        if statut_precedent != statut_actuel:
            url_paiement = f"/paiements/{instance.pk}/"

            # Notifier DFC + Demandeur de la FEB
            destinataires = list(set([
                instance.ordre.dfc,
                instance.bc.fiche.demandeur,
            ]))

            niveau = NiveauNotification.SUCCES if statut_actuel == StatutPaiement.PAYE else NiveauNotification.INFO
            sujet_extra = "(Acompte)" if statut_actuel == StatutPaiement.ACOMPTE else "(Integral)"

            notifier(
                destinataires=destinataires,
                type_notif=TypeNotification.INFO,
                niveau=niveau,
                sujet=f"Paiement execute {sujet_extra} : {instance.numero}",
                message=(
                    f"Paiement de {instance.montant_verse} F CFA execute "
                    f"par {instance.comptable.nom_complet}. "
                    f"BC {instance.bc.numero}. "
                    + (f"Solde restant : {instance.solde_restant} F." if instance.solde_restant > 0 else "BC entierement paye.")
                ),
                expediteur=instance.comptable,
                entite="Paiement",
                entite_id=instance.pk,
                url_action=url_paiement,
            )

            # Email au FOURNISSEUR (acteur externe)
            if instance.bc.fournisseur.email:
                from .services import envoyer_email

                envoyer_email(
                    destinataire_email=instance.bc.fournisseur.email,
                    sujet=f"Confirmation paiement BC {instance.bc.numero}",
                    template_html="notifications/emails/paiement_fournisseur.html",
                    contexte={
                        "paiement": instance,
                        "bc": instance.bc,
                        "fournisseur": instance.bc.fournisseur,
                    },
                )
                logger.info(
                    "Email paiement envoye au fournisseur %s (%s)",
                    instance.bc.fournisseur.nom,
                    instance.bc.fournisseur.email,
                )

    # Paiement rejete -> notifier DFC + Comptable
    elif statut_actuel == StatutPaiement.REJETE and statut_precedent != StatutPaiement.REJETE:
        url_paiement = f"/paiements/{instance.pk}/"
        destinataires = list(set([
            instance.ordre.dfc,
            instance.comptable,
        ]))
        notifier(
            destinataires=destinataires,
            type_notif=TypeNotification.AVERTISSEMENT,
            niveau=NiveauNotification.DANGER,
            sujet=f"Paiement {instance.numero} REJETE",
            message=(
                f"Le paiement {instance.numero} a ete rejete. "
                f"Motif : {instance.motif_rejet}"
            ),
            entite="Paiement",
            entite_id=instance.pk,
            url_action=url_paiement,
        )