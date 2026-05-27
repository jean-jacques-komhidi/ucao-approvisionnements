"""Services metier des referentiels - gestion de stock."""
import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@transaction.atomic
def ajuster_stock(article, quantite_delta, utilisateur, motif=""):
    """
    Ajuste le stock d'un article.

    Args:
        article: Instance Article
        quantite_delta: int (positif = entree, negatif = sortie)
        utilisateur: Utilisateur effectuant l'action
        motif: Texte explicatif

    Returns:
        Article: instance a jour
    """
    ancien_stock = article.quantite_stock
    article.quantite_stock = max(0, article.quantite_stock + quantite_delta)
    article.save(update_fields=["quantite_stock"])

    logger.info(
        "Stock article '%s' : %d -> %d (delta: %+d) par %s | motif: %s",
        article.designation,
        ancien_stock,
        article.quantite_stock,
        quantite_delta,
        utilisateur.identifiant,
        motif or "—",
    )

    return article


def detecter_articles_sous_seuil():
    """Retourne les articles dont le stock est <= seuil d'alerte."""
    from .models import Article

    return Article.objects.filter(
        est_actif=True,
        gestion_stock_active=True,
        seuil_alerte__gt=0,
    ).filter(quantite_stock__lte=models.F("seuil_alerte"))


@transaction.atomic
def generer_feb_draft_pour_rupture(article, demandeur):
    """
    Genere une FEB DRAFT automatique pour un article en rupture/sous seuil.

    Verifie qu'il n'y a pas deja une FEB EN_INSTANCE ou DRAFT pour cet article.

    Args:
        article: Instance Article
        demandeur: Utilisateur Resp.Appro

    Returns:
        FicheExpression | None
    """
    from apps.approvisionnements.models import (
        FicheExpression, LigneFiche, OrigineFEB,
        StatutFEB, TypeLigne,
    )
    from apps.referentiels.models import Fournisseur

    # Verifier qu'il n'y a pas deja une FEB en cours pour cet article
    existe_deja = (
        FicheExpression.objects.non_supprimees()
        .filter(
            lignes__article=article,
            statut__in=[StatutFEB.DRAFT, StatutFEB.EN_INSTANCE],
        )
        .exists()
    )

    if existe_deja:
        logger.info(
            "FEB DRAFT non generee pour '%s' : FEB en cours existe deja",
            article.designation,
        )
        return None

    # Recupere un fournisseur par defaut (le premier)
    fournisseur = Fournisseur.objects.actifs().first()
    if not fournisseur:
        logger.warning("Pas de fournisseur disponible pour FEB DRAFT auto")
        return None

    # Cree la FEB DRAFT
    quantite = article.quantite_a_commander or 10
    # Prix unitaire par defaut (on prend la moyenne des FEB precedentes ou 0)
    from django.db.models import Avg
    prix_moyen = (
        LigneFiche.objects.filter(article=article)
        .aggregate(moy=Avg("prix_unitaire"))["moy"]
    )
    prix_unitaire = prix_moyen or Decimal("10000.00")

    feb = FicheExpression.objects.create(
        demandeur=demandeur,
        fournisseur=fournisseur,
        objet=f"[AUTO] Reapprovisionnement : {article.designation}",
        statut=StatutFEB.DRAFT,
        origine=OrigineFEB.PREDICTION if hasattr(OrigineFEB, "PREDICTION") else OrigineFEB.MANUELLE,
        est_auto=True,
        taux_tva=Decimal("18.00"),
    )

    LigneFiche.objects.create(
        fiche=feb,
        type_ligne=TypeLigne.ARTICLE,
        article=article,
        quantite=quantite,
        prix_unitaire=prix_unitaire,
    )

    # Recalcul des totaux
    feb.calculer_totaux()

    # Marque l'article comme ayant declenche une alerte
    article.derniere_alerte = timezone.now()
    article.save(update_fields=["derniere_alerte"])

    logger.warning(
        "FEB DRAFT AUTO generee : %s pour article '%s' (stock: %d, seuil: %d)",
        feb.numero, article.designation,
        article.quantite_stock, article.seuil_alerte,
    )

    return feb