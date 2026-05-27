"""Vues de l'extension IoT."""
import json
import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.comptes.models import RoleUtilisateur

from .models import (
    AlerteIoT,
    Equipement,
    Localisation,
    StatutEquipement,
    TypeAlerte,
    ZoneGeographique,
)
from .services import enregistrer_signal_capteur, traiter_alerte

logger = logging.getLogger(__name__)


def _peut_voir_iot(user):
    """Admin et Resp.Appro peuvent acceder a l'IoT."""
    return user.role in (RoleUtilisateur.ADMIN, RoleUtilisateur.RESP_APPRO)


# ═══════════════════════════════════════════════════════════════════
# API REST POUR CAPTEURS
# ═══════════════════════════════════════════════════════════════════
@csrf_exempt
@require_http_methods(["POST"])
def api_signal_capteur(request):
    """
    Endpoint API recevant les signaux des capteurs RFID/BLE.

    Request JSON :
    {
        "rfid_tag": "TAG-12345",
        "zone_id": 3,
        "signal_force": 87,
        "capteur_id": "CAPTEUR-A",
        "token": "XXXX..."
    }

    Auth : token de l'equipement.
    """
    try:
        data = json.loads(request.body.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"erreur": "JSON invalide"}, status=400)

    rfid_tag = data.get("rfid_tag")
    zone_id = data.get("zone_id")
    token = data.get("token", "")
    signal_force = data.get("signal_force", 100)
    capteur_id = data.get("capteur_id", "")

    if not rfid_tag or not zone_id:
        return JsonResponse(
            {"erreur": "Champs requis : rfid_tag, zone_id"},
            status=400,
        )

    # Authentification capteur
    try:
        equipement = Equipement.objects.get(rfid_tag=rfid_tag)
    except Equipement.DoesNotExist:
        return JsonResponse({"erreur": "Equipement inconnu"}, status=404)

    if equipement.token_capteur != token:
        logger.warning("Tentative d'acces avec token invalide pour %s", rfid_tag)
        return JsonResponse({"erreur": "Token invalide"}, status=403)

    if not equipement.est_suivi_iot:
        return JsonResponse({"erreur": "Suivi IoT desactive"}, status=403)

    # Recupere la zone
    try:
        zone = ZoneGeographique.objects.get(pk=zone_id, est_active=True)
    except ZoneGeographique.DoesNotExist:
        return JsonResponse({"erreur": "Zone inconnue"}, status=404)

    # Enregistre le signal
    localisation, alerte = enregistrer_signal_capteur(
        equipement=equipement,
        zone=zone,
        signal_force=signal_force,
        capteur_id=capteur_id,
    )

    response = {
        "ok": True,
        "localisation_id": localisation.pk,
        "alerte_declenchee": alerte is not None,
    }

    if alerte:
        response["alerte"] = {
            "id": alerte.pk,
            "type": alerte.type_alerte,
            "message": alerte.message,
        }

    return JsonResponse(response)


