"""
Backend d'authentification personnalise.

Gere :
- L'authentification par 'identifiant' (et non 'username').
- L'increment du compteur d'echecs sur mauvais mot de passe.
- Le rejet immediat des comptes bloques (est_actif=False).
- La reinitialisation du compteur apres authentification reussie.
"""
import logging

from django.conf import settings
from django.contrib.auth.backends import ModelBackend

from .models import Utilisateur

logger = logging.getLogger(__name__)


class BackendCompteurEchecs(ModelBackend):
    """
    Backend qui authentifie via 'identifiant' et gere le compteur d'echecs.

    Comportement :
    - identifiant inconnu -> renvoie None silencieusement
    - compte bloque (est_actif=False) -> renvoie None
    - mot de passe incorrect -> incremente tentatives_echecs
    - succes -> reinitialise tentatives_echecs a 0
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """Tente d'authentifier l'utilisateur."""
        identifiant = username or kwargs.get("identifiant")
        if not identifiant or not password:
            return None

        # ─── Recuperation de l'utilisateur ─────────────────────────
        try:
            utilisateur = Utilisateur.objects.get(identifiant=identifiant)
        except Utilisateur.DoesNotExist:
            # Protection timing attack : on hash quand meme
            Utilisateur().set_password(password)
            logger.info("Tentative de connexion : identifiant inconnu '%s'", identifiant)
            return None

        # ─── Compte deja bloque ────────────────────────────────────
        if not utilisateur.est_actif:
            logger.warning(
                "Tentative sur compte bloque : %s (motif : %s)",
                utilisateur.identifiant,
                utilisateur.motif_blocage,
            )
            return None

        # ─── Verification du mot de passe ──────────────────────────
        if utilisateur.check_password(password):
            utilisateur.reinitialiser_tentatives()
            logger.info("Connexion reussie : %s", utilisateur.identifiant)
            return utilisateur

        # ─── Echec : on incremente le compteur ─────────────────────
        utilisateur.incrementer_tentatives()

        seuil_blocage = getattr(settings, "NB_TENTATIVES_AVANT_BLOCAGE", 5)
        logger.warning(
            "Echec connexion : %s (tentative %d/%d)",
            utilisateur.identifiant,
            utilisateur.tentatives_echecs,
            seuil_blocage,
        )

        return None

    def get_user(self, user_id):
        """Recupere un utilisateur par son ID, en respectant 'est_actif'."""
        try:
            utilisateur = Utilisateur.objects.get(pk=user_id)
        except Utilisateur.DoesNotExist:
            return None
        return utilisateur if utilisateur.est_actif else None

    def user_can_authenticate(self, user):
        """Surcharge pour coherence avec notre champ 'est_actif'."""
        return getattr(user, "est_actif", False)