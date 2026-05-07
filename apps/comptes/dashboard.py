"""
Service de calcul des donnees du tableau de bord.

Adapte les KPI et statistiques selon le role de l'utilisateur connecte.
"""
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

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
from apps.referentiels.models import Article, Fournisseur, ServiceExterieur

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# CONSTRUCTION DES KPI SELON LE ROLE
# ═══════════════════════════════════════════════════════════════════
def construire_kpi(utilisateur):
    """
    Retourne une liste de KPI adaptee au role de l'utilisateur.

    Chaque KPI est un dict avec :
    - label : titre
    - valeur : valeur principale
    - detail : sous-texte (optionnel)
    - icone : nom Lucide
    - couleur : bleu / vert / violet / jaune / gris
    - lien : URL associee (optionnel)
    """
    role = utilisateur.role
    kpi = []

    # ─── DEMANDEUR (Resp.Appro, Chef CCE, Chef SLMG) ─────────
    if role in (RoleUtilisateur.RESP_APPRO, RoleUtilisateur.CHEF_CCE, RoleUtilisateur.CHEF_SLMG):
        mes_feb = FicheExpression.objects.mes_feb(utilisateur)
        en_instance = mes_feb.filter(statut=StatutFEB.EN_INSTANCE).count()
        validees = mes_feb.filter(statut=StatutFEB.VALIDEE).count()
        cloturees = mes_feb.filter(statut=StatutFEB.CLOTUREE).count()
        rejetees = mes_feb.filter(statut=StatutFEB.REJETEE).count()
        montant_total = (
            mes_feb.filter(statut__in=[StatutFEB.VALIDEE, StatutFEB.CLOTUREE])
            .aggregate(total=Sum("montant_ttc"))["total"]
            or Decimal("0")
        )

        kpi = [
            {
                "label": "Mes FEB en instance",
                "valeur": en_instance,
                "detail": "en attente de validation",
                "icone": "clock",
                "couleur": "jaune",
                "lien": "/feb/?statut=EN_INSTANCE",
            },
            {
                "label": "Mes FEB validees",
                "valeur": validees + cloturees,
                "detail": f"{validees} validees + {cloturees} cloturees",
                "icone": "check-circle-2",
                "couleur": "vert",
                "lien": "/feb/?statut=VALIDEE",
            },
            {
                "label": "Mes FEB rejetees",
                "valeur": rejetees,
                "detail": "necessitent correction",
                "icone": "x-circle",
                "couleur": "gris",
                "lien": "/feb/?statut=REJETEE",
            },
            {
                "label": "Total accorde",
                "valeur": format_fcfa(montant_total),
                "detail": "F CFA cumules",
                "icone": "trending-up",
                "couleur": "violet",
            },
        ]

    # ─── CG / DFC : valideurs FEB ─────────────────────────────
    elif role == RoleUtilisateur.CG:
        feb_a_valider = FicheExpression.objects.en_instance().count()
        feb_validees_mois = (
            FicheExpression.objects.non_supprimees()
            .filter(statut=StatutFEB.VALIDEE, validateur=utilisateur)
            .filter(date_validation__month=timezone.now().month)
            .count()
        )
        montant_valide_mois = (
            FicheExpression.objects.non_supprimees()
            .filter(validateur=utilisateur, date_validation__month=timezone.now().month)
            .aggregate(total=Sum("montant_ttc"))["total"]
            or Decimal("0")
        )

        kpi = [
            {
                "label": "FEB a valider",
                "valeur": feb_a_valider,
                "detail": "en attente",
                "icone": "clock",
                "couleur": "jaune",
                "lien": "/feb/?statut=EN_INSTANCE",
            },
            {
                "label": "Validees ce mois",
                "valeur": feb_validees_mois,
                "detail": "par vous",
                "icone": "check-circle-2",
                "couleur": "vert",
            },
            {
                "label": "Montant valide ce mois",
                "valeur": format_fcfa(montant_valide_mois),
                "detail": "F CFA",
                "icone": "trending-up",
                "couleur": "violet",
            },
            {
                "label": "BC actifs",
                "valeur": BonCommande.objects.non_supprimes().count(),
                "detail": "tous statuts",
                "icone": "clipboard-list",
                "couleur": "bleu",
                "lien": "/bc/",
            },
        ]

    # ─── DFC ─────────────────────────────────────────────────
    elif role == RoleUtilisateur.DFC:
        feb_a_valider = FicheExpression.objects.en_instance().count()
        bc_a_valider = BonCommande.objects.en_instance().count()
        ordres_emis = OrdrePaiement.objects.filter(dfc=utilisateur).count()
        bc_a_payer = BonCommande.objects.a_payer().count()

        kpi = [
            {
                "label": "FEB a valider",
                "valeur": feb_a_valider,
                "icone": "file-text",
                "couleur": "jaune",
                "lien": "/feb/?statut=EN_INSTANCE",
            },
            {
                "label": "BC a valider",
                "valeur": bc_a_valider,
                "icone": "clipboard-list",
                "couleur": "violet",
                "lien": "/bc/?statut=EN_INSTANCE",
            },
            {
                "label": "BC a payer",
                "valeur": bc_a_payer,
                "detail": "ordres a emettre",
                "icone": "wallet",
                "couleur": "bleu",
                "lien": "/paiements/bc-a-payer/",
            },
            {
                "label": "Mes ordres emis",
                "valeur": ordres_emis,
                "icone": "send",
                "couleur": "vert",
                "lien": "/paiements/ordres/",
            },
        ]

    # ─── DG ──────────────────────────────────────────────────
    elif role == RoleUtilisateur.DG:
        bc_a_valider = BonCommande.objects.en_instance().count()
        ordres_a_viser = OrdrePaiement.objects.filter(
            statut=StatutOrdrePaiement.EN_ATTENTE_VISA
        ).count()
        montant_engagement = (
            BonCommande.objects.valides()
            .aggregate(total=Sum("montant_ttc"))["total"]
            or Decimal("0")
        )

        kpi = [
            {
                "label": "BC a valider",
                "valeur": bc_a_valider,
                "icone": "clipboard-list",
                "couleur": "jaune",
                "lien": "/bc/?statut=EN_INSTANCE",
            },
            {
                "label": "Ordres a viser",
                "valeur": ordres_a_viser,
                "detail": "visa requis",
                "icone": "shield-check",
                "couleur": "violet",
                "lien": "/paiements/ordres/?statut=EN_ATTENTE_VISA",
            },
            {
                "label": "Engagement total",
                "valeur": format_fcfa(montant_engagement),
                "detail": "F CFA (BC valides)",
                "icone": "trending-up",
                "couleur": "vert",
            },
            {
                "label": "BC valides",
                "valeur": BonCommande.objects.valides().count(),
                "icone": "check-circle-2",
                "couleur": "bleu",
            },
        ]

    # ─── COMPTABLE ──────────────────────────────────────────
    elif role == RoleUtilisateur.COMPTABLE:
        ordres_vises = OrdrePaiement.objects.filter(
            statut=StatutOrdrePaiement.VISA_OK
        ).count()
        bc_a_payer = BonCommande.objects.a_payer().count()
        debut_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0)
        paye_ce_mois = (
            Paiement.objects.filter(
                statut=StatutPaiement.PAYE, date_execution__gte=debut_mois
            )
            .aggregate(total=Sum("montant_verse"))["total"]
            or Decimal("0")
        )
        nb_paiements_executes = Paiement.objects.filter(
            comptable=utilisateur, statut=StatutPaiement.PAYE
        ).count()

        kpi = [
            {
                "label": "Ordres a executer",
                "valeur": ordres_vises,
                "detail": "vises par DG",
                "icone": "banknote",
                "couleur": "jaune",
                "lien": "/paiements/ordres/?statut=VISA_OK",
            },
            {
                "label": "BC a payer",
                "valeur": bc_a_payer,
                "icone": "wallet",
                "couleur": "violet",
                "lien": "/paiements/bc-a-payer/",
            },
            {
                "label": "Paye ce mois",
                "valeur": format_fcfa(paye_ce_mois),
                "detail": "F CFA",
                "icone": "trending-up",
                "couleur": "vert",
            },
            {
                "label": "Mes paiements",
                "valeur": nb_paiements_executes,
                "detail": "executes au total",
                "icone": "check-circle-2",
                "couleur": "bleu",
                "lien": "/paiements/historique/",
            },
        ]

    # ─── ADMIN ──────────────────────────────────────────────
    elif role == RoleUtilisateur.ADMIN:
        from apps.comptes.models import Utilisateur

        nb_users = Utilisateur.objects.filter(est_actif=True).count()
        nb_articles = Article.objects.filter(est_actif=True).count()
        nb_fournisseurs = Fournisseur.objects.filter(est_actif=True).count()
        nb_feb_actives = (
            FicheExpression.objects.non_supprimees().count()
        )

        kpi = [
            {
                "label": "Utilisateurs actifs",
                "valeur": nb_users,
                "icone": "users",
                "couleur": "bleu",
            },
            {
                "label": "Articles catalogue",
                "valeur": nb_articles,
                "icone": "package",
                "couleur": "violet",
                "lien": "/referentiels/articles/",
            },
            {
                "label": "Fournisseurs",
                "valeur": nb_fournisseurs,
                "icone": "building-2",
                "couleur": "vert",
                "lien": "/referentiels/fournisseurs/",
            },
            {
                "label": "FEB actives",
                "valeur": nb_feb_actives,
                "icone": "file-text",
                "couleur": "jaune",
                "lien": "/feb/",
            },
        ]

    return kpi


