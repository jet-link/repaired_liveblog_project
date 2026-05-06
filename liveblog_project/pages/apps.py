from django.apps import AppConfig


class PagesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pages'

    def ready(self):
        import pages.signals  # noqa: F401
        from pages.signals import connect_sitemap_cache_invalidation

        connect_sitemap_cache_invalidation()
