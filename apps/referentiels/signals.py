"""
Signaux de l'app referentiels.

- Genere automatiquement le code fournisseur (F0001, F0002...) avant creation.
- Force qu'une seule devise soit principale.
"""
import logging
from datetime import timedelta

from django.db.models.signals import  post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone


from .models import Devise, Fournisseur

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Code fournisseur automatique : F0001, F0002...
# ═══════════════════════════════════════════════════════════════════
@receiver(pre_save, sender=Fournisseur, dispatch_uid="generer_code_fournisseur")
def generer_code_fournisseur(sender, instance, **kwargs):
    """
    Genere le code fournisseur a la creation (jamais modifie ensuite).
    """
    if not instance.pk and not instance.code:
        instance.code = Fournisseur.objects.prochain_code()
        logger.info("Code fournisseur attribue : %s pour %s", instance.code, instance.nom)


# ═══════════════════════════════════════════════════════════════════
# Une seule devise principale
# ═══════════════════════════════════════════════════════════════════
@receiver(pre_save, sender=Devise, dispatch_uid="forcer_unicite_devise_principale")
def forcer_unicite_devise_principale(sender, instance, **kwargs):
    """
    Si la devise est marquee comme principale, retire le statut aux autres.
    """
    if instance.est_devise_principale:
        Devise.objects.exclude(pk=instance.pk).filter(
            est_devise_principale=True
        ).update(est_devise_principale=False)
        logger.info("Devise principale changee : %s", instance.code)
    
# ═══════════════════════════════════════════════════════════════════
# DETECTION RUPTURE STOCK -> GENERATION AUTO FEB DRAFT
# ═══════════════════════════════════════════════════════════════════
_stock_precedent = {}


@receiver(pre_save, sender="referentiels.Article")
def memoriser_stock_precedent(sender, instance, **kwargs):
    """Memorise le stock avant modification pour detecter le passage sous seuil."""
    if instance.pk:
        try:
            ancien = sender.objects.get(pk=instance.pk)
            _stock_precedent[instance.pk] = ancien.quantite_stock
        except sender.DoesNotExist:
            _stock_precedent[instance.pk] = None
    else:
        _stock_precedent[instance.pk] = None


@receiver(post_save, sender="referentiels.Article")
def detecter_passage_sous_seuil(sender, instance, created, **kwargs):
    """
    Detecte si l'article vient de passer sous son seuil d'alerte.

    Si oui, genere automatiquement une FEB DRAFT.
    """
    if created or not instance.gestion_stock_active or instance.seuil_alerte <= 0:
        return

    stock_precedent = _stock_precedent.pop(instance.pk, None)
    if stock_precedent is None:
        return

    # Detection : on vient de passer SOUS le seuil
    vient_de_passer = (
        stock_precedent > instance.seuil_alerte
        and instance.quantite_stock <= instance.seuil_alerte
    )

    # Anti-spam : ne pas re-alerter si deja alerte dans les 24h
    derniere = instance.derniere_alerte
    if derniere and (timezone.now() - derniere) < timedelta(hours=24):
        return

    if vient_de_passer or (instance.est_sous_seuil and not derniere):
        logger.warning(
            "Article '%s' passe sous seuil (%d <= %d). Generation FEB DRAFT...",
            instance.designation,
            instance.quantite_stock,
            instance.seuil_alerte,
        )

        # Genere FEB DRAFT (attribue au premier Resp.Appro disponible)
        from apps.comptes.models import RoleUtilisateur, Utilisateur
        from .services import generer_feb_draft_pour_rupture

        demandeur = Utilisateur.objects.filter(
            role=RoleUtilisateur.RESP_APPRO, est_actif=True
        ).first()

        if demandeur:
            feb = generer_feb_draft_pour_rupture(instance, demandeur)

            if feb:
                # Notification au Resp.Appro
                from apps.notifications.models import NiveauNotification, TypeNotification
                from apps.notifications.services import notifier

                notifier(
                    destinataires=demandeur,
                    type_notif=TypeNotification.AVERTISSEMENT,
                    niveau=NiveauNotification.AVERTISSEMENT,
                    sujet=f"⚠️ Stock bas : {instance.designation}",
                    message=(
                        f"L'article '{instance.designation}' est passe sous son seuil d'alerte "
                        f"(stock actuel : {instance.quantite_stock}, seuil : {instance.seuil_alerte}). "
                        f"Une FEB DRAFT a ete generee automatiquement : {feb.numero}. "
                        f"Veuillez la consulter, ajuster si necessaire et la soumettre."
                    ),
                    entite="FicheExpression",
                    entite_id=feb.pk,
                    url_action=f"/feb/{feb.pk}/",
                )