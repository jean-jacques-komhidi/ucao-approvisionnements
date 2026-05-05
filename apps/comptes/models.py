"""
Modeles de l'app comptes — UCAO-ISG-CSM.

Definit deux entites principales :
- Utilisateur : compte interne (heritant de AbstractBaseUser).
- Session : trace les sessions actives avec jeton JWT.
"""
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UtilisateurManager


# ═══════════════════════════════════════════════════════════════════
# ENUMERATIONS DE ROLES
# ═══════════════════════════════════════════════════════════════════
class RoleUtilisateur(models.TextChoices):
    """Roles internes du systeme."""

    RESP_APPRO = "resp_appro", "Resp. Approvisionnements / Adjoint"
    CHEF_CCE = "chef_cce", "Chef CCE"
    CHEF_SLMG = "chef_slmg", "Chef SLMG"
    CG = "cg", "Controleur de Gestion"
    DFC = "dfc", "Directeur Financier et Comptable"
    DG = "dg", "Directeur General"
    COMPTABLE = "comptable", "Comptable Tresorerie"
    ADMIN = "admin", "Administrateur Systeme"
    CAPTEUR = "capteur", "Capteur IoT (token)"


# Roles consideres comme demandeurs (peuvent creer une FEB)
ROLES_DEMANDEURS = (
    RoleUtilisateur.RESP_APPRO,
    RoleUtilisateur.CHEF_CCE,
    RoleUtilisateur.CHEF_SLMG,
)

# Roles validateurs FEB (CG ou DFC)
ROLES_VALIDATEURS_FEB = (RoleUtilisateur.CG, RoleUtilisateur.DFC)

# Roles validateurs BC (DG ou DFC en PO)
ROLES_VALIDATEURS_BC = (RoleUtilisateur.DG, RoleUtilisateur.DFC)


# ═══════════════════════════════════════════════════════════════════
# MODELE UTILISATEUR
# ═══════════════════════════════════════════════════════════════════
class Utilisateur(AbstractBaseUser, PermissionsMixin):
    """
    Compte utilisateur du systeme d'approvisionnements.

    Authentification par 'identifiant' (et non 'username').
    Mot de passe hashe via bcrypt (cost >= 12).

    Regle metier critique :
        A 5 tentatives echouees consecutives, le compte est bloque
        automatiquement (est_actif=False) et l'Admin est notifie.
    """

    # ─── Identite ─────────────────────────────────────────────────
    identifiant = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Identifiant de connexion",
        help_text="Login unique, sans espace.",
    )
    email = models.EmailField(
        unique=True,
        verbose_name="Adresse email",
    )
    nom_complet = models.CharField(
        max_length=150,
        verbose_name="Nom complet",
    )
    role = models.CharField(
        max_length=20,
        choices=RoleUtilisateur.choices,
        verbose_name="Role metier",
        db_index=True,
    )

    # ─── Etat du compte ───────────────────────────────────────────
    est_actif = models.BooleanField(
        default=True,
        verbose_name="Compte actif",
        help_text="Faux = compte bloque (apres 5 echecs).",
    )
    tentatives_echecs = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Tentatives echouees consecutives",
    )
    date_dernier_echec = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Date du dernier echec de connexion",
    )
    date_blocage = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Date de blocage automatique",
    )
    motif_blocage = models.CharField(
        max_length=255, blank=True, default="",
        verbose_name="Motif du blocage",
    )

    # ─── Compatibilite Django Admin ───────────────────────────────
    is_staff = models.BooleanField(
        default=False,
        verbose_name="Acces admin Django",
    )

    # ─── Horodatage ───────────────────────────────────────────────
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de creation",
    )
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name="Date de derniere modification",
    )
    date_derniere_connexion_reussie = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Date de derniere connexion reussie",
    )

    # ─── Manager personnalise ─────────────────────────────────────
    objects = UtilisateurManager()

    USERNAME_FIELD = "identifiant"
    REQUIRED_FIELDS = ["email", "nom_complet", "role"]

    class Meta:
        db_table = "utilisateur"
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ["nom_complet"]
        indexes = [
            models.Index(fields=["role", "est_actif"]),
            models.Index(fields=["identifiant"]),
        ]

    def __str__(self):
        return f"{self.nom_complet} ({self.identifiant} — {self.get_role_display()})"

    # ─── Compatibilite Django ─────────────────────────────────────
    @property
    def is_active(self):
        """Surcharge pour pointer vers est_actif."""
        return self.est_actif

    @is_active.setter
    def is_active(self, valeur):
        self.est_actif = valeur

    # ─── Proprietes metier ────────────────────────────────────────
    @property
    def est_demandeur(self):
        """Vrai si l'utilisateur peut creer des FEB."""
        return self.role in (
            RoleUtilisateur.RESP_APPRO,
            RoleUtilisateur.CHEF_CCE,
            RoleUtilisateur.CHEF_SLMG,
        )

    @property
    def peut_valider_feb(self):
        """Vrai si l'utilisateur peut valider une FEB (CG ou DFC)."""
        return self.role in (RoleUtilisateur.CG, RoleUtilisateur.DFC)

    @property
    def peut_valider_bc(self):
        """Vrai si l'utilisateur peut valider un BC (DG ou DFC en PO)."""
        return self.role in (RoleUtilisateur.DG, RoleUtilisateur.DFC)

    @property
    def est_admin(self):
        """Vrai si l'utilisateur est administrateur du systeme."""
        return self.role == RoleUtilisateur.ADMIN

    # ─── Gestion des tentatives echouees ──────────────────────────
    def incrementer_tentatives(self, sauvegarder=True):
        """Incremente le compteur d'echecs et horodate."""
        self.tentatives_echecs += 1
        self.date_dernier_echec = timezone.now()
        if sauvegarder:
            self.save(update_fields=[
                "tentatives_echecs",
                "date_dernier_echec",
            ])

    def reinitialiser_tentatives(self, sauvegarder=True):
        """Remet le compteur a zero apres une connexion reussie."""
        if self.tentatives_echecs > 0:
            self.tentatives_echecs = 0
            self.date_dernier_echec = None
            if sauvegarder:
                self.save(update_fields=[
                    "tentatives_echecs",
                    "date_dernier_echec",
                ])

    def bloquer(self, motif="5 tentatives echouees consecutives", sauvegarder=True):
        """Bloque le compte (suppression logique de l'acces)."""
        self.est_actif = False
        self.date_blocage = timezone.now()
        self.motif_blocage = motif
        if sauvegarder:
            self.save(update_fields=[
                "est_actif",
                "date_blocage",
                "motif_blocage",
            ])

    def debloquer(self, sauvegarder=True):
        """Debloque le compte (reserve Admin)."""
        self.est_actif = True
        self.date_blocage = None
        self.motif_blocage = ""
        self.tentatives_echecs = 0
        self.date_dernier_echec = None
        if sauvegarder:
            self.save(update_fields=[
                "est_actif",
                "date_blocage",
                "motif_blocage",
                "tentatives_echecs",
                "date_dernier_echec",
            ])