# ═══════════════════════════════════════════════════════════════════
# DONNEES POUR GRAPHIQUES
# ═══════════════════════════════════════════════════════════════════
def construire_graphiques(utilisateur):
    """Prepare les donnees JSON pour les 4 graphiques Chart.js."""
    role = utilisateur.role

    # Determine le scope des FEB selon le role
    if role in (RoleUtilisateur.RESP_APPRO, RoleUtilisateur.CHEF_CCE, RoleUtilisateur.CHEF_SLMG):
        feb_qs = FicheExpression.objects.mes_feb(utilisateur)
    else:
        feb_qs = FicheExpression.objects.non_supprimees()

    # ─── 1. Montants par mois (line chart, 6 derniers mois) ──
    montants_mois = _montants_par_mois(feb_qs, nb_mois=6)

    # ─── 2. Repartition par statut FEB (doughnut chart) ──────
    repartition_statuts = _repartition_statuts_feb(feb_qs)

    # ─── 3. Top 5 fournisseurs (bar chart) ───────────────────
    top_fournisseurs = _top_fournisseurs(feb_qs)

    # ─── 4. Evolution paiements (area chart, 6 derniers mois)─
    evolution_paiements = _evolution_paiements(nb_mois=6)

    return {
        "montants_mois": json.dumps(montants_mois),
        "repartition_statuts": json.dumps(repartition_statuts),
        "top_fournisseurs": json.dumps(top_fournisseurs),
        "evolution_paiements": json.dumps(evolution_paiements),
    }


