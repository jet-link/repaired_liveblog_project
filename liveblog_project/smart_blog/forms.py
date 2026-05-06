# forms.py (вставь/замени соответствующие части в своём файле)
import re
import html
import bleach
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Case, Count, IntegerField, Q, When
from django.utils.translation import gettext_lazy as _
from .models import Item, Tag, Category, Comment
from .widgets import MultiFileInput, MultipleFileField
from .utils import normalize_comment_text
from .comment_html import expand_bare_domains, sanitize_and_linkify_comment_html

# try import CSSSanitizer (bleach >= 6)
try:
    from bleach.css_sanitizer import CSSSanitizer
except Exception:
    CSSSanitizer = None

# optional markdown conversion (pip install markdown)
try:
    import markdown as markdown_lib
except Exception:
    markdown_lib = None



# ---------- sanitize/linkify config ----------
LINKIFY_SKIP_TAGS = ['pre', 'code', 'a']

ALLOWED_TAGS = [
    'a', 'b', 'strong', 'i', 'em', 'u', 'mark',
    'ul', 'ol', 'li', 'p', 'br', 'span', 'div',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'pre', 'code', 'blockquote', 'img',
    'figure', 'figcaption',
    'table', 'caption', 'thead', 'tbody', 'tr', 'td', 'th'
]

# разрешённые CSS-свойства
ALLOWED_STYLES = [
    'color', 'background-color', 'text-align', 'font-weight',
    'font-style', 'text-decoration', 'margin', 'margin-left', 'margin-right',
    'padding', 'width', 'height', 'white-space', 'overflow', 'max-width'
]

# стартуем с базовых атрибутов bleach и расширяем
FINAL_ALLOWED_ATTRIBUTES = {}
FINAL_ALLOWED_ATTRIBUTES.update(getattr(bleach.sanitizer, 'ALLOWED_ATTRIBUTES', {}))

FINAL_ALLOWED_ATTRIBUTES.update({
    'a': ['href', 'title', 'target', 'rel', 'name'],
    'img': ['src', 'alt', 'title', 'width', 'height', 'style', 'class'],
    'p': ['style', 'class'],
    'span': ['style', 'class'],
    'div': ['style', 'class'],
    'blockquote': ['style', 'class'],
    'table': ['class', 'style'],
    'caption': ['class', 'style'],
    'thead': ['class', 'style'],
    'tbody': ['class', 'style'],
    'tr': ['class', 'style'],
    'td': ['colspan', 'rowspan', 'style', 'class', 'data-language'],
    'th': ['colspan', 'rowspan', 'style', 'class', 'data-language'],
    'pre': ['class', 'style', 'data-language'],
    'code': ['class', 'style', 'data-language'],
    'mark': ['class', 'style'],
    'h1': ['style'], 'h2': ['style'], 'h3': ['style'],
    'h4': ['style'], 'h5': ['style'], 'h6': ['style'],
    'figure': ['class', 'style'],
    'figcaption': ['class', 'style'],
})

# разрешаем любые data-* атрибуты через regex-ключ
FINAL_ALLOWED_ATTRIBUTES.update({
    re.compile(r'^data-'): True
})