# ═══════════════════════════════════════════════════════════════════
# MODELE SESSION
# ═══════════════════════════════════════════════════════════════════
class Session(models.Model):
    """
    Trace les sessions actives des utilisateurs.

    Permet d'auditer les connexions et stocker les jetons JWT.
    """

    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name="sessions",
        verbose_name="Utilisateur",
    )
    jeton_jwt = models.CharField(
        max_length=512,
        blank=True, default="",
        verbose_name="Jeton JWT (si API)",
    )
    cle_session_django = models.CharField(
        max_length=64,
        blank=True, default="",
        verbose_name="Cle session Django",
        db_index=True,
    )
    adresse_ip = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name="Adresse IP",
    )
    user_agent = models.TextField(
        blank=True, default="",
        verbose_name="User-Agent navigateur",
    )
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'ouverture de session",
    )
    date_derniere_activite = models.DateTimeField(
        auto_now=True,
        verbose_name="Date de derniere activite",
    )
    date_expiration = models.DateTimeField(
        verbose_name="Date d'expiration",
    )
    est_active = models.BooleanField(
        default=True,
        verbose_name="Session active",
    )

    class Meta:
        db_table = "session_utilisateur"
        verbose_name = "Session utilisateur"
        verbose_name_plural = "Sessions utilisateurs"
        ordering = ["-date_creation"]
        indexes = [
            models.Index(fields=["utilisateur", "est_active"]),
            models.Index(fields=["date_expiration"]),
        ]

    def __str__(self):
        statut = "active" if self.est_active else "expiree"
        return f"Session {self.utilisateur.identifiant} — {statut}"

    @property
    def est_expiree(self):
        """Vrai si la session a depasse sa date d'expiration."""
        return timezone.now() >= self.date_expiration

    def invalider(self):
        """Marque la session comme inactive (deconnexion)."""
        self.est_active = False
        self.save(update_fields=["est_active"])