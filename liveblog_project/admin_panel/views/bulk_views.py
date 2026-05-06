"""Bulk delete views for admin tables."""
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.utils import timezone

from admin_panel.decorators import admin_required, superuser_required

User = get_user_model()


def _redirect_with_qs(url_name, request, **kwargs):
    url = reverse(f'admin_panel:{url_name}', kwargs=kwargs)
    qs = request.GET.urlencode()
    if qs:
        url += '?' + qs
    return redirect(url)


def _get_ids(request):
    ids = request.POST.getlist('ids')
    if not ids:
        raw = request.POST.get('ids', '').strip()
        ids = [x.strip() for x in raw.split(',') if x.strip()]
    return ids


@admin_required
def posts_bulk_delete(request):
    """Bulk delete posts. POST ids=1,2,3 (pks)."""
    if request.method != 'POST':
        return redirect('admin_panel:posts_list')
    from smart_blog.models import Item
    ids = _get_ids(request)
    deleted = 0
    for pk_str in ids:
        try:
            pk_int = int(pk_str)
            item = Item.objects.filter(pk=pk_int).first()
            if item:
                item.deleted_at = timezone.now()
                item.is_published = False
                item.save(update_fields=["deleted_at", "is_published"])
                deleted += 1
        except (ValueError, TypeError):
            pass
    if deleted:
        messages.success(request, f"{deleted} post(s) moved to Recent deleted.")
    return _redirect_with_qs('posts_list', request)


@admin_required
def comments_bulk_delete(request):
    """Bulk delete comments. POST ids=1,2,3."""
    if request.method != 'POST':
        return redirect('admin_panel:comments_list')
    from smart_blog.models import Comment
    ids = _get_ids(request)
    deleted = 0
    for pk in ids:
        try:
            pk_int = int(pk)
            comment = Comment.objects.filter(pk=pk_int).first()
            if comment:
                comment.deleted_at = timezone.now()
                comment.save(update_fields=["deleted_at"])
                deleted += 1
        except (ValueError, TypeError):
            pass
    if deleted:
        messages.success(request, f"{deleted} comment(s) moved to Recent deleted.")
    return _redirect_with_qs('comments_list', request)


@admin_required
def users_bulk_delete(request):
    """Bulk move users to Deleted queue (deactivate, keep rows)."""
    if request.method != 'POST':
        return redirect('admin_panel:users_list')
    ids = _get_ids(request)
    deleted = 0
    for pk in ids:
        try:
            pk_int = int(pk)
            user = User.objects.filter(pk=pk_int).first()
            if user and not user.is_staff and not user.is_superuser and user != request.user:
                from admin_panel.models import DeletedUserLog

                DeletedUserLog.objects.update_or_create(
                    user=user,
                    defaults={
                        "username": user.username,
                        "deleted_by": request.user,
                    },
                )
                user.is_active = False
                user.save(update_fields=["is_active"])
                deleted += 1
        except (ValueError, TypeError):
            pass
    if deleted:
        messages.success(request, f"{deleted} user(s) moved to Deleted.")
    return _redirect_with_qs('users_list', request)


@admin_required
def banned_users_bulk_unban(request):
    """Bulk unban users (set is_active=True)."""
    if request.method != 'POST':
        return redirect('admin_panel:banned_users')
    ids = _get_ids(request)
    unbanned = 0
    for pk in ids:
        try:
            pk_int = int(pk)
            user = User.objects.filter(pk=pk_int, is_active=False).first()
            if user:
                user.is_active = True
                user.save()
                unbanned += 1
        except (ValueError, TypeError):
            pass
    if unbanned:
        messages.success(request, f'{unbanned} user(s) unbanned.')
    url = reverse('admin_panel:banned_users')
    qs = request.GET.urlencode()
    if qs:
        url += '?' + qs
    return redirect(url)


@admin_required
def banned_users_bulk_delete(request):
    """Bulk move banned users to Deleted queue (same soft path as users list)."""
    if request.method != 'POST':
        return redirect('admin_panel:banned_users')
    ids = _get_ids(request)
    deleted = 0
    for pk in ids:
        try:
            pk_int = int(pk)
            user = User.objects.filter(pk=pk_int).first()
            if user and not user.is_staff and not user.is_superuser and user != request.user:
                from admin_panel.models import DeletedUserLog

                DeletedUserLog.objects.update_or_create(
                    user=user,
                    defaults={
                        "username": user.username,
                        "deleted_by": request.user,
                    },
                )
                user.is_active = False
                user.save(update_fields=["is_active"])
                deleted += 1
        except (ValueError, TypeError):
            pass
    if deleted:
        messages.success(request, f"{deleted} user(s) moved to Deleted.")
    return _redirect_with_qs('banned_users', request)


@admin_required
def deleted_logs_bulk_delete(request):
    """Legacy: permanently remove selected DeletedUserLog rows (no User rows)."""
    if request.method != 'POST':
        return redirect('admin_panel:recently_deleted')
    ids = _get_ids(request)
    valid_ids = []
    for x in ids:
        try:
            valid_ids.append(int(x))
        except (ValueError, TypeError):
            pass
    from admin_panel.models import DeletedUserLog

    removed = 0
    for log in DeletedUserLog.objects.filter(pk__in=valid_ids):
        if log.user_id is None:
            log.delete()
            removed += 1
    if removed:
        messages.success(request, f"Removed {removed} legacy log record(s).")
    url = reverse('admin_panel:recently_deleted')
    qs = request.GET.urlencode()
    if qs:
        url += '?' + qs
    return redirect(url)