def _montants_par_mois(feb_qs, nb_mois=6):
    """Calcule les montants TTC valides par mois sur les N derniers mois."""
    aujourd_hui = timezone.now()
    debut = (aujourd_hui - timedelta(days=nb_mois * 31)).replace(day=1)

    feb_filtrees = feb_qs.filter(
        statut__in=[StatutFEB.VALIDEE, StatutFEB.CLOTUREE],
        date_validation__gte=debut,
    )

    # Groupe par (annee, mois)
    par_mois = defaultdict(Decimal)
    for feb in feb_filtrees:
        if feb.date_validation:
            cle = feb.date_validation.strftime("%Y-%m")
            par_mois[cle] += feb.montant_ttc

    # Genere les 6 derniers mois (meme si vides)
    labels = []
    valeurs = []
    mois_fr = ["Jan", "Fev", "Mar", "Avr", "Mai", "Jun",
               "Jui", "Aou", "Sep", "Oct", "Nov", "Dec"]
    for i in range(nb_mois - 1, -1, -1):
        date = aujourd_hui.replace(day=1) - timedelta(days=i * 31)
        cle = date.strftime("%Y-%m")
        labels.append(f"{mois_fr[date.month - 1]} {date.year}")
        valeurs.append(float(par_mois.get(cle, 0)))

    return {"labels": labels, "valeurs": valeurs}


