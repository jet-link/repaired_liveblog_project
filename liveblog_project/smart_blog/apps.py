from django.apps import AppConfig


class SmartBlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'smart_blog'

    def ready(self):
        import smart_blog.signals  # noqa: F401

