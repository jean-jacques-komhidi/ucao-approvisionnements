"""
Modele Notification (in-app).

Une notification est generee a chaque event metier important :
- FEB soumise / validee / rejetee / cloturee
- BC genere / valide / envoye au fournisseur
"""
from django.conf import settings
from django.db import models


class TypeNotification(models.TextChoices):
    """Categories de notifications metier."""

    # FEB
    FEB_SOUMISE = "FEB_SOUMISE", "FEB soumise"
    FEB_VALIDEE = "FEB_VALIDEE", "FEB validee"
    FEB_REJETEE = "FEB_REJETEE", "FEB rejetee"
    FEB_CLOTUREE = "FEB_CLOTUREE", "FEB cloturee"

    # BC
    BC_GENERE = "BC_GENERE", "BC genere automatiquement"
    BC_VALIDE = "BC_VALIDE", "BC valide"
    BC_ENVOYE = "BC_ENVOYE", "BC envoye au fournisseur"

    # Generique
    INFO = "INFO", "Information"
    AVERTISSEMENT = "AVERTISSEMENT", "Avertissement"


class NiveauNotification(models.TextChoices):
    """Niveau de criticite (couleur badge)."""

    INFO = "INFO", "Information"
    SUCCES = "SUCCES", "Succes"
    AVERTISSEMENT = "AVERTISSEMENT", "Avertissement"
    DANGER = "DANGER", "Danger"


class Notification(models.Model):
    """Notification in-app envoyee a un utilisateur."""

    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications_recues",
        verbose_name="Destinataire",
    )
    expediteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="notifications_envoyees",
        null=True, blank=True,
        verbose_name="Expediteur",
    )

    type_notif = models.CharField(
        max_length=30,
        choices=TypeNotification.choices,
        default=TypeNotification.INFO,
    )
    niveau = models.CharField(
        max_length=20,
        choices=NiveauNotification.choices,
        default=NiveauNotification.INFO,
    )
    sujet = models.CharField(max_length=200)
    message = models.TextField()

    entite = models.CharField(max_length=50, blank=True, default="")
    entite_id = models.PositiveIntegerField(null=True, blank=True)
    url_action = models.CharField(max_length=255, blank=True, default="")

    est_lue = models.BooleanField(default=False, db_index=True)
    email_envoye = models.BooleanField(default=False)

    date_creation = models.DateTimeField(auto_now_add=True, db_index=True)
    date_lecture = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notification"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-date_creation"]
        indexes = [
            models.Index(fields=["destinataire", "est_lue"]),
            models.Index(fields=["-date_creation"]),
        ]

    def __str__(self):
        return f"[{self.get_type_notif_display()}] {self.sujet}"

    @property
    def couleur_badge(self):
        return {
            NiveauNotification.INFO: "info",
            NiveauNotification.SUCCES: "success",
            NiveauNotification.AVERTISSEMENT: "warning",
            NiveauNotification.DANGER: "error",
        }.get(self.niveau, "info")

    @property
    def icone(self):
        return {
            TypeNotification.FEB_SOUMISE: "file-plus",
            TypeNotification.FEB_VALIDEE: "check-circle-2",
            TypeNotification.FEB_REJETEE: "x-circle",
            TypeNotification.FEB_CLOTUREE: "lock",
            TypeNotification.BC_GENERE: "clipboard-list",
            TypeNotification.BC_VALIDE: "check-square",
            TypeNotification.BC_ENVOYE: "send",
            TypeNotification.INFO: "info",
            TypeNotification.AVERTISSEMENT: "alert-triangle",
        }.get(self.type_notif, "bell")

    def marquer_lue(self):
        from django.utils import timezone

        if not self.est_lue:
            self.est_lue = True
            self.date_lecture = timezone.now()
            self.save(update_fields=["est_lue", "date_lecture"])