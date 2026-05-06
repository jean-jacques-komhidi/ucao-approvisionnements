"""
Signaux de l'app approvisionnements.

- Numerotation automatique FEB-AAAA-NNNN avant creation.
"""
import logging
from datetime import datetime

from django.db.models import Max
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import FicheExpression

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=FicheExpression, dispatch_uid="generer_numero_feb")
def generer_numero_feb(sender, instance, **kwargs):
    """
    Genere le numero FEB-AAAA-NNNN a la creation.

    NNNN reset chaque annee (ex : FEB-2025-0001 puis FEB-2026-0001).
    """
    if not instance.pk and not instance.numero:
        annee = datetime.now().year
        prefixe = f"FEB-{annee}-"

        # Trouve le numero le plus eleve pour cette annee
        derniere_feb = (
            FicheExpression.objects
            .filter(numero__startswith=prefixe)
            .aggregate(Max("numero"))
        )

        max_numero = derniere_feb["numero__max"]
        if max_numero:
            try:
                num = int(max_numero.split("-")[-1])
                instance.numero = f"{prefixe}{num + 1:04d}"
            except (ValueError, IndexError):
                instance.numero = f"{prefixe}0001"
        else:
            instance.numero = f"{prefixe}0001"

        logger.info("Numero FEB attribue : %s", instance.numero)