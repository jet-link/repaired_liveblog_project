from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import index as sitemap_index
from django.contrib.sitemaps.views import sitemap as sitemap_section
from django.http import HttpResponse
from smart_blog import views as smart_views
from smart_blog.sitemaps import PUBLIC_SITEMAPS


def robots_txt(request):
    body = (
        "User-agent: *\n"
        "Disallow: /admin/\n"
        "Disallow: /profile/\n"
        "Disallow: /login/\n"
        "Disallow: /register/\n"
        "\n"
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}\n"
    )
    return HttpResponse(body, content_type="text/plain; charset=utf-8")


urlpatterns = [
    path('admin/', include('admin_panel.urls')),
    path('accounts/', include('allauth.urls')),
    path('sitemap.xml', sitemap_index, {'sitemaps': PUBLIC_SITEMAPS}, name='sitemap_index'),
    path(
        'sitemap-<section>.xml',
        sitemap_section,
        {'sitemaps': PUBLIC_SITEMAPS},
        name='django.contrib.sitemaps.views.sitemap',
    ),
    path('robots.txt', robots_txt, name='robots_txt'),

    # Global search at /search/
    path('search/', smart_views.search_view, name='global_search'),

    # Public feed hubs + /tag/, /post/, /brainews/; APIs and legacy paths under /blog/ (see smart_blog.urls)
    path('', include('smart_blog.urls')),

    # Auth at /login/, /register/; profile at /profile/<username>/
    path('', include('login.urls')),

    # Pages last so slug patterns do not shadow other routes
    path('', include('pages.urls', namespace='pages')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        urlpatterns = [path('__debug__/', include('debug_toolbar.urls'))] + urlpatterns

handler404 = 'pages.views.custom_404_view'
handler403 = 'pages.views.custom_403_view'
handler500 = 'django.views.defaults.server_error'