"""
Middleware de l'app comptes.

ExpirationSession15MinMiddleware :
    Implemente la regle CDC : la session expire apres 15 minutes
    d'inactivite (depuis la derniere requete, pas depuis la creation).
"""
import logging

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class ExpirationSession15MinMiddleware(MiddlewareMixin):
    """Force la deconnexion apres N minutes d'inactivite (defaut : 15)."""

    URLS_EXEMPTEES = (
        "/connexion/",
        "/deconnexion/",
        "/static/",
        "/media/",
        "/admin-django/login/",
        "/api/iot/signal/",
    )

    def process_request(self, request):
        """Verifie l'inactivite avant de traiter la requete."""
        if not request.user.is_authenticated:
            return None

        if any(request.path.startswith(url) for url in self.URLS_EXEMPTEES):
            return None

        maintenant = timezone.now().timestamp()
        derniere_activite = request.session.get("derniere_activite")
        duree_max = getattr(settings, "SESSION_COOKIE_AGE", 15 * 60)

        # Premier passage : initialisation
        if derniere_activite is None:
            request.session["derniere_activite"] = maintenant
            return None

        # Inactivite depassee -> deconnexion
        if maintenant - derniere_activite > duree_max:
            logger.info(
                "Session expiree pour %s (inactivite de %.0fs)",
                request.user.identifiant,
                maintenant - derniere_activite,
            )
            logout(request)
            from django.contrib import messages
            messages.warning(
                request,
                "Votre session a expire apres 15 minutes d'inactivite. "
                "Veuillez vous reconnecter.",
            )
            return redirect(settings.LOGIN_URL)

        # Session encore valide -> rafraichit le timestamp
        request.session["derniere_activite"] = maintenant
        return None