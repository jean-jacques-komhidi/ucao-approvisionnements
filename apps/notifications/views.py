"""Vues de l'app notifications."""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Notification

logger = logging.getLogger(__name__)


@login_required
def liste(request):
    """Liste toutes les notifications de l'utilisateur."""
    notifications = (
        Notification.objects
        .filter(destinataire=request.user)
        .select_related("expediteur")
        .order_by("-date_creation")
    )

    non_lues = notifications.filter(est_lue=False).count()

    return render(request, "notifications/liste.html", {
        "notifications": notifications,
        "non_lues": non_lues,
        "total": notifications.count(),
    })


@login_required
@require_http_methods(["POST"])
def marquer_lue(request, pk):
    """Marque une notification comme lue."""
    notif = get_object_or_404(Notification, pk=pk, destinataire=request.user)
    notif.marquer_lue()

    if notif.url_action:
        return redirect(notif.url_action)
    return redirect("notifications_liste")


@login_required
@require_http_methods(["POST"])
def marquer_toutes_lues(request):
    """Marque toutes les notifications comme lues."""
    nb = (
        Notification.objects
        .filter(destinataire=request.user, est_lue=False)
        .update(est_lue=True, date_lecture=timezone.now())
    )
    messages.success(request, f"{nb} notification(s) marquee(s) comme lue(s).")
    return redirect("notifications_liste")


@login_required
def compteur_non_lues(request):
    """Endpoint AJAX pour rafraichir le compteur."""
    count = (
        Notification.objects
        .filter(destinataire=request.user, est_lue=False)
        .count()
    )
    return JsonResponse({"count": count})