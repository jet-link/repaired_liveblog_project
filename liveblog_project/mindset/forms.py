"""Mindset forms."""
from __future__ import annotations

import re

from django import forms
from django.core.exceptions import ValidationError

from smart_blog.comment_html import (
    comment_html_for_template,
    expand_bare_domains,
    sanitize_and_linkify_comment_html,
)

from .body_html import html_to_plain_text
from .models import Theme


class ThemeForm(forms.ModelForm):
    """CKEditor body — single field. Title comes from the body itself (preview)."""

    MAX_LEN = 5000
    MIN_LEN = 2

    class Meta:
        model = Theme
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'mindset-ckeditor',
                'id': 'id_theme_body',
                'rows': 6,
                'placeholder': 'Share your thoughts… Use #hashtags to group similar themes.',
            }),
        }

    def clean_body(self):
        raw = self.cleaned_data.get('body', '') or ''
        raw = raw.replace('\x00', '').strip()
        if not raw:
            raise ValidationError('Please write your theme body.')

        expanded = expand_bare_domains(raw)
        cleaned = sanitize_and_linkify_comment_html(expanded)
        plain = html_to_plain_text(cleaned)

        if len(plain) < self.MIN_LEN:
            raise ValidationError('Theme body is too short.')
        if len(re.sub(r'\s+', '', plain)) > self.MAX_LEN:
            raise ValidationError(f'Maximum {self.MAX_LEN} characters.')

        return cleaned


class ReplyForm(forms.Form):
    """Inline reply (textarea, no CKEditor)."""

    MAX_LEN = 1500
    MIN_LEN = 1

    body = forms.CharField(
        max_length=10_000,
        widget=forms.Textarea(attrs={
            'class': 'form-control auto-grow mindset-reply-input',
            'rows': 1,
            'placeholder': 'Write a reply…',
            'spellcheck': 'true',
        }),
    )

    def clean_body(self):
        raw = self.cleaned_data.get('body', '') or ''
        raw = raw.replace('\x00', '').strip()
        if not raw:
            raise ValidationError('Reply cannot be empty.')

        expanded = expand_bare_domains(raw)
        cleaned = comment_html_for_template(expanded)
        plain = html_to_plain_text(cleaned)

        if len(plain) < self.MIN_LEN:
            raise ValidationError('Reply is too short.')
        if len(re.sub(r'\s+', '', plain)) > self.MAX_LEN:
            raise ValidationError(f'Maximum {self.MAX_LEN} characters.')

        return cleaned
