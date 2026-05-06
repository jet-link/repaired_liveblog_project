"""File widgets/fields that accept multiple uploads (images, videos)."""
from django import forms
from django.forms.widgets import FileInput


class MultiFileInput(FileInput):
    """<input type="file" multiple>; returns a list via `value_from_datadict`."""

    allow_multiple_selected = True

    def __init__(self, attrs=None):
        attrs = attrs or {}
        attrs.update({"multiple": True})
        super().__init__(attrs)


class MultipleFileField(forms.FileField):
    """
    FileField compatible with ``MultiFileInput``: runs FileField.clean over each
    uploaded file instead of failing with "No file was submitted. Check the
    encoding type on the form." when Django hands it a list of files.
    """

    widget = MultiFileInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultiFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(d, initial) for d in data if d]
        return single_clean(data, initial)
