"""Admin panel forms."""
from django import forms
from smart_blog.models import Item, Category, Tag
from smart_blog.forms import ItemCreateForm as BaseItemCreateForm


class ItemAdminCreateForm(BaseItemCreateForm):
    """Admin-styled create form matching edit layout."""

    class Meta(BaseItemCreateForm.Meta):
        widgets = {
            'title': forms.TextInput(attrs={'class': 'admin-input', 'placeholder': 'Enter title', 'spellcheck': 'true'}),
            'text': forms.Textarea(attrs={'id': 'id_text', 'class': 'admin-textarea ckeditor', 'rows': 12, 'placeholder': 'Fill the text', 'spellcheck': 'true'}),
            'category': forms.Select(attrs={'class': 'admin-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, tags_recent_limit=None, **kwargs)
        self.label_suffix = ''
        self.fields['title'].label = 'Post title'
        self.fields['text'].label = 'Post body'
        self.fields['tags'].widget = forms.SelectMultiple(attrs={'class': 'admin-select', 'size': 6})
        self.fields['new_tags'].widget = forms.TextInput(attrs={
            'class': 'admin-input',
            'placeholder': 'New tags, space-separated · optional',
            'spellcheck': 'true',
        })
        self.fields['images'].label = 'Upload images · optional'
        self.fields['images'].widget.attrs.update({'class': 'admin-file-input'})


class ItemAdminEditForm(forms.ModelForm):
    """Simplified form for admin post editing."""

    status = forms.ChoiceField(
        choices=[('published', 'Published'), ('draft', 'Draft')],
        widget=forms.Select(attrs={'class': 'admin-select'}),
        label='Status',
    )
    body_pin_clear = forms.BooleanField(
        required=False,
        label='',
        widget=forms.HiddenInput(attrs={'id': 'id_body_pin_clear'}),
    )

    class Meta:
        model = Item
        fields = ['title', 'text', 'category', 'tags', 'slug']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'admin-input', 'placeholder': 'Title', 'spellcheck': 'true'}),
            'text': forms.Textarea(attrs={'id': 'id_text', 'class': 'admin-textarea ckeditor', 'rows': 12, 'placeholder': 'Post text', 'spellcheck': 'true'}),
            'category': forms.Select(attrs={'class': 'admin-select'}),
            'tags': forms.SelectMultiple(attrs={'class': 'admin-select', 'size': 6}),
            'slug': forms.TextInput(attrs={'class': 'admin-input', 'placeholder': 'slug'}),
        }
        labels = {
            'title': 'Post title',
            'text': 'Post body',
            'category': 'Category',
            'tags': 'Tags',
            'slug': 'Slug',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ''
        if self.instance and self.instance.pk:
            self.fields['status'].initial = 'published' if self.instance.is_published else 'draft'

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.is_published = (self.cleaned_data['status'] == 'published')
        if commit:
            instance.save()
            self.save_m2m()
        return instance
