"""
Configuration de l'environnement Jinja2.
"""
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from jinja2 import Environment


def environment(**options):
    """Construit l'environnement Jinja2 avec les helpers Django."""
    env = Environment(**options)

    env.globals.update({
        "static": staticfiles_storage.url,
        "url": reverse,
    })

    env.filters.update({
        "fcfa": filtre_montant_fcfa,
        "date_fr": filtre_date_francaise,
    })

    return env


def filtre_montant_fcfa(montant) -> str:
    """Formate un montant en F CFA avec separateurs de milliers."""
    if montant is None:
        return "0 F CFA"
    try:
        return f"{int(montant):,} F CFA".replace(",", " ")
    except (ValueError, TypeError):
        return "0 F CFA"


def filtre_date_francaise(date_obj) -> str:
    """Formate une date au format francais (JJ/MM/AAAA)."""
    if date_obj is None:
        return ""
    try:
        return date_obj.strftime("%d/%m/%Y")
    except (AttributeError, ValueError):
        return ""