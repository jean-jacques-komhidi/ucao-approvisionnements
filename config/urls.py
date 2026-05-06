"""
URLs racines du projet UCAO Approvisionnements.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns



def vue_accueil_temporaire(request):
    """Page d'accueil temporaire pour vérifier que Django fonctionne."""
    return HttpResponse(
        "<h1>UCAO Approvisionnements</h1>"
        "<p>Le projet Django est correctement configure.</p>"
        "<p>Prochaine etape : developper les apps metier.</p>"
    )


urlpatterns = [
    path("", vue_accueil_temporaire, name="accueil_temporaire"),
    path("admin-django/", admin.site.urls),

    # A decommenter au fur et a mesure du developpement :
    path("", include("apps.comptes.urls")),
    path("referentiels/", include("apps.referentiels.urls")),
    path("", include("apps.approvisionnements.urls")),
    # path("iot/", include("apps.extensions.iot.urls")),
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