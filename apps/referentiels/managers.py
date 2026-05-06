"""
Managers personnalises pour les referentiels.

Fournissent des querysets utilitaires pour les vues et les tests.
"""
from django.db import models


class ArticleManager(models.Manager):
    """Manager pour Article."""

    def actifs(self):
        """Retourne les articles non supprimes."""
        return self.filter(est_actif=True)

    def par_nature(self, nature):
        """Filtre par famille d'article."""
        return self.filter(nature=nature, est_actif=True)


class ServiceExterieurManager(models.Manager):
    """Manager pour ServiceExterieur."""

    def actifs(self):
        """Retourne les services non supprimes."""
        return self.filter(est_actif=True)


class FournisseurManager(models.Manager):
    """Manager pour Fournisseur."""

    def actifs(self):
        """Retourne les fournisseurs non supprimes."""
        return self.filter(est_actif=True)

    def prochain_code(self):
        """
        Calcule le prochain code fournisseur (F0001, F0002...).

        Utilise par le signal pre_save lors de la creation.
        """
        dernier = self.order_by("-code").first()
        if not dernier or not dernier.code.startswith("F"):
            return "F0001"

        try:
            numero = int(dernier.code[1:])
            return f"F{numero + 1:04d}"
        except ValueError:
            return "F0001"


class DeviseManager(models.Manager):
    """Manager pour Devise."""

    def actives(self):
        """Retourne les devises actives."""
        return self.filter(est_active=True)

    def principale(self):
        """Retourne la devise principale (XOF par defaut)."""
        return self.filter(est_devise_principale=True, est_active=True).first()