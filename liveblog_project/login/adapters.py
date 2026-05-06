"""django-allauth adapters: redirects, social usernames, single-session policy."""
from __future__ import annotations

import re
import uuid

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.shortcuts import redirect

from login.middleware import is_user_online
from login.validators import validate_username


def _unique_username(base: str) -> str:
    User = get_user_model()
    cleaned = re.sub(r'[^a-zA-Z0-9*_\-~()^$@?!]', '', base)[:15]
    if not cleaned:
        cleaned = ('u' + uuid.uuid4().hex[:8])[:15]
    candidate = cleaned
    suffix_num = 0
    while True:
        try:
            validate_username(candidate)
        except ValidationError:
            candidate = ('u' + uuid.uuid4().hex[:8])[:15]
            cleaned = candidate
            suffix_num = 0
            continue
        if not User.objects.filter(username=candidate).exists():
            return candidate
        suffix_num += 1
        suf = str(suffix_num)
        candidate = (cleaned[: max(1, 15 - len(suf))] + suf)[:15]
        if suffix_num > 9999:
            candidate = ('u' + uuid.uuid4().hex[:8])[:15]
            cleaned = candidate
            suffix_num = 0


class AccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        if request.user.is_authenticated:
            from django.urls import reverse

            return reverse('login_app:profile', kwargs={'username': request.user.username})
        return super().get_login_redirect_url(request)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user
        if user and getattr(user, 'pk', None) and is_user_online(user):
            messages.error(request, 'User already online')
            raise ImmediateHttpResponse(redirect(settings.LOGIN_URL))
        super().pre_social_login(request, sociallogin)

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        if user.pk:
            return user
        email = (data.get('email') or '').strip()
        uid = str(getattr(sociallogin.account, 'uid', '') or '')
        base = (email.split('@')[0] if '@' in email else '') or uid[:12] or 'user'
        user.username = _unique_username(base)
        return user
