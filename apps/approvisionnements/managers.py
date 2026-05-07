"""Managers personnalises de l'app approvisionnements."""
from django.db import models


class FicheExpressionManager(models.Manager):
    """Manager pour FicheExpression."""

    def non_supprimees(self):
        return self.filter(est_supprimee=False)

    def mes_feb(self, utilisateur):
        return self.non_supprimees().filter(demandeur=utilisateur)

    def en_instance(self):
        from .models import StatutFEB
        return self.non_supprimees().filter(statut=StatutFEB.EN_INSTANCE)

    def validees(self):
        from .models import StatutFEB
        return self.non_supprimees().filter(statut=StatutFEB.VALIDEE)

    def cloturees(self):
        from .models import StatutFEB
        return self.non_supprimees().filter(statut=StatutFEB.CLOTUREE)


class LigneFicheManager(models.Manager):
    """Manager pour LigneFiche."""

    def articles(self):
        from .models import TypeLigne
        return self.filter(type_ligne=TypeLigne.ARTICLE)

    def services(self):
        from .models import TypeLigne
        return self.filter(type_ligne=TypeLigne.SERVICE)


class BonCommandeManager(models.Manager):
    """Manager pour BonCommande."""

    def non_supprimes(self):
        return self.filter(est_supprime=False)

    def en_instance(self):
        from .models import StatutBC
        return self.non_supprimes().filter(statut=StatutBC.EN_INSTANCE)

    def valides(self):
        from .models import StatutBC
        return self.non_supprimes().filter(statut=StatutBC.VALIDE)

    def envoyes(self):
        return self.non_supprimes().filter(est_envoye_fournisseur=True)