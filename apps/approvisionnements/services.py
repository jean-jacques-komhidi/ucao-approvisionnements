"""Services metier de l'app approvisionnements."""
import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from .models import (
    BonCommande,
    FicheExpression,
    OrdrePaiement,
    Paiement,
    StatutBC,
    StatutPaiement,
)

logger = logging.getLogger(__name__)


@transaction.atomic
def generer_bc_depuis_feb(feb: FicheExpression) -> BonCommande:
    """Genere un BC depuis une FEB validee."""
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
        "BC %s genere depuis FEB %s (TTC : %s)",
        bc.numero, feb.numero, feb.montant_ttc,
    )
    return bc


def calculer_solde_restant(bc: BonCommande) -> Decimal:
    """
    Calcule le solde restant a payer pour un BC.

    Returns:
        Decimal : solde = montant_ttc_BC - somme(paiements PAYE/ACOMPTE)
    """
    total_paye = (
        Paiement.objects
        .filter(bc=bc)
        .filter(statut__in=[StatutPaiement.PAYE, StatutPaiement.ACOMPTE])
        .aggregate(total=Sum("montant_verse"))["total"]
        or Decimal("0.00")
    )
    return bc.montant_ttc - total_paye


@transaction.atomic
def executer_paiement(paiement: Paiement) -> Paiement:
    """
    Execute un paiement et determine son statut final.

    Regles :
    - Si montant_verse <= 0 : REJETE
    - Si montant_verse > solde_restant : REJETE (surpaiement)
    - Si montant_verse == solde_restant : PAYE
    - Sinon : ACOMPTE (paiement partiel)

    Args:
        paiement: instance Paiement non encore executee

    Returns:
        Paiement : avec statut + solde_restant a jour
    """
    from django.utils import timezone

    bc = paiement.bc
    solde_actuel = calculer_solde_restant(bc) + paiement.montant_verse  # avant ce paiement

    # Verification montant
    if paiement.montant_verse <= 0:
        paiement.statut = StatutPaiement.REJETE
        paiement.motif_rejet = "Le montant verse doit etre superieur a 0."
        paiement.solde_restant = solde_actuel
        paiement.save()
        logger.warning("Paiement %s rejete : montant <= 0", paiement.numero)
        return paiement

    if paiement.montant_verse > solde_actuel:
        paiement.statut = StatutPaiement.REJETE
        paiement.motif_rejet = (
            f"Surpaiement detecte : montant_verse ({paiement.montant_verse}) "
            f"superieur au solde restant ({solde_actuel})."
        )
        paiement.solde_restant = solde_actuel
        paiement.save()
        logger.warning("Paiement %s rejete : surpaiement", paiement.numero)
        return paiement

    # Calcul du solde apres ce paiement
    nouveau_solde = solde_actuel - paiement.montant_verse

    if nouveau_solde == 0:
        # Paiement integral
        paiement.statut = StatutPaiement.PAYE
        paiement.est_acompte = False
    else:
        # Paiement partiel
        paiement.statut = StatutPaiement.ACOMPTE
        paiement.est_acompte = True

    paiement.solde_restant = nouveau_solde
    paiement.date_execution = timezone.now()
    paiement.save()

    logger.info(
        "Paiement %s execute : %s F (%s) - Solde restant : %s F",
        paiement.numero,
        paiement.montant_verse,
        paiement.statut,
        nouveau_solde,
    )

    return paiement