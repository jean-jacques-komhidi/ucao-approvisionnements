"""
Vues de l'app approvisionnements (FEB).

Workflow :
- Demandeur cree une FEB (DRAFT) -> soumet (EN_INSTANCE)
- CG / DFC valide / modifie / rejette
- Si montant > 50 000 F : generation BC automatique (a venir)
- Si montant <= 50 000 F : cloture directe (impression + signature physique)
"""
import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.comptes.models import RoleUtilisateur
from apps.referentiels.models import Article, ServiceExterieur

from .forms import FormSetLignes, FormulaireFEB
from .models import FicheExpression, StatutFEB

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# UTILITAIRES
# ═══════════════════════════════════════════════════════════════════
def _peut_voir_toutes_feb(user):
    """Vrai si l'utilisateur peut voir toutes les FEB (pas seulement les siennes)."""
    return user.role in (
        RoleUtilisateur.CG,
        RoleUtilisateur.DFC,
        RoleUtilisateur.DG,
        RoleUtilisateur.COMPTABLE,
        RoleUtilisateur.ADMIN,
    )


def _peut_valider(user):
    """Vrai si l'utilisateur peut valider/rejeter des FEB."""
    return user.role in (RoleUtilisateur.CG, RoleUtilisateur.DFC, RoleUtilisateur.ADMIN)


# ═══════════════════════════════════════════════════════════════════
# LISTE DES FEB
# ═══════════════════════════════════════════════════════════════════
@login_required
def feb_liste(request):
    """
    Liste des FEB selon le role :
    - Demandeur : ses FEB uniquement
    - CG/DFC/DG : toutes les FEB
    """
    # Filtrage selon le role
    if _peut_voir_toutes_feb(request.user):
        queryset = FicheExpression.objects.non_supprimees()
        titre_page = "Toutes les FEB"
    else:
        queryset = FicheExpression.objects.mes_feb(request.user)
        titre_page = "Mes FEB"

    # KPI
    total_actives = queryset.count()
    en_instance = queryset.filter(statut=StatutFEB.EN_INSTANCE).count()
    validees = queryset.filter(statut=StatutFEB.VALIDEE).count()
    montant_total = queryset.filter(
        statut__in=[StatutFEB.VALIDEE, StatutFEB.CLOTUREE]
    ).aggregate(total=Sum("montant_ttc"))["total"] or Decimal("0")

    kpi = {
        "total": total_actives,
        "en_instance": en_instance,
        "validees": validees,
        "montant_total": montant_total,
    }

    # Filtres
    statut_filtre = request.GET.get("statut", "").strip()
    if statut_filtre:
        queryset = queryset.filter(statut=statut_filtre)

    recherche = request.GET.get("q", "").strip()
    if recherche:
        queryset = queryset.filter(
            Q(numero__icontains=recherche) |
            Q(objet__icontains=recherche) |
            Q(fournisseur__nom__icontains=recherche)
        )

    # Pagination
    paginator = Paginator(queryset.select_related("demandeur", "fournisseur"), 20)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "approvisionnements/feb_liste.html", {
        "feb_list": page,
        "titre_page": titre_page,
        "statut_filtre": statut_filtre,
        "recherche": recherche,
        "statuts": StatutFEB.choices,
        "kpi": kpi,
        "total": paginator.count,
    })


# ═══════════════════════════════════════════════════════════════════
# CREATION D'UNE FEB
# ═══════════════════════════════════════════════════════════════════
@login_required
@require_http_methods(["GET", "POST"])
def feb_creer(request):
    """Cree une nouvelle FEB avec ses lignes."""
    if not request.user.est_demandeur and not request.user.est_admin:
        messages.error(request, "Vous n'etes pas autorise a creer une FEB.")
        return redirect("tableau_de_bord")

    if request.method == "POST":
        formulaire = FormulaireFEB(request.POST)
        formset = FormSetLignes(request.POST, prefix="lignes")

        if formulaire.is_valid() and formset.is_valid():
            with transaction.atomic():
                # Cree la FEB
                feb = formulaire.save(commit=False)
                feb.demandeur = request.user
                feb.statut = StatutFEB.EN_INSTANCE  # Soumise directement
                feb.save()

                # Sauvegarde les lignes
                formset.instance = feb
                formset.save()

                # Recalcule les totaux
                feb.calculer_totaux()

                logger.info(
                    "FEB %s creee par %s (montant TTC : %s)",
                    feb.numero,
                    request.user.identifiant,
                    feb.montant_ttc,
                )

                messages.success(
                    request,
                    f"FEB {feb.numero} creee avec succes (TTC : {feb.montant_ttc} F CFA).",
                )
                return redirect("feb_detail", pk=feb.pk)
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        formulaire = FormulaireFEB()
        formset = FormSetLignes(prefix="lignes")

    # Donnees pour les selects JavaScript
    articles_data = list(Article.objects.actifs().values(
        "id", "designation", "unite"
    ))
    services_data = list(ServiceExterieur.objects.actifs().values(
        "id", "designation"
    ))

    return render(request, "approvisionnements/feb_creer.html", {
        "formulaire": formulaire,
        "formset": formset,
        "titre_page": "Nouvelle FEB",
        "articles_data": articles_data,
        "services_data": services_data,
    })