def sanitize_item_text_html(raw: str) -> str:
    """
    Markdown (best-effort), bleach, linkify. Raises ValidationError if no visible text.
    Expects non-whitespace HTML or text; use after field-level normalization.
    """
    raw = raw or ""
    raw = raw.replace("\x00", "")
    raw = html.unescape(raw)

    converted = raw
    try:
        if markdown_lib and (
            re.search(r"(^```)|(^#{1,6}\s)", raw, flags=re.M)
            or re.search(r"\n```", raw)
        ):
            exts = ["fenced_code"]
            try:
                exts.append("codehilite")
            except Exception:
                pass
            converted = markdown_lib.markdown(raw, extensions=exts)
            try:
                converted = re.sub(
                    r'(<pre[^>]*>)\s*<code[^>]*class="([^"]*language-([a-z0-9_+-]+)[^"]*)"([^>]*)>',
                    lambda m: f'{m.group(1)}<code data-language="{m.group(3)}"{m.group(4)}>',
                    converted,
                    flags=re.I,
                )
                converted = re.sub(
                    r'<code[^>]*class="([^"]*language-([a-z0-9_+-]+)[^"]*)"([^>]*)>',
                    lambda m: f'<code data-language="{m.group(2)}"{m.group(3)}>',
                    converted,
                    flags=re.I,
                )
            except Exception:
                pass
    except Exception:
        converted = raw

    try:
        if CSSSanitizer is not None:
            css_sanitizer = CSSSanitizer(allowed_css_properties=ALLOWED_STYLES)
            cleaner = bleach.Cleaner(
                tags=ALLOWED_TAGS,
                attributes=FINAL_ALLOWED_ATTRIBUTES,
                strip=True,
                css_sanitizer=css_sanitizer,
            )
        else:
            cleaner = bleach.Cleaner(
                tags=ALLOWED_TAGS,
                attributes=FINAL_ALLOWED_ATTRIBUTES,
                strip=True,
            )
        cleaned = cleaner.clean(converted)
    except Exception:
        cleaned = bleach.clean(
            converted, tags=ALLOWED_TAGS, attributes=FINAL_ALLOWED_ATTRIBUTES, strip=True
        )

    try:
        cleaned = bleach.linkify(cleaned, skip_tags=LINKIFY_SKIP_TAGS, parse_email=False)
    except Exception:
        pass

    plain = re.sub(r"<[^>]+>", "", cleaned).strip()
    if not plain:
        raise ValidationError(_("Please write the post text *"))
    return cleaned