# ═══════════════════════════════════════════════════════════════════
# DASHBOARD IoT
# ═══════════════════════════════════════════════════════════════════
@login_required
def dashboard_iot(request):
    """Vue principale du module IoT."""
    if not _peut_voir_iot(request.user):
        messages.error(request, "Acces reserve a l'admin et au Resp.Approvisionnements.")
        return redirect("tableau_de_bord")

    # KPI
    nb_equipements = Equipement.objects.filter(est_suivi_iot=True).count()
    nb_zones_autorisees = ZoneGeographique.objects.filter(est_zone_autorisee=True, est_active=True).count()
    alertes_actives = AlerteIoT.objects.filter(est_traitee=False).count()
    equipements_sortis = Equipement.objects.filter(statut=StatutEquipement.SORTI_ZONE).count()

    # Equipements par zone
    par_zone = (
        Equipement.objects
        .filter(est_suivi_iot=True, zone_actuelle__isnull=False)
        .values("zone_actuelle__nom")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # Dernieres alertes
    alertes_recentes = (
        AlerteIoT.objects
        .select_related("equipement", "zone_actuelle")
        .order_by("-timestamp")[:5]
    )

    # Donnees pour la carte (zones avec equipements)
    zones_carte = []
    for z in ZoneGeographique.objects.filter(est_active=True).annotate(
        nb_equipements=Count("equipements_presents")
    ):
        zones_carte.append({
            "id": z.pk,
            "nom": z.nom,
            "batiment": z.batiment,
            "etage": z.etage,
            "type": z.get_type_zone_display(),
            "autorisee": z.est_zone_autorisee,
            "nb_equipements": z.nb_equipements,
            "lat": float(z.latitude) if z.latitude else None,
            "lng": float(z.longitude) if z.longitude else None,
        })

    kpi = {
        "nb_equipements": nb_equipements,
        "nb_zones_autorisees": nb_zones_autorisees,
        "alertes_actives": alertes_actives,
        "equipements_sortis": equipements_sortis,
    }

    return render(request, "iot/dashboard.html", {
        "kpi": kpi,
        "par_zone": par_zone,
        "alertes_recentes": alertes_recentes,
        "zones_carte": json.dumps(zones_carte),
    })


# ═══════════════════════════════════════════════════════════════════
# EQUIPEMENTS — LISTE
# ═══════════════════════════════════════════════════════════════════
@login_required
def equipements_liste(request):
    """Liste tous les equipements."""
    if not _peut_voir_iot(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    queryset = Equipement.objects.select_related("zone_actuelle", "fournisseur")

    # Filtres
    statut_filtre = request.GET.get("statut", "").strip()
    if statut_filtre:
        queryset = queryset.filter(statut=statut_filtre)

    recherche = request.GET.get("q", "").strip()
    if recherche:
        queryset = queryset.filter(
            Q(designation__icontains=recherche) |
            Q(numero_serie__icontains=recherche) |
            Q(rfid_tag__icontains=recherche)
        )

    return render(request, "iot/equipements_liste.html", {
        "equipements": queryset,
        "statuts": StatutEquipement.choices,
        "statut_filtre": statut_filtre,
        "recherche": recherche,
    })


# ═══════════════════════════════════════════════════════════════════
# EQUIPEMENT — DETAIL + HISTORIQUE
# ═══════════════════════════════════════════════════════════════════
@login_required
def equipement_detail(request, pk):
    """Detail d'un equipement avec son historique recent."""
    if not _peut_voir_iot(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    equipement = get_object_or_404(
        Equipement.objects.select_related("zone_actuelle", "fournisseur"),
        pk=pk,
    )

    # Historique 50 derniers signaux
    historique = (
        equipement.localisations.select_related("zone")
        .order_by("-timestamp")[:50]
    )

    # Alertes
    alertes = equipement.alertes.order_by("-timestamp")[:20]

    return render(request, "iot/equipement_detail.html", {
        "equipement": equipement,
        "historique": historique,
        "alertes": alertes,
    })


# ═══════════════════════════════════════════════════════════════════
# ALERTES IoT — LISTE
# ═══════════════════════════════════════════════════════════════════
@login_required
def alertes_liste(request):
    """Liste des alertes IoT."""
    if not _peut_voir_iot(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    queryset = AlerteIoT.objects.select_related(
        "equipement", "zone_actuelle", "zone_quittee", "traite_par"
    ).order_by("-timestamp")

    # Filtre traitee/non traitee
    filtre = request.GET.get("filtre", "actives")
    if filtre == "actives":
        queryset = queryset.filter(est_traitee=False)
    elif filtre == "traitees":
        queryset = queryset.filter(est_traitee=True)
    # else "toutes"

    nb_actives = AlerteIoT.objects.filter(est_traitee=False).count()
    nb_traitees = AlerteIoT.objects.filter(est_traitee=True).count()

    return render(request, "iot/alertes_liste.html", {
        "alertes": queryset,
        "filtre": filtre,
        "nb_actives": nb_actives,
        "nb_traitees": nb_traitees,
    })


# ═══════════════════════════════════════════════════════════════════
# ALERTE — TRAITER
# ═══════════════════════════════════════════════════════════════════
@login_required
@require_http_methods(["POST"])
def alerte_traiter(request, pk):
    """Marque une alerte comme traitee."""
    if not _peut_voir_iot(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    alerte = get_object_or_404(AlerteIoT, pk=pk)
    commentaire = request.POST.get("commentaire", "").strip()

    if alerte.est_traitee:
        messages.info(request, "Alerte deja traitee.")
    else:
        traiter_alerte(alerte, request.user, commentaire)
        messages.success(request, "Alerte marquee comme traitee.")

    return redirect("iot_alertes_liste")


# ═══════════════════════════════════════════════════════════════════
# ZONES — LISTE
# ═══════════════════════════════════════════════════════════════════
@login_required
def zones_liste(request):
    """Liste des zones geographiques."""
    if not _peut_voir_iot(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    zones = ZoneGeographique.objects.filter(est_active=True).annotate(
        nb_equipements=Count("equipements_presents")
    )

    return render(request, "iot/zones_liste.html", {
        "zones": zones,
    })

@login_required
def alerte_detail(request, pk):
    """Detail d'une alerte IoT specifique."""
    if not _peut_voir_iot(request.user):
        messages.error(request, "Acces refuse.")
        return redirect("tableau_de_bord")

    alerte = get_object_or_404(
        AlerteIoT.objects.select_related(
            "equipement", "zone_actuelle", "zone_quittee", "traite_par"
        ),
        pk=pk,
    )

    return render(request, "iot/alerte_detail.html", {
        "alerte": alerte,
    })