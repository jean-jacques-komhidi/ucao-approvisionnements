"""
Vues de l'app approvisionnements (FEB + BC).
"""
import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.comptes.models import RoleUtilisateur
from apps.referentiels.models import Article, ServiceExterieur

from .forms import FormSetLignes, FormulaireFEB, FormulaireValidationBC
from .models import BonCommande, FicheExpression, StatutBC, StatutFEB
from .services import generer_bc_depuis_feb

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# UTILITAIRES PERMISSIONS
# ═══════════════════════════════════════════════════════════════════
def _peut_voir_toutes_feb(user):
    return user.role in (
        RoleUtilisateur.CG, RoleUtilisateur.DFC, RoleUtilisateur.DG,
        RoleUtilisateur.COMPTABLE, RoleUtilisateur.ADMIN,
    )


def _peut_valider_feb(user):
    return user.role in (RoleUtilisateur.CG, RoleUtilisateur.DFC, RoleUtilisateur.ADMIN)


def _peut_voir_bc(user):
    return user.role in (
        RoleUtilisateur.DG, RoleUtilisateur.DFC, RoleUtilisateur.CG,
        RoleUtilisateur.COMPTABLE, RoleUtilisateur.ADMIN,
    )


def _peut_valider_bc(user):
    return user.role in (RoleUtilisateur.DG, RoleUtilisateur.DFC, RoleUtilisateur.ADMIN)


# ═══════════════════════════════════════════════════════════════════
# FEB — LISTE
# ═══════════════════════════════════════════════════════════════════
@login_required
def feb_liste(request):
    """Liste des FEB selon le role."""
    if _peut_voir_toutes_feb(request.user):
        queryset = FicheExpression.objects.non_supprimees()
        titre_page = "Toutes les FEB"
    else:
        queryset = FicheExpression.objects.mes_feb(request.user)
        titre_page = "Mes FEB"

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
# FEB — CREATION
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
                feb = formulaire.save(commit=False)
                feb.demandeur = request.user
                feb.statut = StatutFEB.EN_INSTANCE
                feb.save()

                formset.instance = feb
                formset.save()

                feb.calculer_totaux()

                logger.info(
                    "FEB %s creee par %s (TTC : %s)",
                    feb.numero, request.user.identifiant, feb.montant_ttc,
                )
                messages.success(
                    request,
                    f"FEB {feb.numero} creee (TTC : {feb.montant_ttc} F CFA).",
                )
                return redirect("feb_detail", pk=feb.pk)
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        formulaire = FormulaireFEB()
        formset = FormSetLignes(prefix="lignes")

    articles_data = list(Article.objects.actifs().values("id", "designation", "unite"))
    services_data = list(ServiceExterieur.objects.actifs().values("id", "designation"))

    return render(request, "approvisionnements/feb_creer.html", {
        "formulaire": formulaire,
        "formset": formset,
        "titre_page": "Nouvelle FEB",
        "articles_data": articles_data,
        "services_data": services_data,
    })


# ═══════════════════════════════════════════════════════════════════
# FEB — DETAIL
# ═══════════════════════════════════════════════════════════════════
@login_required
def feb_detail(request, pk):
    """Detail d'une FEB."""
    feb = get_object_or_404(
        FicheExpression.objects.select_related("demandeur", "fournisseur", "validateur"),
        pk=pk,
    )

    if not _peut_voir_toutes_feb(request.user) and feb.demandeur != request.user:
        messages.error(request, "Acces refuse.")
        return redirect("feb_liste")

    # BC associe (s'il existe)
    bc_associe = None
    if hasattr(feb, "bon_commande") and not feb.bon_commande.est_supprime:
        bc_associe = feb.bon_commande

    return render(request, "approvisionnements/feb_detail.html", {
        "feb": feb,
        "lignes": feb.lignes.select_related("article", "service").all(),
        "peut_valider": _peut_valider_feb(request.user) and feb.peut_etre_validee,
        "bc_associe": bc_associe,
    })


