# smart_blog/image_utils.py
"""
Обработка изображений при загрузке:
- Ограничение ширины (max 1600px)
- Конвертация в WebP (качество 85-90%)
- Генерация thumbnail (~300px), medium (~800px), feed (~1024px), large (~1400-1600px)
- Проверка MIME и размера файла
- Несколько файлов могут обрабатываться параллельно (создание поста).
"""
import io
import os
import logging
from typing import Optional
import hashlib
import time
import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)

# Ограничения
MAX_IMAGE_WIDTH = 1600
MAX_FILE_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB
ALLOWED_MIME_TYPES = frozenset({
    "image/jpeg", "image/jpg", "image/png", "image/webp"
})
WEBP_QUALITY = 88
# Параллельная обработка при нескольких вложениях
IMAGE_PROCESS_MAX_WORKERS = 4

# Размеры для responsive
SIZE_THUMBNAIL = 300
SIZE_MEDIUM = 800
SIZE_FEED = 1024
SIZE_LARGE = 1600
WEBP_QUALITY_PREVIEW = 85

# Display / layout hints for post galleries (derived from pixel dimensions).
ORIENTATION_LANDSCAPE = "landscape"
ORIENTATION_PORTRAIT = "portrait"
ORIENTATION_WIDE = "wide"
ORIENTATION_SQUARE = "square"


def compute_orientation_kind(width: Optional[int], height: Optional[int]) -> str:
    """Classify aspect ratio for editorial layout (not the same as EXIF orientation)."""
    if not width or not height:
        return ORIENTATION_LANDSCAPE
    w, h = int(width), int(height)
    if h <= 0:
        return ORIENTATION_LANDSCAPE
    ratio = w / h
    if ratio >= 2.0:
        return ORIENTATION_WIDE
    if ratio <= 0.82:
        return ORIENTATION_PORTRAIT
    if 0.88 <= ratio <= 1.12:
        return ORIENTATION_SQUARE
    return ORIENTATION_LANDSCAPE


def _get_content_type(ufile):
    """Извлекает MIME из UploadedFile."""
    ct = getattr(ufile, "content_type", None) or ""
    return ct.lower().strip()


def _validate_file(ufile):
    """
    Проверяет MIME-тип и размер файла.
    Raises ValueError при ошибке.
    """
    ct = _get_content_type(ufile)
    if ct not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Unsupported image type: {ct}")

    ufile.seek(0, 2)
    size = ufile.tell()
    ufile.seek(0)
    if size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File too large ({size / (1024*1024):.1f} MB). Maximum allowed: {MAX_FILE_SIZE_BYTES / (1024*1024):.0f} MB"
        )


def _validate_bytes(raw: bytes, content_type: str):
    ct = (content_type or "").lower().strip()
    if ct not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Unsupported image type: {ct}")
    if len(raw) > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File too large ({len(raw) / (1024*1024):.1f} MB). Maximum allowed: {MAX_FILE_SIZE_BYTES / (1024*1024):.0f} MB"
        )


def _open_image(ufile):
    """Открывает изображение из UploadedFile, применяет EXIF Orientation, конвертирует в RGB."""
    ufile.seek(0)
    img = Image.open(ufile)
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    if img.mode == "RGB":
        return img
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        return background
    return img.convert("RGB")


def _resize_to_max_width(img, max_width, resample=Image.Resampling.LANCZOS):
    """Масштабирует по ширине, сохраняя соотношение сторон."""
    w, h = img.size
    if w <= max_width:
        return img
    ratio = max_width / w
    new_h = int(h * ratio)
    return img.resize((max_width, new_h), resample)


def _save_webp(img, max_width, quality=WEBP_QUALITY, resample=Image.Resampling.LANCZOS):
    """
    Масштабирует и сохраняет в WebP.
    Для preview/medium можно передать BILINEAR — заметно быстрее LANCZOS при малых потерях.
    """
    resized = _resize_to_max_width(img, max_width, resample)
    buf = io.BytesIO()
    resized.save(buf, format="WEBP", quality=quality, method=4)
    buf.seek(0)
    return buf.getvalue(), resized.width, resized.height


