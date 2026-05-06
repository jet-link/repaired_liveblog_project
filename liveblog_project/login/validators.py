"""Validators for login_app."""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Username: 1-100 chars, no spaces, allowed: letters, digits, *_-~()^$@?!
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9*_\-~()^$@?!]{1,100}$')

USERNAME_RULES_MSG = _(
    "Username: 1–100 characters, no spaces. "
    "Allowed: letters, digits, * _ - ~ ( ) ^ $ @ ? !"
)


def validate_username(value):
    """Validate username format."""
    if not value:
        return
    value = str(value).strip()
    if ' ' in value or '\t' in value:
        raise ValidationError(
            _("Username must not contain spaces."),
            code="username_no_spaces",
        )
    if len(value) > 100:
        raise ValidationError(
            _("Username must be at most 100 characters."),
            code="username_too_long",
        )
    if not USERNAME_REGEX.match(value):
        raise ValidationError(
            USERNAME_RULES_MSG,
            code="username_invalid_chars",
        )
