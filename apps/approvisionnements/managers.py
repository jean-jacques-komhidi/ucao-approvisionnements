"""Managers personnalises de l'app approvisionnements."""
from django.db import models


class FicheExpressionManager(models.Manager):
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
    def articles(self):
        from .models import TypeLigne
        return self.filter(type_ligne=TypeLigne.ARTICLE)

    def services(self):
        from .models import TypeLigne
        return self.filter(type_ligne=TypeLigne.SERVICE)


class BonCommandeManager(models.Manager):
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

    def a_payer(self):
        """BC valides sans paiement complet (= a payer)."""
        from .models import StatutBC, StatutPaiement
        from django.db.models import Sum

        # BC valides
        bc_valides = self.non_supprimes().filter(statut=StatutBC.VALIDE)

        # On exclut ceux qui sont deja entierement payes
        bc_a_payer_ids = []
        for bc in bc_valides:
            total_paye = (
                bc.paiements.filter(statut=StatutPaiement.PAYE)
                .aggregate(total=Sum("montant_verse"))["total"]
            )
            if total_paye is None or total_paye < bc.montant_ttc:
                bc_a_payer_ids.append(bc.pk)

        return bc_valides.filter(pk__in=bc_a_payer_ids)