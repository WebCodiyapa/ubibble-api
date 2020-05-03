# -*- coding: utf-8 -*-
from django.contrib import admin
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.conf import settings


admin.autodiscover()

urlpatterns = [
    url(r'^api/', include('apps.api_rest.urls')),
    url(r'jet/', include('jet.urls', 'jet')),  # Django JET URLS
    url(r'jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),  # Django JET dashboard URLS
    url(r'^admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(
            settings.STATIC_URL,
            document_root=settings.STATIC_ROOT
    ) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns.append(
        url(r'__debug__/', include(debug_toolbar.urls)),
    )
