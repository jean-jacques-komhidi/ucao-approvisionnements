"""
Services metier de l'app approvisionnements.

Fonctions reutilisables qui encapsulent la logique :
- generer_bc_depuis_feb : genere un BC depuis une FEB (transaction atomique)
"""
import logging

from django.db import transaction

from .models import BonCommande, FicheExpression, StatutBC

logger = logging.getLogger(__name__)


@transaction.atomic
def generer_bc_depuis_feb(feb: FicheExpression) -> BonCommande:
    """
    Genere un Bon de Commande a partir d'une FEB validee.

    Utilise @transaction.atomic : si une etape echoue, tout est annule.

    Args:
        feb: FEB validee dont le montant > seuil BC

    Returns:
        BonCommande : le BC nouvellement cree

    Raises:
        ValueError : si la FEB n'est pas dans un etat permettant la generation BC
    """
    # Verifier que la FEB peut generer un BC
    if hasattr(feb, "bon_commande"):
        logger.warning(
            "FEB %s a deja un BC associe (%s)",
            feb.numero, feb.bon_commande.numero,
        )
        return feb.bon_commande

    if not feb.est_au_dela_du_seuil:
        raise ValueError(
            f"FEB {feb.numero} en dessous du seuil BC ({feb.montant_ttc} F CFA)"
        )

    # Creer le BC
    bc = BonCommande.objects.create(
        fiche=feb,
        fournisseur=feb.fournisseur,
        statut=StatutBC.EN_INSTANCE,
        montant_ht=feb.montant_ht,
        taux_tva=feb.taux_tva,
        montant_tva=feb.montant_tva,
        montant_ttc=feb.montant_ttc,
        est_verrouille=True,
    )

    logger.info(
        "BC %s genere automatiquement depuis FEB %s (TTC : %s)",
        bc.numero, feb.numero, feb.montant_ttc,
    )

    return bc