# ═══════════════════════════════════════════════════════════════════
# DETAIL D'UNE FEB
# ═══════════════════════════════════════════════════════════════════
@login_required
def feb_detail(request, pk):
    """Detail d'une FEB avec actions selon le role et le statut."""
    feb = get_object_or_404(
        FicheExpression.objects.select_related("demandeur", "fournisseur", "validateur"),
        pk=pk,
    )

    # Permissions
    if not _peut_voir_toutes_feb(request.user) and feb.demandeur != request.user:
        messages.error(request, "Acces refuse.")
        return redirect("feb_liste")

    return render(request, "approvisionnements/feb_detail.html", {
        "feb": feb,
        "lignes": feb.lignes.select_related("article", "service").all(),
        "peut_valider": _peut_valider(request.user) and feb.peut_etre_validee,
    })


# ═══════════════════════════════════════════════════════════════════
# VALIDATION D'UNE FEB
# ═══════════════════════════════════════════════════════════════════
@login_required
@require_http_methods(["POST"])
def feb_valider(request, pk):
    """
    Valide une FEB (CG ou DFC).

    Si montant <= 50 000 F : passe a CLOTUREE.
    Si montant > 50 000 F : passe a VALIDEE et generera un BC.
    """
    if not _peut_valider(request.user):
        messages.error(request, "Reserve aux CG/DFC.")
        return redirect("feb_liste")

    feb = get_object_or_404(FicheExpression, pk=pk)

    if not feb.peut_etre_validee:
        messages.error(request, "Cette FEB ne peut pas etre validee dans son etat actuel.")
        return redirect("feb_detail", pk=pk)

    with transaction.atomic():
        # Recalcule au cas ou
        feb.calculer_totaux(sauvegarder=False)

        # Decide du statut final selon le seuil
        if feb.est_au_dela_du_seuil:
            feb.statut = StatutFEB.VALIDEE
            message_succes = (
                f"FEB {feb.numero} validee. Un Bon de Commande sera genere "
                f"(montant TTC : {feb.montant_ttc} F CFA)."
            )
        else:
            feb.statut = StatutFEB.CLOTUREE
            message_succes = (
                f"FEB {feb.numero} cloturee directement (montant <= 50 000 F)."
            )

        feb.validateur = request.user
        feb.date_validation = timezone.now()
        feb.save()

        logger.info(
            "FEB %s validee par %s (statut final : %s)",
            feb.numero, request.user.identifiant, feb.statut,
        )
        messages.success(request, message_succes)

    return redirect("feb_detail", pk=pk)


# ═══════════════════════════════════════════════════════════════════
# REJET D'UNE FEB
# ═══════════════════════════════════════════════════════════════════
@login_required
@require_http_methods(["POST"])
def feb_rejeter(request, pk):
    """Rejette une FEB avec motif obligatoire."""
    if not _peut_valider(request.user):
        messages.error(request, "Reserve aux CG/DFC.")
        return redirect("feb_liste")

    feb = get_object_or_404(FicheExpression, pk=pk)
    motif = request.POST.get("motif", "").strip()

    if not motif:
        messages.error(request, "Le motif de rejet est obligatoire.")
        return redirect("feb_detail", pk=pk)

    if not feb.peut_etre_validee:
        messages.error(request, "FEB non rejetable dans son etat.")
        return redirect("feb_detail", pk=pk)

    feb.statut = StatutFEB.REJETEE
    feb.motif_action = motif
    feb.validateur = request.user
    feb.save()

    logger.info("FEB %s rejetee par %s : %s", feb.numero, request.user.identifiant, motif)
    messages.warning(request, f"FEB {feb.numero} rejetee.")
    return redirect("feb_detail", pk=pk)


# ═══════════════════════════════════════════════════════════════════
# SUPPRESSION (logique) D'UNE FEB
# ═══════════════════════════════════════════════════════════════════
@login_required
@require_http_methods(["POST"])
def feb_supprimer(request, pk):
    """Suppression LOGIQUE avec motif obligatoire."""
    feb = get_object_or_404(FicheExpression, pk=pk)

    # Permission : demandeur (sa FEB DRAFT) ou CG/DFC
    peut_supprimer = (
        feb.demandeur == request.user and feb.statut == StatutFEB.DRAFT
    ) or _peut_valider(request.user)

    if not peut_supprimer:
        messages.error(request, "Vous n'etes pas autorise a supprimer cette FEB.")
        return redirect("feb_detail", pk=pk)

    motif = request.POST.get("motif", "").strip()
    if not motif:
        messages.error(request, "Le motif de suppression est obligatoire.")
        return redirect("feb_detail", pk=pk)

    feb.est_supprimee = True
    feb.statut = StatutFEB.SUPPRIMEE
    feb.motif_action = motif
    feb.date_suppression = timezone.now()
    feb.save()

    logger.warning("FEB %s supprimee par %s : %s", feb.numero, request.user.identifiant, motif)
    messages.warning(request, f"FEB {feb.numero} supprimee.")
    return redirect("feb_liste")