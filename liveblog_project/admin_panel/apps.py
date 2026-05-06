from django.apps import AppConfig


class AdminPanelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_panel'
    verbose_name = 'Admin Panel'

    def ready(self):
        import admin_panel.signals  # noqa: F401 - connect post_save for Item/Comment
