"""Login app context processors."""
from django.conf import settings


def user_obj_context(request):
    """Provide user_obj for base template (CURRENT_AVATAR). Defaults to request.user.
    Profile pages override with the viewed user."""
    return {"user_obj": getattr(request, "user", None)}


def turnstile_context(request):
    key = getattr(settings, 'TURNSTILE_SITE_KEY', '') or ''
    return {'turnstile_site_key': key}


def oauth_buttons_context(request):
    return {
        'oauth_google_enabled': getattr(
            settings, 'SOCIALACCOUNT_GOOGLE_ENABLED', False
        ),
        'oauth_apple_enabled': getattr(
            settings, 'SOCIALACCOUNT_APPLE_ENABLED', False
        ),
    }
