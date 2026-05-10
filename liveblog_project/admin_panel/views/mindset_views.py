"""Admin: Mindset (themes + replies) moderation views.

The list view shows both Theme and Reply rows in one paginated table; the
``filter`` query param chooses what is included:

* ``all`` (default): themes + replies, newest first;
* ``root``: themes only;
* ``replies``: replies only.

Each row has author, a preview anchor link to the public page, publication
date, the first hashtag (themes use the M2M; replies parse it from the body),
and a single Delete button which opens a confirmation modal (no Actions
dropdown). Bulk delete works the same way as on Comments / Posts and supports
both kinds at once.
"""
from __future__ import annotations

from itertools import chain

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from admin_panel.decorators import admin_required
from admin_panel.views.bulk_views import _get_ids
from mindset.models import Reply, Theme

PREVIEW_MAX = 60


def _truncate_preview(text: str) -> str:
    """Annotation up to 60 characters used as the visible link label."""
    cleaned = (text or "").strip()
    if not cleaned:
        return "(empty)"
    if len(cleaned) <= PREVIEW_MAX:
        return cleaned
    return cleaned[:PREVIEW_MAX].rstrip() + "…"


def _reply_plain_text(reply: Reply) -> str:
    """Mindset replies store sanitised HTML; strip tags for the preview."""
    from mindset.body_html import html_to_plain_text

    return html_to_plain_text(reply.body or "")


def _first_reply_hashtag(reply: Reply) -> dict | None:
    """Return ``{'name', 'slug'}`` for the first ``#tag`` in the reply body or
    ``None``. Replies don't M2M-attach to ``Hashtag`` so we parse it from the
    body — same regex used to render the public hashtag links, so what the
    user clicks in the table matches what the public page links to.
    """
    from mindset.body_html import (
        extract_hashtags,
        html_to_plain_text,
        normalise_hashtags,
    )

    plain = html_to_plain_text(reply.body or "")
    pairs = normalise_hashtags(extract_hashtags(plain))
    if not pairs:
        return None
    name, slug = pairs[0]
    return {"name": name, "slug": slug}


def _theme_row(theme: Theme) -> dict:
    first_tag = theme.hashtags.all().first() if theme.pk else None
    return {
        "kind": "theme",
        "row_id": f"theme-{theme.pk}",
        "pk": theme.pk,
        "author": theme.author,
        "preview": _truncate_preview(theme.body_text or ""),
        "url": reverse("mindset:theme_detail", kwargs={"pk": theme.pk}),
        "created": theme.created_at,
        "hashtag": first_tag,
        "delete_url": reverse("admin_panel:mindset_theme_delete", args=[theme.pk]),
    }


def _reply_row(reply: Reply) -> dict:
    return {
        "kind": "reply",
        "row_id": f"reply-{reply.pk}",
        "pk": reply.pk,
        "author": reply.author,
        "preview": _truncate_preview(_reply_plain_text(reply)),
        "url": (
            reverse("mindset:theme_detail", kwargs={"pk": reply.theme_id})
            + f"#mindset-reply-{reply.pk}"
        ),
        "created": reply.created_at,
        "hashtag": _first_reply_hashtag(reply),
        "delete_url": reverse("admin_panel:mindset_reply_delete", args=[reply.pk]),
    }


@admin_required
def mindset_list(request):
    """Themes + replies admin table with search / filter / bulk delete."""
    search = (request.GET.get("q") or "").strip()
    filter_type = (request.GET.get("filter") or "all").strip().lower()
    if filter_type not in ("all", "root", "replies"):
        filter_type = "all"

    themes_qs = (
        Theme.objects.filter(is_deleted=False)
        .select_related("author")
        .prefetch_related("hashtags")
        .order_by("-created_at")
    )
    replies_qs = (
        Reply.objects.filter(is_deleted=False)
        .select_related("author", "theme")
        .order_by("-created_at")
    )

    if search:
        themes_qs = themes_qs.filter(
            Q(body_text__icontains=search)
            | Q(body__icontains=search)
            | Q(author__username__icontains=search)
            | Q(hashtags__name__icontains=search)
        ).distinct()
        replies_qs = replies_qs.filter(
            Q(body__icontains=search) | Q(author__username__icontains=search)
        )

    rows: list[dict] = []
    if filter_type == "root":
        rows = [_theme_row(t) for t in themes_qs]
    elif filter_type == "replies":
        rows = [_reply_row(r) for r in replies_qs]
    else:
        merged = sorted(
            chain(themes_qs, replies_qs),
            key=lambda obj: obj.created_at,
            reverse=True,
        )
        for obj in merged:
            rows.append(_theme_row(obj) if isinstance(obj, Theme) else _reply_row(obj))

    paginator = Paginator(rows, 30)
    page = paginator.get_page(request.GET.get("page", 1))

    context = {
        "rows_page": page,
        "search": search,
        "filter_type": filter_type,
    }
    return render(request, "admin/mindset/mindset_list.html", context)


def _redirect_back(request):
    url = reverse("admin_panel:mindset_list")
    qs = request.GET.urlencode()
    if qs:
        url += "?" + qs
    return redirect(url)


@admin_required
def mindset_theme_delete(request, pk):
    theme = get_object_or_404(Theme.objects.filter(is_deleted=False), pk=pk)
    if request.method == "POST":
        theme.delete()
        messages.success(request, "Theme deleted.")
        return _redirect_back(request)
    return render(
        request,
        "admin/mindset/mindset_confirm_delete.html",
        {
            "kind": "theme",
            "preview": _truncate_preview(theme.body_text or ""),
            "author": theme.author,
            "action_url": reverse("admin_panel:mindset_theme_delete", args=[theme.pk]),
        },
    )


@admin_required
def mindset_reply_delete(request, pk):
    reply = get_object_or_404(Reply.objects.filter(is_deleted=False), pk=pk)
    if request.method == "POST":
        reply.delete()
        messages.success(request, "Reply deleted.")
        return _redirect_back(request)
    return render(
        request,
        "admin/mindset/mindset_confirm_delete.html",
        {
            "kind": "reply",
            "preview": _truncate_preview(_reply_plain_text(reply)),
            "author": reply.author,
            "action_url": reverse("admin_panel:mindset_reply_delete", args=[reply.pk]),
        },
    )


@admin_required
def mindset_bulk_delete(request):
    """Bulk delete. Selected rows carry ``theme-<pk>`` / ``reply-<pk>`` ids."""
    if request.method != "POST":
        return redirect("admin_panel:mindset_list")
    raw_ids = _get_ids(request)
    deleted = 0
    for raw in raw_ids:
        kind, _, pk_str = str(raw).partition("-")
        try:
            pk = int(pk_str)
        except (TypeError, ValueError):
            continue
        if kind == "theme":
            obj = Theme.objects.filter(pk=pk, is_deleted=False).first()
        elif kind == "reply":
            obj = Reply.objects.filter(pk=pk, is_deleted=False).first()
        else:
            continue
        if obj is None:
            continue
        obj.delete()
        deleted += 1
    if deleted:
        messages.success(request, f"{deleted} mindset record(s) deleted.")
    return _redirect_back(request)