def _unique_storage_rel_path(item_id, suffix, original_name, sample_bytes):
    """Путь в storage; nonce уникален при параллельной обработке."""
    h = hashlib.sha256(sample_bytes[:65536]).hexdigest()[:12]
    base = "img"
    if original_name:
        base = (Path(str(original_name)).stem[:30] or "img").replace(" ", "_")
    ts = int(time.time() * 1000)
    nonce = secrets.token_hex(4)
    return f"items/{item_id}/{suffix}/{base}_{h}_{ts}_{nonce}.webp"


def process_image_bytes(raw: bytes, content_type: str, original_name: str, item_id):
    """
    То же, что process_image, но из байтов (удобно для фоновых потоков).
    """
    _validate_bytes(raw, content_type)
    buf = io.BytesIO(raw)
    img = _open_image(buf)
    sample = raw

    large_data, large_w, large_h = _save_webp(
        img, SIZE_LARGE, resample=Image.Resampling.LANCZOS
    )
    large_path = _unique_storage_rel_path(item_id, "large", original_name, sample)
    large_file = ContentFile(large_data, name=large_path)

    medium_data, medium_w, _ = _save_webp(
        img, SIZE_MEDIUM, quality=WEBP_QUALITY_PREVIEW, resample=Image.Resampling.BILINEAR
    )
    medium_path = _unique_storage_rel_path(item_id, "medium", original_name, sample)
    medium_file = ContentFile(medium_data, name=medium_path)

    feed_data, feed_w, _ = _save_webp(
        img, SIZE_FEED, quality=WEBP_QUALITY_PREVIEW, resample=Image.Resampling.BILINEAR
    )
    feed_path = _unique_storage_rel_path(item_id, "feed", original_name, sample)
    feed_file = ContentFile(feed_data, name=feed_path)

    thumb_data, thumb_w, thumb_h = _save_webp(
        img, SIZE_THUMBNAIL, quality=WEBP_QUALITY_PREVIEW, resample=Image.Resampling.BILINEAR
    )
    thumb_path = _unique_storage_rel_path(item_id, "thumbnails", original_name, sample)
    thumb_file = ContentFile(thumb_data, name=thumb_path)

    return {
        "image": large_file,
        "image_thumbnail": thumb_file,
        "image_medium": medium_file,
        "image_feed": feed_file,
        "width": large_w,
        "height": large_h,
        "thumbnail_width": thumb_w,
        "thumbnail_height": thumb_h,
        "medium_width": medium_w,
        "feed_width": feed_w,
    }


def process_image(ufile, item_id):
    """
    Обрабатывает загруженное изображение:
    1. Проверяет MIME и размер
    2. Генерирует thumbnail, medium, feed, large в WebP
    3. Удаляет оригинал после успешной конвертации (если временный файл)
    """
    _validate_file(ufile)
    ufile.seek(0)
    raw = ufile.read()
    ct = _get_content_type(ufile)
    name = getattr(ufile, "name", "") or "upload"
    result = process_image_bytes(raw, ct, name, item_id)

    try:
        if hasattr(ufile, "temporary_file_path"):
            tmp_path = ufile.temporary_file_path()
            if tmp_path and os.path.isfile(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    logger.warning("Could not remove temp file %s", tmp_path)
    except Exception:
        pass

    return result


def process_uploaded_files_parallel(uploaded_files, item_id, max_workers=IMAGE_PROCESS_MAX_WORKERS):
    """
    Читает файлы в текущем потоке, декодирование/WEBP — в пуле (ускоряет пост с 2–10 фото).
    Возвращает список dict | None той же длины и порядка, что и uploaded_files.
    """
    bundles = []
    for f in uploaded_files:
        f.seek(0)
        raw = f.read()
        ct = (getattr(f, "content_type", None) or "").lower().strip()
        name = getattr(f, "name", "") or "image.bin"
        bundles.append((raw, ct, name))

    if not bundles:
        return []

    def _one(bundle):
        raw, ct, name = bundle
        try:
            return process_image_bytes(raw, ct, name, item_id)
        except Exception as e:
            logger.exception("Image processing failed for item %s: %s", item_id, e)
            return None

    n = len(bundles)
    workers = max(1, min(max_workers, n))
    if n == 1:
        return [_one(bundles[0])]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_one, bundles))


