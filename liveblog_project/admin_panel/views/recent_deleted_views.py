"""System: recently soft-deleted content (restore / purge)."""
from pathlib import Path

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from admin_panel.decorators import admin_required
from admin_panel.views.bulk_views import _get_ids
from backups.models import Backup
from smart_blog.models import Category, Comment, ContentReport, Item, Tag
from smart_blog.public_listing_cache import invalidate_public_listing_caches

TAB_POSTS = "posts"
TAB_COMMENTS = "comments"
TAB_TAGS = "tags"
TAB_CATEGORIES = "categories"
TAB_REPORTS = "reports"
TAB_BACKUPS = "backups"
TABS = (
    TAB_POSTS,
    TAB_COMMENTS,
    TAB_TAGS,
    TAB_CATEGORIES,
    TAB_REPORTS,
    TAB_BACKUPS,
)


def _redirect_recent_deleted(request, tab):
    return redirect(f"{reverse('admin_panel:recent_deleted_content')}?tab={tab}")


def _paginate(qs, request, per_page=30):
    paginator = Paginator(qs, per_page)
    return paginator.get_page(request.GET.get("page", 1))


@admin_required
def recent_deleted_content(request):
    tab = request.GET.get("tab", TAB_POSTS)
    if tab not in TABS:
        tab = TAB_POSTS

    partial = request.GET.get("partial") == "1"
    if tab == TAB_BACKUPS and not request.user.is_superuser:
        if partial:
            return HttpResponse(status=403)
        return redirect("admin_panel:dashboard")

    ctx = {"tab": tab, "tabs": TABS}
    if tab == TAB_POSTS:
        qs = Item.all_objects.filter(deleted_at__isnull=False).order_by("-deleted_at")
        ctx["rows"] = _paginate(qs, request)
    elif tab == TAB_COMMENTS:
        qs = Comment.all_objects.filter(deleted_at__isnull=False).select_related("item", "author").order_by(
            "-deleted_at"
        )
        ctx["rows"] = _paginate(qs, request)
    elif tab == TAB_TAGS:
        qs = Tag.all_objects.filter(deleted_at__isnull=False).order_by("-deleted_at")
        ctx["rows"] = _paginate(qs, request)
    elif tab == TAB_CATEGORIES:
        qs = Category.all_objects.filter(deleted_at__isnull=False).order_by("-deleted_at")
        ctx["rows"] = _paginate(qs, request)
    elif tab == TAB_REPORTS:
        qs = ContentReport.objects.filter(deleted_at__isnull=False).select_related(
            "item", "comment", "reporter"
        ).order_by("-deleted_at")
        ctx["rows"] = _paginate(qs, request)
    elif tab == TAB_BACKUPS:
        qs = Backup.all_objects.filter(deleted_at__isnull=False).order_by("-deleted_at")
        ctx["rows"] = _paginate(qs, request)

    if partial:
        return render(request, "admin/system/_recent_deleted_bucket.html", ctx)
    return render(request, "admin/system/recent_deleted.html", ctx)


