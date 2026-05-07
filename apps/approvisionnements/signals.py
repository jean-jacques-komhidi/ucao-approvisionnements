"""
Signaux de l'app approvisionnements.

- Numerotation auto FEB-AAAA-NNNN avant creation FEB.
- Numerotation auto BC-AAAA-NNNN avant creation BC.
"""
import logging
from datetime import datetime

from django.db.models import Max
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import BonCommande, FicheExpression

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=FicheExpression, dispatch_uid="generer_numero_feb")
def generer_numero_feb(sender, instance, **kwargs):
    """Genere le numero FEB-AAAA-NNNN a la creation."""
    if not instance.pk and not instance.numero:
        annee = datetime.now().year
        prefixe = f"FEB-{annee}-"

        derniere = (
            FicheExpression.objects
            .filter(numero__startswith=prefixe)
            .aggregate(Max("numero"))
        )

        max_numero = derniere["numero__max"]
        if max_numero:
            try:
                num = int(max_numero.split("-")[-1])
                instance.numero = f"{prefixe}{num + 1:04d}"
            except (ValueError, IndexError):
                instance.numero = f"{prefixe}0001"
        else:
            instance.numero = f"{prefixe}0001"

        logger.info("Numero FEB attribue : %s", instance.numero)


@receiver(pre_save, sender=BonCommande, dispatch_uid="generer_numero_bc")
def generer_numero_bc(sender, instance, **kwargs):
    """Genere le numero BC-AAAA-NNNN a la creation."""
    if not instance.pk and not instance.numero:
        annee = datetime.now().year
        prefixe = f"BC-{annee}-"

        derniere = (
            BonCommande.objects
            .filter(numero__startswith=prefixe)
            .aggregate(Max("numero"))
        )

        max_numero = derniere["numero__max"]
        if max_numero:
            try:
                num = int(max_numero.split("-")[-1])
                instance.numero = f"{prefixe}{num + 1:04d}"
            except (ValueError, IndexError):
                instance.numero = f"{prefixe}0001"
        else:
            instance.numero = f"{prefixe}0001"

        logger.info("Numero BC attribue : %s", instance.numero)