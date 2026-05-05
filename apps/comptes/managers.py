"""
Managers du modele Utilisateur.

Le UtilisateurManager remplace le UserManager natif Django pour utiliser
'identifiant' comme champ de connexion a la place de 'username'.
"""
from django.contrib.auth.models import BaseUserManager


class UtilisateurManager(BaseUserManager):
    """
    Manager personnalise pour le modele Utilisateur.

    - Utilise 'identifiant' comme champ d'authentification.
    - Force la creation de l'email (utile pour notifications de blocage).
    - Hash bcrypt automatique via set_password().
    """

    use_in_migrations = True

    def _creer_utilisateur(self, identifiant, email, mot_de_passe, **champs_extra):
        """Methode interne mutualisee pour create_user et create_superuser."""
        if not identifiant:
            raise ValueError("L'identifiant est obligatoire.")
        if not email:
            raise ValueError("L'email est obligatoire.")

        email = self.normalize_email(email)
        utilisateur = self.model(
            identifiant=identifiant,
            email=email,
            **champs_extra,
        )
        utilisateur.set_password(mot_de_passe)
        utilisateur.save(using=self._db)
        return utilisateur

    def create_user(self, identifiant, email, mot_de_passe=None, **champs_extra):
        """Cree un utilisateur standard."""
        champs_extra.setdefault("is_staff", False)
        champs_extra.setdefault("is_superuser", False)
        return self._creer_utilisateur(identifiant, email, mot_de_passe, **champs_extra)

    def create_superuser(self, identifiant, email, mot_de_passe=None, **champs_extra):
        """Cree un super-utilisateur (admin technique Django)."""
        champs_extra.setdefault("is_staff", True)
        champs_extra.setdefault("is_superuser", True)
        champs_extra.setdefault("role", "admin")
        champs_extra.setdefault("est_actif", True)

        if champs_extra.get("is_staff") is not True:
            raise ValueError("Le super-utilisateur doit avoir is_staff=True.")
        if champs_extra.get("is_superuser") is not True:
            raise ValueError("Le super-utilisateur doit avoir is_superuser=True.")

        return self._creer_utilisateur(identifiant, email, mot_de_passe, **champs_extra)

    # ─── Querysets utilitaires ────────────────────────────────────
    def actifs(self):
        """Retourne uniquement les utilisateurs actifs (non bloques)."""
        return self.filter(est_actif=True)

    def bloques(self):
        """Retourne uniquement les comptes bloques."""
        return self.filter(est_actif=False)

    def par_role(self, role):
        """Retourne tous les utilisateurs ayant un role donne."""
        return self.filter(role=role, est_actif=True)