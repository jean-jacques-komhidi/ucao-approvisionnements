"""Managers personnalises de l'app approvisionnements."""
from django.db import models


class FicheExpressionManager(models.Manager):
    """Manager pour FicheExpression."""

    def non_supprimees(self):
        """Toutes les FEB non supprimees logiquement."""
        return self.filter(est_supprimee=False)

    def mes_feb(self, utilisateur):
        """FEB creees par un demandeur donne."""
        return self.non_supprimees().filter(demandeur=utilisateur)

    def en_instance(self):
        """FEB en attente de validation (visibles par CG/DFC)."""
        from .models import StatutFEB
        return self.non_supprimees().filter(statut=StatutFEB.EN_INSTANCE)

    def validees(self):
        """FEB validees."""
        from .models import StatutFEB
        return self.non_supprimees().filter(statut=StatutFEB.VALIDEE)

    def cloturees(self):
        """FEB cloturees (montant <= 50 000)."""
        from .models import StatutFEB
        return self.non_supprimees().filter(statut=StatutFEB.CLOTUREE)


class LigneFicheManager(models.Manager):
    """Manager pour LigneFiche."""

    def articles(self):
        """Lignes de type Article uniquement."""
        from .models import TypeLigne
        return self.filter(type_ligne=TypeLigne.ARTICLE)

    def services(self):
        """Lignes de type Service uniquement."""
        from .models import TypeLigne
        return self.filter(type_ligne=TypeLigne.SERVICE)