# ═══════════════════════════════════════════════════════════════════
# FEB — VALIDATION (genere BC si > seuil)
# ═══════════════════════════════════════════════════════════════════
@login_required
@require_http_methods(["POST"])
def feb_valider(request, pk):
    """Valide une FEB et genere un BC si montant > 50 000 F."""
    if not _peut_valider_feb(request.user):
        messages.error(request, "Reserve aux CG/DFC.")
        return redirect("feb_liste")

    feb = get_object_or_404(FicheExpression, pk=pk)

    if not feb.peut_etre_validee:
        messages.error(request, "Cette FEB ne peut pas etre validee dans son etat actuel.")
        return redirect("feb_detail", pk=pk)

    with transaction.atomic():
        feb.calculer_totaux(sauvegarder=False)

        if feb.est_au_dela_du_seuil:
            # FEB > 50 000 F : valide + genere BC
            feb.statut = StatutFEB.VALIDEE
            feb.validateur = request.user
            feb.date_validation = timezone.now()
            feb.save()

            # Generation atomique du BC
            bc = generer_bc_depuis_feb(feb)

            messages.success(
                request,
                f"FEB {feb.numero} validee. Bon de Commande {bc.numero} genere "
                f"automatiquement (TTC : {feb.montant_ttc} F CFA).",
            )
            return redirect("bc_detail", pk=bc.pk)

        else:
            # FEB <= 50 000 F : cloturee directement
            feb.statut = StatutFEB.CLOTUREE
            feb.validateur = request.user
            feb.date_validation = timezone.now()
            feb.save()

            messages.success(
                request,
                f"FEB {feb.numero} cloturee directement (montant <= 50 000 F).",
            )
            return redirect("feb_detail", pk=pk)


# ═══════════════════════════════════════════════════════════════════
# FEB — REJET
# ═══════════════════════════════════════════════════════════════════
@login_required
@require_http_methods(["POST"])
def feb_rejeter(request, pk):
    """Rejette une FEB avec motif obligatoire."""
    if not _peut_valider_feb(request.user):
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
# FEB — SUPPRESSION
# ═══════════════════════════════════════════════════════════════════
@login_required
@require_http_methods(["POST"])
def feb_supprimer(request, pk):
    """Suppression LOGIQUE avec motif obligatoire."""
    feb = get_object_or_404(FicheExpression, pk=pk)

    peut_supprimer = (
        feb.demandeur == request.user and feb.statut == StatutFEB.DRAFT
    ) or _peut_valider_feb(request.user)

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


# ═══════════════════════════════════════════════════════════════════
# BC — LISTE
# ═══════════════════════════════════════════════════════════════════
@login_required
def bc_liste(request):
    """Liste des Bons de Commande."""
    if not _peut_voir_bc(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    queryset = BonCommande.objects.non_supprimes()

    # KPI
    total = queryset.count()
    en_instance = queryset.filter(statut=StatutBC.EN_INSTANCE).count()
    valides = queryset.filter(statut=StatutBC.VALIDE).count()
    montant_total = queryset.filter(statut=StatutBC.VALIDE).aggregate(
        total=Sum("montant_ttc")
    )["total"] or Decimal("0")

    kpi = {
        "total": total,
        "en_instance": en_instance,
        "valides": valides,
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
            Q(fiche__numero__icontains=recherche) |
            Q(fournisseur__nom__icontains=recherche)
        )

    paginator = Paginator(
        queryset.select_related("fiche", "fournisseur", "validateur"), 20
    )
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "approvisionnements/bc_liste.html", {
        "bc_list": page,
        "statut_filtre": statut_filtre,
        "recherche": recherche,
        "statuts": StatutBC.choices,
        "kpi": kpi,
        "total": paginator.count,
    })