@admin_required
def recent_deleted_restore(request):
    if request.method != "POST":
        return redirect("admin_panel:recent_deleted_content")
    kind = request.POST.get("kind", "")
    ids = _get_ids(request)
    if kind not in TABS or not ids:
        messages.error(request, "Nothing to recover.")
        return _redirect_recent_deleted(request, kind if kind in TABS else TAB_POSTS)
    n = 0
    try:
        id_ints = [int(x) for x in ids]
    except (ValueError, TypeError):
        id_ints = []
    if kind == TAB_POSTS:
        # Trash sets is_published=False; recovery must re-publish (Draft is only via Posts UI).
        n = Item.all_objects.filter(pk__in=id_ints, deleted_at__isnull=False).update(
            deleted_at=None, is_published=True
        )
    elif kind == TAB_COMMENTS:
        n = Comment.all_objects.filter(pk__in=id_ints, deleted_at__isnull=False).update(
            deleted_at=None, is_draft=False
        )
    elif kind == TAB_TAGS:
        tags_qs = Tag.all_objects.filter(pk__in=id_ints, deleted_at__isnull=False)
        for tag in tags_qs:
            through_ids = set(
                Item.tags.through.objects.filter(tag_id=tag.pk).values_list("item_id", flat=True)
            )
            snapshot_ids = set(tag.pending_restore_item_ids or [])
            item_ids = through_ids | snapshot_ids
            tag.deleted_at = None
            tag.pending_restore_item_ids = None
            tag.save(update_fields=["deleted_at", "pending_restore_item_ids"])
            n += 1
            for item_id in item_ids:
                item = Item.all_objects.filter(pk=item_id, deleted_at__isnull=True).first()
                if item:
                    item.tags.add(tag)
    elif kind == TAB_CATEGORIES:
        cats_qs = Category.all_objects.filter(pk__in=id_ints, deleted_at__isnull=False)
        for cat in cats_qs:
            snapshot_ids = set(cat.pending_restore_item_ids or [])
            cat.deleted_at = None
            cat.pending_restore_item_ids = None
            cat.save(update_fields=["deleted_at", "pending_restore_item_ids"])
            n += 1
            for item_id in snapshot_ids:
                item = Item.all_objects.filter(pk=item_id, deleted_at__isnull=True).first()
                if item:
                    item.category = cat
                    item.save(update_fields=["category"])
    elif kind == TAB_REPORTS:
        n = ContentReport.objects.filter(pk__in=id_ints, deleted_at__isnull=False).update(deleted_at=None)
    elif kind == TAB_BACKUPS:
        if not request.user.is_superuser:
            return redirect("admin_panel:dashboard")
        n = Backup.all_objects.filter(pk__in=id_ints, deleted_at__isnull=False).update(deleted_at=None)
    if n:
        messages.success(request, f"Recovered {n} record(s).")
        if kind == TAB_POSTS:
            # Bulk .update() bypasses model save signals; public caches must refresh immediately.
            invalidate_public_listing_caches(bump_home=True)
    else:
        messages.info(request, "No matching records to recover.")
    return _redirect_recent_deleted(request, kind)


@admin_required
def recent_deleted_purge(request):
    if request.method != "POST":
        return redirect("admin_panel:recent_deleted_content")
    kind = request.POST.get("kind", "")
    ids = _get_ids(request)
    if kind not in TABS or not ids:
        messages.error(request, "Nothing to purge.")
        return _redirect_recent_deleted(request, kind if kind in TABS else TAB_POSTS)
    try:
        id_ints = [int(x) for x in ids]
    except (ValueError, TypeError):
        id_ints = []
    n = 0
    if kind == TAB_POSTS:
        for obj in Item.all_objects.filter(pk__in=id_ints, deleted_at__isnull=False):
            obj.delete()
            n += 1
    elif kind == TAB_COMMENTS:
        for obj in Comment.all_objects.filter(pk__in=id_ints, deleted_at__isnull=False):
            obj.delete()
            n += 1
    elif kind == TAB_TAGS:
        for obj in Tag.all_objects.filter(pk__in=id_ints, deleted_at__isnull=False):
            obj.delete()
            n += 1
    elif kind == TAB_CATEGORIES:
        for obj in Category.all_objects.filter(pk__in=id_ints, deleted_at__isnull=False):
            obj.delete()
            n += 1
    elif kind == TAB_REPORTS:
        n, _ = ContentReport.objects.filter(pk__in=id_ints, deleted_at__isnull=False).delete()
    elif kind == TAB_BACKUPS:
        if not request.user.is_superuser:
            return redirect("admin_panel:dashboard")
        for backup in Backup.all_objects.filter(pk__in=id_ints, deleted_at__isnull=False):
            if backup.file_path and Path(backup.file_path).exists():
                try:
                    Path(backup.file_path).unlink()
                except OSError:
                    pass
            backup.delete()
            n += 1
    if n:
        messages.success(request, f"Permanently removed {n} record(s).")
    else:
        messages.info(request, "No matching records to purge.")
    return _redirect_recent_deleted(request, kind)
