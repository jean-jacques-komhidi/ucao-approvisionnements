"""
Signaux de l'app referentiels.

- Genere automatiquement le code fournisseur (F0001, F0002...) avant creation.
- Force qu'une seule devise soit principale.
"""
import logging

from django.db.models.signals import pre_save
from django.dispatch import receiver

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