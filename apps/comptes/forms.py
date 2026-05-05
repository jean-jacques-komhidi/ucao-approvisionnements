"""
Formulaires de l'app comptes.

- FormulaireConnexion : login par identifiant + mot de passe.
"""
from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

from .models import Utilisateur


class FormulaireConnexion(forms.Form):
    """Formulaire de connexion par identifiant + mot de passe."""

    identifiant = forms.CharField(
        label="Identifiant",
        max_length=50,
        widget=forms.TextInput(attrs={
            "class": "champ-formulaire",
            "placeholder": "Votre identifiant",
            "autofocus": True,
            "autocomplete": "username",
        }),
    )
    mot_de_passe = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={
            "class": "champ-formulaire",
            "placeholder": "Mot de passe",
            "autocomplete": "current-password",
        }),
    )

    error_messages = {
        "identifiants_invalides": "Identifiant ou mot de passe incorrect.",
        "compte_bloque": (
            "Votre compte a ete bloque suite a 5 tentatives echouees. "
            "Contactez l'administrateur."
        ),
    }

    def __init__(self, request=None, *args, **kwargs):
        """Stocke la requete pour passer le contexte au backend."""
        self.request = request
        self.utilisateur_authentifie = None
        super().__init__(*args, **kwargs)

    def clean(self):
        """Delegue l'authentification au backend custom."""
        cleaned_data = super().clean()
        identifiant = cleaned_data.get("identifiant")
        mot_de_passe = cleaned_data.get("mot_de_passe")

        if identifiant and mot_de_passe:
            self.utilisateur_authentifie = authenticate(
                request=self.request,
                username=identifiant,
                password=mot_de_passe,
            )

            if self.utilisateur_authentifie is None:
                # Verifie si le compte est bloque pour adapter le message
                try:
                    utilisateur = Utilisateur.objects.get(identifiant=identifiant)
                    if not utilisateur.est_actif:
                        raise ValidationError(
                            self.error_messages["compte_bloque"],
                            code="compte_bloque",
                        )
                except Utilisateur.DoesNotExist:
                    pass

                raise ValidationError(
                    self.error_messages["identifiants_invalides"],
                    code="identifiants_invalides",
                )

        return cleaned_data

    def get_utilisateur(self):
        """Retourne l'utilisateur authentifie apres clean()."""
        return self.utilisateur_authentifie