@admin_required
def users_bulk_ban(request):
    """Bulk ban users (set is_active=False). Skips staff, superuser, self."""
    if request.method != 'POST':
        return redirect('admin_panel:users_list')
    ids = _get_ids(request)
    banned = 0
    for pk in ids:
        try:
            pk_int = int(pk)
            user = User.objects.filter(pk=pk_int).first()
            if user and not user.is_staff and not user.is_superuser and user != request.user and user.is_active:
                user.is_active = False
                user.save()
                banned += 1
        except (ValueError, TypeError):
            pass
    if banned:
        messages.success(request, f'{banned} user(s) banned.')
    qs = request.GET.copy()
    qs['status'] = 'active'
    return redirect(reverse('admin_panel:users_list') + '?' + qs.urlencode())


@admin_required
def tags_bulk_delete(request):
    """Bulk delete tags. POST ids=1,2,3."""
    if request.method != 'POST':
        return redirect('admin_panel:tags_list')
    from smart_blog.models import Tag
    ids = _get_ids(request)
    deleted = 0
    for pk in ids:
        try:
            pk_int = int(pk)
            tag = Tag.objects.filter(pk=pk_int).first()
            if tag:
                tag.soft_delete()
                deleted += 1
        except (ValueError, TypeError):
            pass
    if deleted:
        messages.success(request, f"{deleted} tag(s) moved to Recent deleted.")
    return _redirect_with_qs('tags_list', request)


@admin_required
def categories_bulk_delete(request):
    """Bulk delete categories. POST ids=1,2,3."""
    if request.method != 'POST':
        return redirect('admin_panel:categories_list')
    from smart_blog.models import Category
    ids = _get_ids(request)
    deleted = 0
    for pk in ids:
        try:
            pk_int = int(pk)
            cat = Category.objects.filter(pk=pk_int).first()
            if cat:
                cat.soft_delete()
                deleted += 1
        except (ValueError, TypeError):
            pass
    if deleted:
        messages.success(request, f"{deleted} categor(y/ies) moved to Recent deleted.")
    return _redirect_with_qs('categories_list', request)


@admin_required
def reports_bulk_clear(request):
    """Bulk clear: hide reports from admin list (admin_hidden=True), do NOT delete. Records stay for "Already reported". POST ids=1,2,3."""
    if request.method != 'POST':
        return redirect('admin_panel:reports_list')
    from smart_blog.models import ContentReport
    ids = _get_ids(request)
    cleared = 0
    for pk in ids:
        try:
            pk_int = int(pk)
            report = ContentReport.objects.filter(pk=pk_int).first()
            if report:
                report.admin_hidden = True
                report.save(update_fields=['admin_hidden'])
                cleared += 1
        except (ValueError, TypeError):
            pass
    if cleared:
        messages.success(request, f'{cleared} report(s) cleared.')
    return _redirect_with_qs('reports_list', request)


@admin_required
def reports_bulk_delete(request):
    """Bulk delete reported content (item or comment). POST ids=1,2,3."""
    if request.method != 'POST':
        return redirect('admin_panel:reports_list')
    from smart_blog.models import ContentReport
    ids = _get_ids(request)
    deleted = 0
    for pk in ids:
        try:
            pk_int = int(pk)
            report = ContentReport.objects.filter(pk=pk_int).first()
            if report:
                if report.item:
                    report.item.delete()
                    deleted += 1
                elif report.comment:
                    report.comment.delete()
                    deleted += 1
        except (ValueError, TypeError):
            pass
    if deleted:
        messages.success(request, f'{deleted} content item(s) deleted.')
    return _redirect_with_qs('reports_list', request)


@admin_required
def faq_bulk_delete(request):
    """Bulk delete FAQ items. POST ids=1,2,3."""
    if request.method != 'POST':
        return redirect('admin_panel:faq_list')
    from pages.models import FAQItem
    ids = _get_ids(request)
    deleted = 0
    for pk in ids:
        try:
            pk_int = int(pk)
            item = FAQItem.objects.filter(pk=pk_int).first()
            if item:
                item.delete()
                deleted += 1
        except (ValueError, TypeError):
            pass
    if deleted:
        messages.success(request, f'{deleted} FAQ item(s) deleted.')
    return _redirect_with_qs('faq_list', request)


@admin_required
@superuser_required
def backups_bulk_delete(request):
    """Bulk delete backups. Superuser only. POST ids=1,2,3."""
    if request.method != 'POST':
        return redirect('admin_panel:backups_list')
    from backups.models import Backup

    ids = _get_ids(request)
    deleted = 0
    for pk in ids:
        try:
            pk_int = int(pk)
            backup = Backup.objects.filter(pk=pk_int).first()
            if backup:
                backup.deleted_at = timezone.now()
                backup.save(update_fields=["deleted_at"])
                deleted += 1
        except (ValueError, TypeError):
            pass
    if deleted:
        messages.success(request, f"{deleted} backup(s) moved to Recent deleted.")
    return _redirect_with_qs('backups_list', request)