# ---------- форма ----------
class ItemCreateForm(forms.ModelForm):
    images = MultipleFileField(
        required=False,
        help_text="You can upload up to 10 images per post.",
        label=_('Upload media'),
    )

    body_pin_file = forms.FileField(
        required=False,
        label="",
        widget=forms.FileInput(
            attrs={
                "class": "item-images-file-input",
                "accept": ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "title": "Choose PDF or Word file",
            }
        ),
    )

    body_pin_clear = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput(attrs={"id": "id_body_pin_clear"}),
    )

    videos = MultipleFileField(
        required=False,
        help_text="You can upload up to 3 videos per post.",
        label=_('Upload videos'),
    )

    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all().order_by("tag_name"),
        required=False,
        label="Existing tags",
        widget=forms.CheckboxSelectMultiple(attrs={"class": "tag-badge-checkbox"}),
    )

    new_tags = forms.CharField(
        required=False,
        label=_('New tags'),
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": " ",
            "spellcheck": "true",
        }),
    )

    category = forms.ModelChoiceField(
        queryset=Category.objects.all().order_by("name"),
        required=False,
        label="Category",
        empty_label="— Select category —",
        widget=forms.Select(attrs={"class": "custom-select-category"}),
    )

    class Meta:
        model = Item
        fields = ["title", "text", "category", "tags", "new_tags"]
        labels = {"title": "Enter title", "text": "Post text"}
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                # single space: Bootstrap .form-floating shows the label only (no duplicate “Enter title” vs placeholder)
                "placeholder": " ",
                "required": True,
                "spellcheck": "true",
            }),
            "text": forms.Textarea(attrs={
                "class": "form-control editor-container__editor ckeditor",
                # "id": "editor",
                "placeholder": "Fill the text",
                "rows": 15,
                "spellcheck": "true",
            }),
        }

    def __init__(
        self, *args, item=None, tags_recent_limit=30, is_create=False, **kwargs
    ):
        self.is_create = bool(is_create)
        self._item = item
        self._body_pin_plain_snapshot = ""
        super().__init__(*args, **kwargs)
        if self.is_create:
            self.fields["text"].required = False
        if tags_recent_limit is None:
            self.fields["tags"].queryset = Tag.objects.all().order_by("tag_name")
            return
        limit = int(tags_recent_limit)
        published_items_filter = Q(items__is_published=True, items__deleted_at__isnull=True)
        top_qs = (
            Tag.objects.annotate(
                num_items=Count("items", filter=published_items_filter),
            )
            .order_by("-num_items", "-pk")[:limit]
        )
        ids = list(top_qs.values_list("pk", flat=True))
        if item is not None:
            for pk in item.tags.values_list("pk", flat=True):
                if pk not in ids:
                    ids.append(pk)
        if not ids:
            self.fields["tags"].queryset = Tag.objects.none()
            return
        preserved = Case(
            *[When(pk=pk, then=pos) for pos, pk in enumerate(ids)],
            output_field=IntegerField(),
        )
        self.fields["tags"].queryset = Tag.objects.filter(pk__in=ids).order_by(preserved)

    def clean_title(self):
        title = self.cleaned_data.get("title", "")
        if len(title) > 40:
            raise forms.ValidationError("Length of title should not exceed 40 symbols.")
        return title

    def clean_new_tags(self):
        value = (self.cleaned_data.get('new_tags') or '').strip()
        if not value:
            return value
        tokens = [t.strip().lower() for t in re.split(r'\s+', value) if t.strip()]
        value = ' '.join(tokens)
        from admin_panel.models import ForbiddenWord
        forbidden = list(ForbiddenWord.objects.filter(is_active=True))
        for token in tokens:
            for fw in forbidden:
                if fw.is_active and fw.word.lower() in token:
                    raise forms.ValidationError('Sorry, forbidden tag.')

        # Best-effort OpenAI moderation on tags. Tags are short, so latency is
        # acceptable. ANY error from the AI layer is non-fatal — we log and
        # accept the tag, so an outage of OpenAI cannot break tag submission.
        try:
            from django.conf import settings
            if getattr(settings, 'OPENAI_API_KEY', '').strip():
                from admin_panel.services.openai_moderator import openai_moderate
                found, _reason, _detected = openai_moderate(value)
                if found:
                    raise forms.ValidationError('Sorry, forbidden tag.')
        except forms.ValidationError:
            raise
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                'OpenAI tag moderation skipped due to transient error.', exc_info=True,
            )
        return value

    def clean_text(self):
        """
        1) Optionally convert fenced-code markdown -> HTML (if markdown lib present)
        2) Sanitize HTML via bleach (allow code, pre, table, mark, underline, data-*)
        3) Linkify (skipping pre/code/a)
        """
        raw = self.cleaned_data.get('text', '') or ''

        # normalize multiple line breaks (plain text)
        raw = re.sub(r'(\r?\n\s*){3,}', '\n\n', raw)
        raw = re.sub(r'^(\s*\r?\n)+', '\n', raw)
        raw = re.sub(r'(\r?\n\s*)+$', '\n', raw)

        # normalize empty HTML paragraphs (CKEditor output)
        raw = re.sub(r'(<p(?:\s[^>]*)?>\s*</p>\s*){2,}', '<p></p>', raw)
        raw = re.sub(r'^(<p(?:\s[^>]*)?>\s*</p>\s*)+', '', raw)
        raw = re.sub(r'(<p(?:\s[^>]*)?>\s*</p>\s*)+$', '', raw)
        raw = re.sub(r'(<p(?:\s[^>]*)?>\s*<br\s*/?>\s*</p>\s*){2,}', '<p><br></p>', raw)
        raw = raw.strip()

        if not raw or not raw.strip():
            if self.is_create:
                return ""
            pin_upload = None
            if self.files is not None:
                pin_upload = self.files.get("body_pin_file")
            if pin_upload and getattr(pin_upload, "size", 0):
                return ""
            clear = str(self.data.get("body_pin_clear") or "").lower() in (
                "1",
                "on",
                "true",
                "yes",
            )
            if (
                not clear
                and self._item
                and getattr(self._item, "body_pin_original", None)
            ):
                return ""
            raise ValidationError(_("Please write the post text *"))

        return sanitize_item_text_html(raw)

    def clean_body_pin_file(self):
        f = self.cleaned_data.get("body_pin_file")
        if not f:
            return f
        size = getattr(f, "size", None)
        try:
            if size is not None and int(size) == 0:
                raise ValidationError(_("File is empty"))
        except ValidationError:
            raise
        except (TypeError, ValueError):
            size = None
        if size is None:
            try:
                head = f.read(1)
            except Exception:
                head = b""
            try:
                f.seek(0)
            except Exception:
                pass
            if not head:
                raise ValidationError(_("File is empty"))
        name = (getattr(f, "name", "") or "").lower()
        if not (name.endswith(".pdf") or name.endswith(".docx")):
            raise ValidationError(_("Use a .pdf or .docx file."))
        max_b = 15 * 1024 * 1024
        if size is not None and int(size) > max_b:
            raise ValidationError(_("File too large (max 15 MB)."))
        return f

    def clean(self):
        cleaned_data = super().clean()
        if not self.is_create:
            return cleaned_data

        pin = cleaned_data.get("body_pin_file")
        if not pin:
            self._body_sourced_from_document = False
            self._body_pin_plain_snapshot = ""
            editor_part = cleaned_data.get("text") or ""
            plain = re.sub(r"<[^>]+>", "", editor_part).strip()
            if not plain:
                raise ValidationError({"text": [_("Please write the post text *")]})
            return cleaned_data

        pin_name = (pin.name or "").lower()
        self._body_pin_plain_snapshot = ""
        editor_part = cleaned_data.get("text") or ""
        editor_plain = re.sub(r"<[^>]+>", "", editor_part).strip()

        if pin_name.endswith(".pdf"):
            if editor_plain:
                cleaned_data["text"] = sanitize_item_text_html(editor_part)
            else:
                cleaned_data["text"] = ""
            self._body_sourced_from_document = True
            return cleaned_data

        if pin_name.endswith(".docx"):
            if editor_plain:
                cleaned_data["text"] = sanitize_item_text_html(editor_part)
            else:
                cleaned_data["text"] = ""
            self._body_sourced_from_document = True
            return cleaned_data

        self._body_sourced_from_document = False
        if not editor_plain:
            raise ValidationError({"text": [_("Please write the post text *")]})
        return cleaned_data


