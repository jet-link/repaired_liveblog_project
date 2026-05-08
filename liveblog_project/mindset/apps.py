from django.apps import AppConfig


class MindsetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mindset'

    def ready(self):
        import mindset.signals  # noqa: F401
