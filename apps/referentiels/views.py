"""
Vues de l'app referentiels.

CRUD complet pour Articles (avec image), Services, Fournisseurs et Devises.
Inclut les KPI statistiques pour chaque page de liste.
"""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.comptes.models import RoleUtilisateur

from .forms import (
    FormulaireArticle,
    FormulaireDevise,
    FormulaireFournisseur,
    FormulaireServiceExterieur,
)
from .models import Article, Devise, Fournisseur, ServiceExterieur

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# DECORATEURS DE PERMISSION
# ═══════════════════════════════════════════════════════════════════
def _est_demandeur_ou_admin(user):
    """Vrai si l'utilisateur peut gerer Articles/Services/Fournisseurs."""
    return user.est_demandeur or user.est_admin


def _peut_gerer_devises(user):
    """Vrai si l'utilisateur peut gerer les Devises (DFC ou Admin)."""
    return user.role in (RoleUtilisateur.DFC, RoleUtilisateur.ADMIN)


# ═══════════════════════════════════════════════════════════════════
# ARTICLES
# ═══════════════════════════════════════════════════════════════════
@login_required
def liste_articles(request):
    """Affiche la liste des articles avec recherche, filtres et KPI."""
    if not _est_demandeur_ou_admin(request.user):
        messages.error(request, "Vous n'avez pas l'autorisation d'acceder a cette page.")
        return redirect("tableau_de_bord")

    queryset = Article.objects.actifs()

    # KPI globaux (avant filtrage)
    tous_articles = Article.objects.all()
    kpi = {
        "total_actifs": tous_articles.filter(est_actif=True).count(),
        "total_inactifs": tous_articles.filter(est_actif=False).count(),
        "avec_image": tous_articles.filter(est_actif=True).exclude(image="").exclude(image=None).count(),
        "par_nature_count": tous_articles.filter(est_actif=True).values("nature").distinct().count(),
    }

    # Recherche
    recherche = request.GET.get("q", "").strip()
    if recherche:
        queryset = queryset.filter(
            Q(designation__icontains=recherche) |
            Q(description__icontains=recherche)
        )

    # Filtre par nature
    nature_filtre = request.GET.get("nature", "").strip()
    if nature_filtre:
        queryset = queryset.filter(nature=nature_filtre)

    # Pagination
    paginator = Paginator(queryset.order_by("designation"), 12)  # 12 par page (3x4 en grille)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "referentiels/articles_liste.html", {
        "articles": page,
        "recherche": recherche,
        "nature_filtre": nature_filtre,
        "natures": Article._meta.get_field("nature").choices,
        "total": paginator.count,
        "kpi": kpi,
    })


