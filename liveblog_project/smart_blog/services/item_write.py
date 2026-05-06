"""Shared logic for public Item create/update: validation, tags, images.

Keeps views thin and avoids duplicate queries between create_item and edit_item.
"""
from __future__ import annotations

import logging
import re
from typing import List, Sequence

from django.core.files.base import ContentFile
from django.db.models import Max
from django.forms import BaseForm

from smart_blog.image_utils import (
    MAX_FILE_SIZE_BYTES,
    ALLOWED_MIME_TYPES,
    process_uploaded_files_parallel,
)
from smart_blog.models import Item, ItemImage, Tag

logger = logging.getLogger(__name__)

MAX_ITEM_IMAGES = 10


def merge_item_tags(cleaned_data: dict) -> List[Tag]:
    """Existing tags from the form plus new tag strings (already lowercased in form clean)."""
    merged: List[Tag] = list(cleaned_data["tags"])
    raw = (cleaned_data.get("new_tags") or "").strip()
    if not raw:
        return merged
    tokens = [t for t in re.split(r"\s+", raw) if t]
    if not tokens:
        return merged
    seen = {t.pk for t in merged}
    by_name = {t.tag_name: t for t in Tag.objects.filter(tag_name__in=tokens)}
    for name in tokens:
        tag = by_name.get(name)
        if tag is None:
            tag = Tag.objects.create(tag_name=name)
            by_name[name] = tag
        if tag.pk not in seen:
            merged.append(tag)
            seen.add(tag.pk)
    return merged


def validate_uploaded_image_files(files: Sequence[Any], form: BaseForm) -> bool:
    """
    Enforce count, MIME, and size. Mutates ``form`` with errors.
    Returns True if files pass (or list is empty), False if errors were added.
    """
    if len(files) > MAX_ITEM_IMAGES:
        form.add_error(
            None,
            f"You can upload up to {MAX_ITEM_IMAGES} images per post.",
        )
        return False
    bad = [
        f.name
        for f in files
        if (getattr(f, "content_type", None) or "").lower().strip() not in ALLOWED_MIME_TYPES
    ]
    if bad:
        form.add_error(None, f"Unsupported file types: {', '.join(bad)}")
        return False
    for f in files:
        f.seek(0, 2)
        sz = f.tell()
        f.seek(0)
        if sz > MAX_FILE_SIZE_BYTES:
            form.add_error(
                None,
                f"File {f.name} too large ({sz / (1024*1024):.1f} MB). "
                f"Max {MAX_FILE_SIZE_BYTES / (1024*1024):.0f} MB.",
            )
            return False
    return True


def _parse_image_delete_ids(raw_ids: Sequence[Any]) -> List[int]:
    out: List[int] = []
    for x in raw_ids or []:
        s = str(x).strip()
        if s.isdigit():
            out.append(int(s))
    return out


def validate_edit_image_totals(item: Item, files: Sequence[Any], delete_raw: Sequence[Any], form: BaseForm) -> bool:
    """Uses only images that actually belong to this item when counting removals."""
    delete_ids = _parse_image_delete_ids(delete_raw)
    n_existing = ItemImage.objects.filter(item=item).count()
    n_remove = ItemImage.objects.filter(item=item, pk__in=delete_ids).count() if delete_ids else 0
    remaining = max(0, n_existing - n_remove)
    total_after = remaining + len(files)
    if total_after > MAX_ITEM_IMAGES:
        form.add_error(
            None,
            f"Total images after updates cannot exceed {MAX_ITEM_IMAGES}.",
        )
        return False
    return True


def _strip_item_image_files(img: ItemImage) -> None:
    for fn in ("image", "image_thumbnail", "image_medium"):
        try:
            field = getattr(img, fn, None)
            if field and getattr(field, "name", None):
                field.delete(save=False)
        except Exception:
            logger.exception("Failed to delete %s file for ItemImage %s", fn, img.pk)


def delete_item_images_by_ids(item: Item, raw_id_list: Sequence[Any]) -> int:
    ids = _parse_image_delete_ids(raw_id_list)
    if not ids:
        return 0
    qs = ItemImage.objects.filter(item=item, pk__in=ids)
    n = 0
    for img in qs:
        _strip_item_image_files(img)
        img.delete()
        n += 1
    return n


def attach_item_images_from_uploads(item: Item, files: Sequence[Any]) -> None:
    file_list = list(files)[:MAX_ITEM_IMAGES]
    if not file_list:
        return
    agg = ItemImage.objects.filter(item=item).aggregate(mx=Max("sort_order"))
    next_order = (agg["mx"] if agg["mx"] is not None else -1) + 1
    processed_list = process_uploaded_files_parallel(file_list, item.pk)
    for i, (f, processed) in enumerate(zip(file_list, processed_list)):
        order = next_order + i
        if processed:
            ItemImage.objects.create(
                item=item,
                image=processed["image"],
                image_thumbnail=processed["image_thumbnail"],
                image_medium=processed["image_medium"],
                width=processed.get("width"),
                height=processed.get("height"),
                sort_order=order,
            )
        else:
            f.seek(0)
            ItemImage.objects.create(
                item=item,
                image=ContentFile(
                    f.read(),
                    name=getattr(f, "name", None) or "upload.bin",
                ),
                sort_order=order,
            )