# simple CommentForm (оставил как есть; при необходимости можно расширить)
class CommentForm(forms.ModelForm):
    MAX_TEXT_LEN = 1500
    class Meta:
        model = Comment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={
                "class": "form-control auto-grow",
                "id": "id_comment_text",
                "placeholder": _("Write a comment…"),
                "rows": 1,
                "required": True,
                "spellcheck": "true",
            })
        }
        # error_messages = {
        #     "text": {
        #         "required": _("Please write a comment *")
        #     }
        # }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields["text"].error_messages = {"required": _("Please write a comment *")}

    def clean_text(self):
        raw = self.cleaned_data.get("text", "") or ""
        raw = raw.replace('\x00', '')
        normalized = normalize_comment_text(raw)
        text_for_count = re.sub(r'@\[\s*user\s*:\s*\d+\s*\],\s*', '', normalized)
        text_for_count = re.sub(r'[\r\n]', '', text_for_count)
        if len(text_for_count) > self.MAX_TEXT_LEN:
            raise ValidationError(_('Maximum 1500 characters (line breaks are not counted).'))

        expanded = expand_bare_domains(normalized)
        cleaned = sanitize_and_linkify_comment_html(expanded)

        plain = re.sub(r'<[^>]+>', '', cleaned).strip()
        if not plain or len(plain) < 2:
            raise forms.ValidationError("Please enter comment")

        return cleaned