@login_required
@require_http_methods(["GET", "POST"])
def article_creer(request):
    """Cree un nouvel article (avec upload d'image)."""
    if not _est_demandeur_ou_admin(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    if request.method == "POST":
        formulaire = FormulaireArticle(request.POST, request.FILES)
        if formulaire.is_valid():
            article = formulaire.save(commit=False)
            article.cree_par = request.user
            article.save()
            messages.success(request, f"Article '{article.designation}' cree avec succes.")
            logger.info("Article cree : %s par %s", article.designation, request.user.identifiant)
            return redirect("articles_liste")
    else:
        formulaire = FormulaireArticle()

    return render(request, "referentiels/article_formulaire.html", {
        "formulaire": formulaire,
        "titre_page": "Nouvel article",
        "mode": "creer",
    })


@login_required
@require_http_methods(["GET", "POST"])
def article_modifier(request, pk):
    """Modifie un article existant (avec upload d'image)."""
    if not _est_demandeur_ou_admin(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    article = get_object_or_404(Article, pk=pk)

    if request.method == "POST":
        formulaire = FormulaireArticle(request.POST, request.FILES, instance=article)
        if formulaire.is_valid():
            formulaire.save()
            messages.success(request, f"Article '{article.designation}' modifie.")
            return redirect("articles_liste")
    else:
        formulaire = FormulaireArticle(instance=article)

    return render(request, "referentiels/article_formulaire.html", {
        "formulaire": formulaire,
        "titre_page": f"Modifier : {article.designation}",
        "mode": "modifier",
        "objet": article,
    })


@login_required
@require_http_methods(["POST"])
def article_supprimer(request, pk):
    """Suppression LOGIQUE d'un article (est_actif = False)."""
    if not _est_demandeur_ou_admin(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    article = get_object_or_404(Article, pk=pk)
    article.est_actif = False
    article.save(update_fields=["est_actif"])

    messages.warning(request, f"Article '{article.designation}' retire du catalogue.")
    logger.info("Article retire : %s par %s", article.designation, request.user.identifiant)
    return redirect("articles_liste")


# ═══════════════════════════════════════════════════════════════════
# SERVICES EXTERIEURS
# ═══════════════════════════════════════════════════════════════════
@login_required
def liste_services(request):
    """Affiche la liste des services exterieurs avec KPI."""
    if not _est_demandeur_ou_admin(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    queryset = ServiceExterieur.objects.actifs()

    # KPI
    tous_services = ServiceExterieur.objects.all()
    kpi = {
        "total_actifs": tous_services.filter(est_actif=True).count(),
        "total_inactifs": tous_services.filter(est_actif=False).count(),
        "ce_mois": tous_services.filter(
            est_actif=True,
            date_creation__month__gte=1,  # Tous ce mois (simplification)
        ).count(),
    }

    recherche = request.GET.get("q", "").strip()
    if recherche:
        queryset = queryset.filter(
            Q(designation__icontains=recherche) |
            Q(description__icontains=recherche)
        )

    paginator = Paginator(queryset.order_by("designation"), 20)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "referentiels/services_liste.html", {
        "services": page,
        "recherche": recherche,
        "total": paginator.count,
        "kpi": kpi,
    })


@login_required
@require_http_methods(["GET", "POST"])
def service_creer(request):
    """Cree un nouveau service exterieur."""
    if not _est_demandeur_ou_admin(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    if request.method == "POST":
        formulaire = FormulaireServiceExterieur(request.POST)
        if formulaire.is_valid():
            service = formulaire.save(commit=False)
            service.cree_par = request.user
            service.save()
            messages.success(request, f"Service '{service.designation}' cree.")
            return redirect("services_liste")
    else:
        formulaire = FormulaireServiceExterieur()

    return render(request, "referentiels/service_formulaire.html", {
        "formulaire": formulaire,
        "titre_page": "Nouveau service",
        "mode": "creer",
    })


@login_required
@require_http_methods(["GET", "POST"])
def service_modifier(request, pk):
    """Modifie un service exterieur."""
    if not _est_demandeur_ou_admin(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    service = get_object_or_404(ServiceExterieur, pk=pk)

    if request.method == "POST":
        formulaire = FormulaireServiceExterieur(request.POST, instance=service)
        if formulaire.is_valid():
            formulaire.save()
            messages.success(request, f"Service '{service.designation}' modifie.")
            return redirect("services_liste")
    else:
        formulaire = FormulaireServiceExterieur(instance=service)

    return render(request, "referentiels/service_formulaire.html", {
        "formulaire": formulaire,
        "titre_page": f"Modifier : {service.designation}",
        "mode": "modifier",
        "objet": service,
    })


@login_required
@require_http_methods(["POST"])
def service_supprimer(request, pk):
    """Supprime logiquement un service exterieur."""
    if not _est_demandeur_ou_admin(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    service = get_object_or_404(ServiceExterieur, pk=pk)
    service.est_actif = False
    service.save(update_fields=["est_actif"])

    messages.warning(request, f"Service '{service.designation}' retire.")
    return redirect("services_liste")


# ═══════════════════════════════════════════════════════════════════
# FOURNISSEURS
# ═══════════════════════════════════════════════════════════════════
@login_required
def liste_fournisseurs(request):
    """Affiche la liste des fournisseurs avec KPI."""
    if not _est_demandeur_ou_admin(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    queryset = Fournisseur.objects.actifs()

    # KPI
    tous_fournisseurs = Fournisseur.objects.all()
    kpi = {
        "total_actifs": tous_fournisseurs.filter(est_actif=True).count(),
        "total_inactifs": tous_fournisseurs.filter(est_actif=False).count(),
        "personnes_morales": tous_fournisseurs.filter(
            est_actif=True, type_personne="morale"
        ).count(),
        "personnes_physiques": tous_fournisseurs.filter(
            est_actif=True, type_personne="physique"
        ).count(),
    }

    recherche = request.GET.get("q", "").strip()
    if recherche:
        queryset = queryset.filter(
            Q(nom__icontains=recherche) |
            Q(code__icontains=recherche) |
            Q(email__icontains=recherche)
        )

    paginator = Paginator(queryset.order_by("code"), 20)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "referentiels/fournisseurs_liste.html", {
        "fournisseurs": page,
        "recherche": recherche,
        "total": paginator.count,
        "kpi": kpi,
    })


@login_required
@require_http_methods(["GET", "POST"])
def fournisseur_creer(request):
    """Cree un nouveau fournisseur (code automatique F0001...)."""
    if request.user.role not in (
        RoleUtilisateur.RESP_APPRO,
        RoleUtilisateur.ADMIN,
    ):
        messages.error(request, "Reserve aux Responsables Approvisionnements.")
        return redirect("tableau_de_bord")

    if request.method == "POST":
        formulaire = FormulaireFournisseur(request.POST)
        if formulaire.is_valid():
            fournisseur = formulaire.save(commit=False)
            fournisseur.cree_par = request.user
            fournisseur.save()
            messages.success(
                request,
                f"Fournisseur '{fournisseur.nom}' cree avec le code {fournisseur.code}.",
            )
            return redirect("fournisseurs_liste")
    else:
        formulaire = FormulaireFournisseur()

    return render(request, "referentiels/fournisseur_formulaire.html", {
        "formulaire": formulaire,
        "titre_page": "Nouveau fournisseur",
        "mode": "creer",
    })


@login_required
@require_http_methods(["GET", "POST"])
def fournisseur_modifier(request, pk):
    """Modifie un fournisseur (le code reste fige)."""
    if request.user.role not in (
        RoleUtilisateur.RESP_APPRO,
        RoleUtilisateur.ADMIN,
    ):
        messages.error(request, "Reserve aux Responsables Approvisionnements.")
        return redirect("tableau_de_bord")

    fournisseur = get_object_or_404(Fournisseur, pk=pk)

    if request.method == "POST":
        formulaire = FormulaireFournisseur(request.POST, instance=fournisseur)
        if formulaire.is_valid():
            formulaire.save()
            messages.success(request, f"Fournisseur '{fournisseur.nom}' modifie.")
            return redirect("fournisseurs_liste")
    else:
        formulaire = FormulaireFournisseur(instance=fournisseur)

    return render(request, "referentiels/fournisseur_formulaire.html", {
        "formulaire": formulaire,
        "titre_page": f"Modifier : {fournisseur.code} — {fournisseur.nom}",
        "mode": "modifier",
        "objet": fournisseur,
    })


@login_required
@require_http_methods(["POST"])
def fournisseur_supprimer(request, pk):
    """Supprime logiquement un fournisseur."""
    if request.user.role not in (
        RoleUtilisateur.RESP_APPRO,
        RoleUtilisateur.ADMIN,
    ):
        messages.error(request, "Reserve aux Responsables Approvisionnements.")
        return redirect("tableau_de_bord")

    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    fournisseur.est_actif = False
    fournisseur.save(update_fields=["est_actif"])

    messages.warning(request, f"Fournisseur '{fournisseur.nom}' retire.")
    return redirect("fournisseurs_liste")


# ═══════════════════════════════════════════════════════════════════
# DEVISES (DFC uniquement)
# ═══════════════════════════════════════════════════════════════════
@login_required
def liste_devises(request):
    """Affiche la liste des devises avec KPI."""
    if not _peut_gerer_devises(request.user):
        messages.error(request, "Reserve au Directeur Financier et Comptable.")
        return redirect("tableau_de_bord")

    devises = Devise.objects.all().order_by("-est_devise_principale", "code")

    # KPI
    devise_principale = Devise.objects.filter(
        est_devise_principale=True, est_active=True
    ).first()
    kpi = {
        "total": devises.count(),
        "actives": devises.filter(est_active=True).count(),
        "inactives": devises.filter(est_active=False).count(),
        "principale_code": devise_principale.code if devise_principale else "—",
        "principale_tva": (
            f"{devise_principale.taux_tva}%" if devise_principale else "—"
        ),
    }

    return render(request, "referentiels/devises_liste.html", {
        "devises": devises,
        "total": devises.count(),
        "kpi": kpi,
    })


@login_required
@require_http_methods(["GET", "POST"])
def devise_creer(request):
    """Cree une nouvelle devise."""
    if not _peut_gerer_devises(request.user):
        messages.error(request, "Reserve au DFC.")
        return redirect("tableau_de_bord")

    if request.method == "POST":
        formulaire = FormulaireDevise(request.POST)
        if formulaire.is_valid():
            devise = formulaire.save(commit=False)
            devise.gere_par = request.user
            devise.save()
            messages.success(request, f"Devise '{devise.code}' creee.")
            return redirect("devises_liste")
    else:
        formulaire = FormulaireDevise()

    return render(request, "referentiels/devise_formulaire.html", {
        "formulaire": formulaire,
        "titre_page": "Nouvelle devise",
        "mode": "creer",
    })


@login_required
@require_http_methods(["GET", "POST"])
def devise_modifier(request, pk):
    """Modifie une devise."""
    if not _peut_gerer_devises(request.user):
        messages.error(request, "Reserve au DFC.")
        return redirect("tableau_de_bord")

    devise = get_object_or_404(Devise, pk=pk)

    if request.method == "POST":
        formulaire = FormulaireDevise(request.POST, instance=devise)
        if formulaire.is_valid():
            formulaire.save()
            messages.success(request, f"Devise '{devise.code}' modifiee.")
            return redirect("devises_liste")
    else:
        formulaire = FormulaireDevise(instance=devise)

    return render(request, "referentiels/devise_formulaire.html", {
        "formulaire": formulaire,
        "titre_page": f"Modifier : {devise.code}",
        "mode": "modifier",
        "objet": devise,
    })

# ═══════════════════════════════════════════════════════════════════
# GESTION DE STOCK
# ═══════════════════════════════════════════════════════════════════
@login_required
def articles_stock(request):
    """Page de gestion de stock des articles."""
    from apps.comptes.models import RoleUtilisateur

    if request.user.role not in (RoleUtilisateur.RESP_APPRO, RoleUtilisateur.ADMIN, RoleUtilisateur.CHEF_CCE, RoleUtilisateur.CHEF_SLMG):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    from .models import Article

    queryset = Article.objects.filter(est_actif=True, gestion_stock_active=True).order_by("designation")

    # Filtres
    filtre = request.GET.get("filtre", "tous")
    if filtre == "rupture":
        queryset = queryset.filter(quantite_stock__lte=0)
    elif filtre == "sous_seuil":
        from django.db.models import F
        queryset = queryset.filter(quantite_stock__lte=F("seuil_alerte"), quantite_stock__gt=0)
    elif filtre == "ok":
        from django.db.models import F
        queryset = queryset.filter(quantite_stock__gt=F("seuil_alerte"))

    # KPI
    total_geres = Article.objects.filter(est_actif=True, gestion_stock_active=True).count()
    nb_rupture = Article.objects.filter(est_actif=True, gestion_stock_active=True, quantite_stock__lte=0).count()

    from django.db.models import F
    nb_sous_seuil = (
        Article.objects.filter(est_actif=True, gestion_stock_active=True, quantite_stock__lte=F("seuil_alerte"), quantite_stock__gt=0)
        .count()
    )
    nb_ok = total_geres - nb_rupture - nb_sous_seuil

    kpi = {
        "total_geres": total_geres,
        "nb_rupture": nb_rupture,
        "nb_sous_seuil": nb_sous_seuil,
        "nb_ok": nb_ok,
    }

    return render(request, "referentiels/articles_stock.html", {
        "articles": queryset,
        "filtre": filtre,
        "kpi": kpi,
    })


@login_required
@require_http_methods(["POST"])
def article_ajuster_stock(request, pk):
    """Ajuste le stock d'un article (entree ou sortie)."""
    from apps.comptes.models import RoleUtilisateur
    from .models import Article
    from .services import ajuster_stock

    if request.user.role not in (RoleUtilisateur.RESP_APPRO, RoleUtilisateur.ADMIN):
        messages.error(request, "Reserve au Resp.Appro et Admin.")
        return redirect("articles_stock")

    article = get_object_or_404(Article, pk=pk)

    try:
        delta = int(request.POST.get("delta", 0))
    except ValueError:
        messages.error(request, "Quantite invalide.")
        return redirect("articles_stock")

    motif = request.POST.get("motif", "").strip()

    if delta == 0:
        messages.warning(request, "Quantite egale a zero, aucun changement.")
    else:
        ajuster_stock(article, delta, request.user, motif)
        type_ope = "Entree" if delta > 0 else "Sortie"
        messages.success(
            request,
            f"{type_ope} de {abs(delta)} {article.unite}(s) enregistree. "
            f"Nouveau stock : {article.quantite_stock}."
        )

    return redirect("articles_stock")