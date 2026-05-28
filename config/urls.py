"""
URLs racines du projet UCAO Approvisionnements.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.shortcuts import redirect
from django.urls import include, path


def vue_accueil(request):
    """
    Page d'accueil : redirige selon l'etat de connexion.

    - Utilisateur connecte  -> tableau de bord
    - Non connecte          -> page de connexion
    """
    if request.user.is_authenticated:
        return redirect("tableau_de_bord")
    return redirect("connexion")


urlpatterns = [
    path("", vue_accueil, name="accueil"),
    path("admin-django/", admin.site.urls),

    # Apps metier
    path("", include("apps.extensions.iot.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.comptes.urls")),
    path("referentiels/", include("apps.referentiels.urls")),
    path("", include("apps.approvisionnements.urls")),
    # path("predictions/", include("apps.extensions.prediction.urls")),
]


if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

    try:
        import debug_toolbar
        urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
    except ImportError:
        pass