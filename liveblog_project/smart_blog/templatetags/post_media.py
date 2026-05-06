"""Reusable post media context: photo/video pinned links + JSON payloads."""
from __future__ import annotations

from typing import Any, Dict, List

from django import template

register = template.Library()


def _slides_payload(images) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for im in images:
        alt = (im.alt_text or "").strip()
        out.append(
            {
                "full": im.get_url(),
                "thumb": im.get_thumbnail_url(),
                "srcset": im.get_srcset() or "",
                "alt": alt,
                "caption": (im.caption or "").strip(),
                "w": im.width,
                "h": im.height,
                "o": im.orientation_kind or "landscape",
            }
        )
    return out


def _video_payload(videos) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for v in videos:
        entry: Dict[str, Any] = {
            "src": v.get_url(),
            "caption": (v.caption or "").strip(),
        }
        qualities = v.get_quality_sources()
        if qualities:
            entry["qualities"] = qualities
        out.append(entry)
    return out


@register.inclusion_tag("smart_blog/includes/post_media_gallery.html")
def post_media_gallery(item):
    """Pinned photos/videos links + JSON payloads for lightbox/video viewer."""
    images = list(item.images.all())
    videos = list(item.videos.all()) if hasattr(item, 'videos') else []

    n_images = len(images)
    n_videos = len(videos)
    has_pin_file = bool(getattr(item, "body_pin_original", None))

    if n_images == 0 and n_videos == 0 and not has_pin_file:
        return {"show": False}

    slides = _slides_payload(images) if n_images else []
    video_slides = _video_payload(videos) if n_videos else []

    return {
        "show": True,
        "item": item,
        "slides": slides,
        "video_slides": video_slides,
        "image_count": n_images,
        "video_count": n_videos,
        "has_pin_file": has_pin_file,
        "script_id": f"post-media-json-{item.pk}",
        "video_script_id": f"post-video-json-{item.pk}",
    }