def _repartition_statuts_feb(feb_qs):
    """Repartition des FEB par statut (pour doughnut chart)."""
    stats = (
        feb_qs.values("statut")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # Mapping label -> couleur
    couleurs_statuts = {
        StatutFEB.DRAFT: "#9CA3AF",
        StatutFEB.EN_INSTANCE: "#F59E0B",
        StatutFEB.VALIDEE: "#059669",
        StatutFEB.CLOTUREE: "#10B981",
        StatutFEB.REJETEE: "#DC2626",
        StatutFEB.MODIFIEE: "#3B82F6",
        StatutFEB.SUPPRIMEE: "#6B7280",
    }

    labels_statuts = dict(StatutFEB.choices)

    labels = []
    valeurs = []
    couleurs = []
    for stat in stats:
        labels.append(labels_statuts.get(stat["statut"], stat["statut"]))
        valeurs.append(stat["count"])
        couleurs.append(couleurs_statuts.get(stat["statut"], "#9CA3AF"))

    return {"labels": labels, "valeurs": valeurs, "couleurs": couleurs}


def _top_fournisseurs(feb_qs, limit=5):
    """Top 5 des fournisseurs par montant cumule."""
    stats = (
        feb_qs.filter(statut__in=[StatutFEB.VALIDEE, StatutFEB.CLOTUREE])
        .values("fournisseur__nom")
        .annotate(total=Sum("montant_ttc"), count=Count("id"))
        .order_by("-total")[:limit]
    )

    labels = [s["fournisseur__nom"][:25] for s in stats]
    valeurs = [float(s["total"] or 0) for s in stats]

    return {"labels": labels, "valeurs": valeurs}


def _evolution_paiements(nb_mois=6):
    """Evolution des paiements executes par mois."""
    aujourd_hui = timezone.now()
    debut = (aujourd_hui - timedelta(days=nb_mois * 31)).replace(day=1)

    paiements = Paiement.objects.filter(
        statut=StatutPaiement.PAYE, date_execution__gte=debut
    )

    par_mois = defaultdict(Decimal)
    for p in paiements:
        if p.date_execution:
            cle = p.date_execution.strftime("%Y-%m")
            par_mois[cle] += p.montant_verse

    labels = []
    valeurs = []
    mois_fr = ["Jan", "Fev", "Mar", "Avr", "Mai", "Jun",
               "Jui", "Aou", "Sep", "Oct", "Nov", "Dec"]
    for i in range(nb_mois - 1, -1, -1):
        date = aujourd_hui.replace(day=1) - timedelta(days=i * 31)
        cle = date.strftime("%Y-%m")
        labels.append(f"{mois_fr[date.month - 1]} {date.year}")
        valeurs.append(float(par_mois.get(cle, 0)))

    return {"labels": labels, "valeurs": valeurs}


# ═══════════════════════════════════════════════════════════════════
# ACTIVITES RECENTES
# ═══════════════════════════════════════════════════════════════════
def construire_activites_recentes(utilisateur, limit=8):
    """Liste des derniers events selon le role."""
    role = utilisateur.role
    activites = []

    # Demandeur : ses propres FEB
    if role in (RoleUtilisateur.RESP_APPRO, RoleUtilisateur.CHEF_CCE, RoleUtilisateur.CHEF_SLMG):
        feb_qs = FicheExpression.objects.mes_feb(utilisateur)[:limit]
        for feb in feb_qs:
            activites.append({
                "type": "FEB",
                "icone": "file-text",
                "titre": feb.numero,
                "description": feb.objet,
                "statut": feb.get_statut_display(),
                "couleur": feb.couleur_statut,
                "date": feb.date_creation,
                "url": f"/feb/{feb.pk}/",
                "montant": feb.montant_ttc,
            })

    # CG / DFC / DG / Admin : toutes les FEB recentes
    elif role in (RoleUtilisateur.CG, RoleUtilisateur.DFC, RoleUtilisateur.DG, RoleUtilisateur.ADMIN):
        feb_qs = FicheExpression.objects.non_supprimees().select_related(
            "demandeur", "fournisseur"
        )[:limit]
        for feb in feb_qs:
            activites.append({
                "type": "FEB",
                "icone": "file-text",
                "titre": feb.numero,
                "description": f"{feb.demandeur.nom_complet} • {feb.objet[:50]}",
                "statut": feb.get_statut_display(),
                "couleur": feb.couleur_statut,
                "date": feb.date_creation,
                "url": f"/feb/{feb.pk}/",
                "montant": feb.montant_ttc,
            })

    # Comptable : derniers paiements
    elif role == RoleUtilisateur.COMPTABLE:
        paiements_qs = Paiement.objects.select_related("bc", "bc__fournisseur")[:limit]
        for p in paiements_qs:
            activites.append({
                "type": "PAIEMENT",
                "icone": "banknote",
                "titre": p.numero,
                "description": f"{p.bc.numero} • {p.bc.fournisseur.nom[:30]}",
                "statut": p.get_statut_display(),
                "couleur": p.couleur_statut,
                "date": p.date_creation,
                "url": f"/paiements/{p.pk}/",
                "montant": p.montant_verse,
            })

    return activites


# ═══════════════════════════════════════════════════════════════════
# ALERTES INTELLIGENTES
# ═══════════════════════════════════════════════════════════════════
def construire_alertes(utilisateur):
    """Genere des alertes contextuelles selon le role."""
    role = utilisateur.role
    alertes = []

    # FEB en attente depuis +5 jours (CG / DFC / Admin)
    if role in (RoleUtilisateur.CG, RoleUtilisateur.DFC, RoleUtilisateur.ADMIN):
        seuil = timezone.now() - timedelta(days=5)
        feb_anciennes = FicheExpression.objects.en_instance().filter(
            date_creation__lt=seuil
        ).count()
        if feb_anciennes > 0:
            alertes.append({
                "icone": "alert-triangle",
                "couleur": "warning",
                "message": f"{feb_anciennes} FEB en attente depuis plus de 5 jours",
                "lien": "/feb/?statut=EN_INSTANCE",
            })

    # BC valides non payes depuis +7 jours (DFC / Comptable)
    if role in (RoleUtilisateur.DFC, RoleUtilisateur.COMPTABLE, RoleUtilisateur.ADMIN):
        seuil = timezone.now() - timedelta(days=7)
        bc_anciens = BonCommande.objects.a_payer().filter(date_validation__lt=seuil).count()
        if bc_anciens > 0:
            alertes.append({
                "icone": "alert-circle",
                "couleur": "error",
                "message": f"{bc_anciens} BC valides depuis +7 jours sans paiement",
                "lien": "/paiements/bc-a-payer/",
            })

    # FEB rejetees pour le demandeur
    if role in (RoleUtilisateur.RESP_APPRO, RoleUtilisateur.CHEF_CCE, RoleUtilisateur.CHEF_SLMG):
        rejets_recents = (
            FicheExpression.objects.mes_feb(utilisateur)
            .filter(statut=StatutFEB.REJETEE)
            .filter(date_modification__gte=timezone.now() - timedelta(days=7))
            .count()
        )
        if rejets_recents > 0:
            alertes.append({
                "icone": "x-circle",
                "couleur": "error",
                "message": f"{rejets_recents} FEB rejetee(s) cette semaine — voir motifs",
                "lien": "/feb/?statut=REJETEE",
            })

    return alertes


# ═══════════════════════════════════════════════════════════════════
# UTILITAIRES
# ═══════════════════════════════════════════════════════════════════
def format_fcfa(montant):
    """Formate un montant en F CFA avec separateurs."""
    try:
        return f"{int(montant):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"