# ═══════════════════════════════════════════════════════════════════
# BC — DETAIL
# ═══════════════════════════════════════════════════════════════════
@login_required
def bc_detail(request, pk):
    """Detail d'un Bon de Commande."""
    if not _peut_voir_bc(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    bc = get_object_or_404(
        BonCommande.objects.select_related("fiche", "fournisseur", "validateur"),
        pk=pk,
    )

    return render(request, "approvisionnements/bc_detail.html", {
        "bc": bc,
        "lignes": bc.lignes.select_related("article", "service"),
        "peut_valider": _peut_valider_bc(request.user) and bc.peut_etre_valide,
        "formulaire_validation": FormulaireValidationBC(),
        "est_dfc": request.user.role == RoleUtilisateur.DFC,
    })


# ═══════════════════════════════════════════════════════════════════
# BC — VALIDATION
# ═══════════════════════════════════════════════════════════════════
@login_required
@require_http_methods(["POST"])
def bc_valider(request, pk):
    """Valide un BC (DG ou DFC en PO)."""
    if not _peut_valider_bc(request.user):
        messages.error(request, "Reserve aux DG/DFC.")
        return redirect("bc_liste")

    bc = get_object_or_404(BonCommande, pk=pk)

    if not bc.peut_etre_valide:
        messages.error(request, "Ce BC ne peut pas etre valide dans son etat actuel.")
        return redirect("bc_detail", pk=pk)

    formulaire = FormulaireValidationBC(request.POST)
    if not formulaire.is_valid():
        messages.error(request, "Erreur dans le formulaire.")
        return redirect("bc_detail", pk=pk)

    signe_en_po = formulaire.cleaned_data.get("signe_en_po", False)

    # Si DFC sans cocher PO et que le user n'est pas DG
    if request.user.role == RoleUtilisateur.DFC and not signe_en_po:
        messages.warning(
            request,
            "En tant que DFC, vous devez cocher 'Signer en PO' si le DG est absent.",
        )
        return redirect("bc_detail", pk=pk)

    with transaction.atomic():
        # SELECT_FOR_UPDATE pour eviter double validation
        bc = BonCommande.objects.select_for_update().get(pk=pk)

        if not bc.peut_etre_valide:
            messages.error(request, "Ce BC vient d'etre modifie.")
            return redirect("bc_detail", pk=pk)

        bc.statut = StatutBC.VALIDE
        bc.validateur = request.user
        bc.date_validation = timezone.now()
        bc.signe_en_po = signe_en_po
        bc.save()

        logger.info(
            "BC %s valide par %s%s",
            bc.numero, request.user.identifiant,
            " (signe en PO)" if signe_en_po else "",
        )
        messages.success(request, f"BC {bc.numero} valide avec succes.")

    return redirect("bc_detail", pk=pk)


# ═══════════════════════════════════════════════════════════════════
# BC — SUPPRESSION (logique)
# ═══════════════════════════════════════════════════════════════════
@login_required
@require_http_methods(["POST"])
def bc_supprimer(request, pk):
    """Suppression LOGIQUE d'un BC avec motif."""
    if not _peut_valider_bc(request.user):
        messages.error(request, "Reserve aux DG/DFC.")
        return redirect("bc_liste")

    bc = get_object_or_404(BonCommande, pk=pk)

    if not bc.peut_etre_supprime:
        messages.error(request, "Ce BC ne peut pas etre supprime.")
        return redirect("bc_detail", pk=pk)

    motif = request.POST.get("motif", "").strip()
    if not motif:
        messages.error(request, "Le motif de suppression est obligatoire.")
        return redirect("bc_detail", pk=pk)

    with transaction.atomic():
        bc.est_supprime = True
        bc.statut = StatutBC.SUPPRIME
        bc.motif_suppression = motif
        bc.date_suppression = timezone.now()
        bc.save()

        # Cascade logique sur la FEB liee
        feb = bc.fiche
        feb.est_supprimee = True
        feb.statut = StatutFEB.SUPPRIMEE
        feb.motif_action = f"Suppression BC : {motif}"
        feb.date_suppression = timezone.now()
        feb.save()

    logger.warning(
        "BC %s supprime par %s : %s (cascade FEB %s)",
        bc.numero, request.user.identifiant, motif, feb.numero,
    )
    messages.warning(request, f"BC {bc.numero} supprime.")
    return redirect("bc_liste")


# ═══════════════════════════════════════════════════════════════════
# BC — GENERATION PDF (WeasyPrint avec fallback xhtml2pdf)
# ═══════════════════════════════════════════════════════════════════
@login_required
def bc_pdf(request, pk):
    """
    Genere un PDF du BC.

    Strategie :
    1. Essaie d'abord WeasyPrint (rendu premium)
    2. Si echec (GTK absent), utilise xhtml2pdf (pure Python)
    """
    if not _peut_voir_bc(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    bc = get_object_or_404(
        BonCommande.objects.select_related("fiche", "fournisseur", "validateur"),
        pk=pk,
    )

    contexte = {
        "bc": bc,
        "lignes": bc.lignes.select_related("article", "service"),
        "request": request,
    }

    # Tentative 1 : WeasyPrint (rendu premium)
    try:
        from weasyprint import HTML
        html_string = render_to_string("approvisionnements/bc_pdf.html", contexte)
        pdf_bytes = HTML(
            string=html_string,
            base_url=request.build_absolute_uri("/"),
        ).write_pdf()

        logger.info("PDF BC %s genere par %s (WeasyPrint)", bc.numero, request.user.identifiant)

    except (ImportError, OSError) as exc:
        # Tentative 2 : xhtml2pdf (fallback pure Python)
        logger.warning("WeasyPrint indisponible (%s), bascule sur xhtml2pdf", exc)
        try:
            from io import BytesIO
            from xhtml2pdf import pisa

            html_string = render_to_string("approvisionnements/bc_pdf.html", contexte)
            tampon = BytesIO()
            pisa_status = pisa.CreatePDF(
                src=html_string,
                dest=tampon,
                encoding="utf-8",
                link_callback=_pdf_link_callback,
            )

            if pisa_status.err:
                logger.error("Erreur xhtml2pdf BC %s", bc.numero)
                messages.error(request, "Erreur lors de la generation du PDF.")
                return redirect("bc_detail", pk=pk)

            pdf_bytes = tampon.getvalue()
            tampon.close()
            logger.info("PDF BC %s genere par %s (xhtml2pdf)", bc.numero, request.user.identifiant)

        except ImportError:
            messages.error(
                request,
                "Aucune librairie PDF installee. Lancez : pip install weasyprint OU pip install xhtml2pdf",
            )
            return redirect("bc_detail", pk=pk)
        except Exception as exc2:
            logger.exception("Erreur fallback xhtml2pdf BC %s : %s", bc.numero, exc2)
            messages.error(request, f"Erreur de generation PDF : {exc2}")
            return redirect("bc_detail", pk=pk)
    except Exception as exc:
        logger.exception("Erreur generation PDF BC %s : %s", bc.numero, exc)
        messages.error(request, f"Erreur lors de la generation : {exc}")
        return redirect("bc_detail", pk=pk)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{bc.numero}.pdf"'
    return response


def _pdf_link_callback(uri, rel):
    """
    Convertit les URI relatives (/static/, /media/) en chemins absolus.
    Utilise par xhtml2pdf pour charger images et CSS.
    """
    import os
    from django.conf import settings

    if uri.startswith(settings.STATIC_URL):
        chemin = uri.replace(settings.STATIC_URL, "")
        for repertoire in getattr(settings, "STATICFILES_DIRS", []):
            chemin_complet = os.path.join(repertoire, chemin)
            if os.path.isfile(chemin_complet):
                return chemin_complet
        if hasattr(settings, "STATIC_ROOT") and settings.STATIC_ROOT:
            chemin_complet = os.path.join(settings.STATIC_ROOT, chemin)
            if os.path.isfile(chemin_complet):
                return chemin_complet

    if uri.startswith(settings.MEDIA_URL):
        chemin = uri.replace(settings.MEDIA_URL, "")
        chemin_complet = os.path.join(settings.MEDIA_ROOT, chemin)
        if os.path.isfile(chemin_complet):
            return chemin_complet

    if uri.startswith("http://") or uri.startswith("https://"):
        return uri

    return uri