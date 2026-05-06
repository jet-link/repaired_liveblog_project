from django.apps import AppConfig


def _patch_user_username_validators():
    """Replace Django's default username validator with our custom one."""
    from django.contrib.auth import get_user_model
    from .validators import validate_username

    User = get_user_model()
    username_field = User._meta.get_field('username')
    username_field.validators = [validate_username]


class LoginConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'login'

    def ready(self):
        _patch_user_username_validators()
