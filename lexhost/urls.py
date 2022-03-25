"""lexhost URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, re_path
from django.contrib import admin

from .apps import land, sitemapping
from .apps.legacy import LegacyPathHandler
from .apps.search import views as search
from .apps.read import Read

# Error handlers
handler500 = 'lexhost.apps.exceptions.internal_error'
handler404 = 'lexhost.apps.exceptions.not_found'
handler403 = 'lexhost.apps.exceptions.forbidden'
handler400 = 'lexhost.apps.exceptions.bad_request'


urlpatterns = [
    path('admin', admin.site.urls),
    path('', land.index, name='home'),
    path('sitemap.xml', sitemapping.view),
    re_path('^(?P<obsolete_document_path>[a-zA-Z0-9-_]+)/?$',
            land.handle_obsolete_document_path),
    # TODO: register botapi and indexadmin
    path('eu/search', search.corpus_search),
    path('<slug:domain>/<slug:document_id>/search', search.document_search),
]

# Read.register(urlpatterns)

LegacyPathHandler.register(urlpatterns)