def process_variants_from_bytes(raw: bytes, item_id, original_name: str = "image.webp"):
    """
    Regenerate thumbnail, medium, and feed WebP variants from an existing large image (bytes).
    Does not replace the large/master file.
    """
    buf = io.BytesIO(raw)
    img = _open_image(buf)
    sample = raw[:65536] if len(raw) > 65536 else raw

    medium_data, medium_w, _ = _save_webp(
        img, SIZE_MEDIUM, quality=WEBP_QUALITY_PREVIEW, resample=Image.Resampling.BILINEAR
    )
    medium_path = _unique_storage_rel_path(item_id, "medium", original_name, sample)
    medium_file = ContentFile(medium_data, name=medium_path)

    feed_data, feed_w, _ = _save_webp(
        img, SIZE_FEED, quality=WEBP_QUALITY_PREVIEW, resample=Image.Resampling.BILINEAR
    )
    feed_path = _unique_storage_rel_path(item_id, "feed", original_name, sample)
    feed_file = ContentFile(feed_data, name=feed_path)

    thumb_data, thumb_w, thumb_h = _save_webp(
        img, SIZE_THUMBNAIL, quality=WEBP_QUALITY_PREVIEW, resample=Image.Resampling.BILINEAR
    )
    thumb_path = _unique_storage_rel_path(item_id, "thumbnails", original_name, sample)
    thumb_file = ContentFile(thumb_data, name=thumb_path)

    return {
        "image_thumbnail": thumb_file,
        "image_medium": medium_file,
        "image_feed": feed_file,
        "thumbnail_width": thumb_w,
        "thumbnail_height": thumb_h,
        "medium_width": medium_w,
        "feed_width": feed_w,
    }


def _delete_item_image_variant_fields(item_image, field_names):
    for fn in field_names:
        try:
            field = getattr(item_image, fn, None)
            if field and getattr(field, "name", None):
                field.delete(save=False)
        except Exception:
            logger.exception("Failed to delete %s for ItemImage %s", fn, getattr(item_image, "pk", None))


def regenerate_item_image_variants(item_image, *, save=True):
    """
    Rebuild thumbnail / medium / feed from the stored large image.
    Returns True on success, False if there is no source image or processing failed.
    """
    if not item_image.image or not getattr(item_image.image, "name", None):
        return False
    try:
        with item_image.image.open("rb") as fh:
            raw = fh.read()
    except Exception:
        logger.exception("Could not read large image for ItemImage %s", item_image.pk)
        return False
    if not raw:
        return False

    original_name = Path(item_image.image.name).name or "image.webp"
    try:
        processed = process_variants_from_bytes(raw, item_image.item_id, original_name)
    except Exception:
        logger.exception("Variant regeneration failed for ItemImage %s", item_image.pk)
        return False

    _delete_item_image_variant_fields(
        item_image, ("image_thumbnail", "image_medium", "image_feed")
    )
    item_image.image_thumbnail = processed["image_thumbnail"]
    item_image.image_medium = processed["image_medium"]
    item_image.image_feed = processed["image_feed"]
    if save:
        item_image.save(
            update_fields=["image_thumbnail", "image_medium", "image_feed"]
        )
    return True


def process_image_legacy_safe(ufile, item_id):
    """Обрабатывает изображение. При ошибке возвращает None (fallback на сохранение без обработки)."""
    try:
        return process_image(ufile, item_id)
    except Exception as e:
        logger.exception("Image processing failed for item %s: %s", item_id, e)
        return None
