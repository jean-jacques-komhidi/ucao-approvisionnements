"""Signaux de l'app approvisionnements."""
import logging
from datetime import datetime

from django.db.models import Max
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import BonCommande, FicheExpression, OrdrePaiement, Paiement

logger = logging.getLogger(__name__)


def _generer_numero(prefixe, annee, modele):
    """Genere un numero auto-incremente PREFIXE-AAAA-NNNN."""
    pattern = f"{prefixe}-{annee}-"
    derniere = (
        modele.objects
        .filter(numero__startswith=pattern)
        .aggregate(Max("numero"))
    )

    max_numero = derniere["numero__max"]
    if max_numero:
        try:
            num = int(max_numero.split("-")[-1])
            return f"{pattern}{num + 1:04d}"
        except (ValueError, IndexError):
            return f"{pattern}0001"
    return f"{pattern}0001"


@receiver(pre_save, sender=FicheExpression, dispatch_uid="generer_numero_feb")
def generer_numero_feb(sender, instance, **kwargs):
    if not instance.pk and not instance.numero:
        annee = datetime.now().year
        instance.numero = _generer_numero("FEB", annee, FicheExpression)
        logger.info("Numero FEB attribue : %s", instance.numero)


@receiver(pre_save, sender=BonCommande, dispatch_uid="generer_numero_bc")
def generer_numero_bc(sender, instance, **kwargs):
    if not instance.pk and not instance.numero:
        annee = datetime.now().year
        instance.numero = _generer_numero("BC", annee, BonCommande)
        logger.info("Numero BC attribue : %s", instance.numero)


@receiver(pre_save, sender=OrdrePaiement, dispatch_uid="generer_numero_op")
def generer_numero_op(sender, instance, **kwargs):
    if not instance.pk and not instance.numero:
        annee = datetime.now().year
        instance.numero = _generer_numero("OP", annee, OrdrePaiement)
        logger.info("Numero OP attribue : %s", instance.numero)


@receiver(pre_save, sender=Paiement, dispatch_uid="generer_numero_pay")
def generer_numero_paiement(sender, instance, **kwargs):
    if not instance.pk and not instance.numero:
        annee = datetime.now().year
        instance.numero = _generer_numero("PAY", annee, Paiement)
        logger.info("Numero Paiement attribue : %s", instance.numero)