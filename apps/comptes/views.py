"""
Vues de l'app comptes — UCAO-ISG-CSM.

- vue_connexion       : POST /connexion/ (cf. DS-01)
- vue_deconnexion     : POST /deconnexion/
- vue_tableau_de_bord : GET  /tableau-de-bord/
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .forms import FormulaireConnexion
from .models import Session

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# CONNEXION
# ═══════════════════════════════════════════════════════════════════
@never_cache
@csrf_protect
@require_http_methods(["GET", "POST"])
def vue_connexion(request):
    """
    Affiche le formulaire de connexion (GET) et le traite (POST).

    Cf. diagramme DS-01 — Authentification de l'Utilisateur.
    """
    # Si deja connecte -> redirige vers le tableau de bord
    if request.user.is_authenticated:
        return redirect("tableau_de_bord")

    if request.method == "POST":
        formulaire = FormulaireConnexion(request, data=request.POST)
        if formulaire.is_valid():
            utilisateur = formulaire.get_utilisateur()
            login(request, utilisateur)

            # Trace de session pour l'audit
            _enregistrer_session(request, utilisateur)

            logger.info(
                "Connexion reussie : %s depuis %s",
                utilisateur.identifiant,
                request.META.get("REMOTE_ADDR", "?"),
            )
            messages.success(
                request,
                f"Bienvenue, {utilisateur.nom_complet}.",
            )

            url_redirection = request.GET.get("next") or reverse("tableau_de_bord")
            return redirect(url_redirection)
    else:
        formulaire = FormulaireConnexion(request)

    return render(request, "comptes/connexion.html", {
        "formulaire": formulaire,
    })


def _enregistrer_session(request, utilisateur):
    """Enregistre une trace de session pour l'audit."""
    duree = timedelta(seconds=getattr(settings, "SESSION_COOKIE_AGE", 15 * 60))
    Session.objects.create(
        utilisateur=utilisateur,
        cle_session_django=request.session.session_key or "",
        adresse_ip=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        date_expiration=timezone.now() + duree,
    )


# ═══════════════════════════════════════════════════════════════════
# DECONNEXION
# ═══════════════════════════════════════════════════════════════════
@require_http_methods(["GET", "POST"])
@login_required
def vue_deconnexion(request):
    """Deconnecte l'utilisateur et invalide ses sessions actives."""
    identifiant = request.user.identifiant
    logout(request)
    messages.info(request, "Vous avez ete deconnecte.")
    logger.info("Deconnexion : %s", identifiant)
    return redirect("connexion")


# ═══════════════════════════════════════════════════════════════════
# TABLEAU DE BORD
# ═══════════════════════════════════════════════════════════════════
@login_required
def vue_tableau_de_bord(request):
    """Tableau de bord principal - cockpit adaptatif par role."""
    from .dashboard import (
        construire_activites_recentes,
        construire_alertes,
        construire_graphiques,
        construire_kpi,
    )

    contexte = {
        "kpi": construire_kpi(request.user),
        "graphiques": construire_graphiques(request.user),
        "activites": construire_activites_recentes(request.user, limit=6),
        "alertes": construire_alertes(request.user),
    }

    # Essaye plusieurs chemins de template
    try:
        return render(request, "comptes/tableau_bord.html", contexte)
    except Exception:
        return render(request, "comptes/tableau_de_bord.html", contexte)