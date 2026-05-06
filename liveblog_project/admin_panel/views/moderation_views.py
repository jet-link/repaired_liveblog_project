"""Content violations moderation views."""
from urllib.parse import urlencode
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from admin_panel.decorators import admin_required
from admin_panel.models import ContentViolation
from smart_blog.models import Item, Comment
from smart_blog.public_listing_cache import invalidate_public_listing_caches


def _attach_resolved_targets(violations):
    """
    FK `v.item` / `v.comment` use default managers which hide soft-deleted rows,
    so attach `resolved_item` / `resolved_comment` from all_objects for the template.
    """
    item_ids = {v.item_id for v in violations if v.item_id}
    comment_ids = {v.comment_id for v in violations if v.comment_id}
    items_map = {}
    if item_ids:
        items_map = {
            it.pk: it
            for it in Item.all_objects.filter(pk__in=item_ids).select_related('author')
        }
    comments_map = {}
    if comment_ids:
        comments_map = {
            c.pk: c
            for c in Comment.all_objects.filter(pk__in=comment_ids).select_related('author', 'item')
        }
    for v in violations:
        v.resolved_item = items_map.get(v.item_id) if v.item_id else None
        v.resolved_comment = comments_map.get(v.comment_id) if v.comment_id else None


def _schedule_trust_recalc(user_or_id):
    """Recompute user's trust score on commit; accepts user pk or instance."""
    if not user_or_id:
        return
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if hasattr(user_or_id, 'pk'):
        user = user_or_id
    else:
        user = User.objects.filter(pk=int(user_or_id)).first()
    if not user:
        return

    def _recalc():
        try:
            from admin_panel.services.trust_score_service import update_user_trust_score
            update_user_trust_score(user)
        except Exception:
            pass

    transaction.on_commit(_recalc)


@admin_required
@require_GET
def content_violations_list(request):
    """List content violations with search and filters."""
    if not request.user.is_superuser:
        return redirect('admin_panel:dashboard')

    qs = ContentViolation.objects.select_related(
        'item', 'comment', 'analysis_run',
        'item__author', 'comment__author',
    )

    # Search (author username, detected word, item title, comment text).
    # Use Item.all_objects / Comment.all_objects so soft-deleted posts/comments still match
    # (default managers would exclude them via FK joins and drop valid rows).
    search = request.GET.get('q', '').strip()
    if search:
        search_q = Q(detected_word__icontains=search)
        item_ids = list(
            Item.all_objects.filter(
                Q(title__icontains=search) | Q(author__username__icontains=search)
            ).values_list('pk', flat=True)
        )
        if item_ids:
            search_q |= Q(item_id__in=item_ids)
        comment_ids = list(
            Comment.all_objects.filter(
                Q(text__icontains=search) | Q(author__username__icontains=search)
            ).values_list('pk', flat=True)
        )
        if comment_ids:
            search_q |= Q(comment_id__in=comment_ids)
        qs = qs.filter(search_q)

    # Type filter
    content_type = request.GET.get('type')
    if content_type == 'post':
        qs = qs.filter(content_type=ContentViolation.TYPE_POST)
    elif content_type == 'comment':
        qs = qs.filter(content_type=ContentViolation.TYPE_COMMENT)

    # Status filter. "cleared" is a soft-hide bucket (server-side Clear action);
    # by default we exclude it from the list, but allow opt-in via ?status=cleared.
    status_filter = request.GET.get('status')
    if status_filter and status_filter in ('pending', 'checked', 'ignored', 'cleared'):
        qs = qs.filter(status=status_filter)
    else:
        qs = qs.exclude(status=ContentViolation.STATUS_CLEARED)

    # Analysis run filter
    analysis_id = request.GET.get('analysis_id')
    if analysis_id:
        try:
            qs = qs.filter(analysis_run_id=int(analysis_id))
        except (ValueError, TypeError):
            pass

    qs = qs.order_by('-created_at')
    paginator = Paginator(qs, 30)
    page = request.GET.get('page', 1)
    violations = paginator.get_page(page)
    _attach_resolved_targets(list(violations.object_list))

    filter_params = {}
    if search:
        filter_params['q'] = search
    if content_type:
        filter_params['type'] = content_type
    if status_filter:
        filter_params['status'] = status_filter
    if analysis_id:
        filter_params['analysis_id'] = analysis_id
    page_num = request.GET.get('page')
    if page_num:
        filter_params['page'] = page_num
    filter_qs = urlencode(filter_params) if filter_params else ''

    pagination_params = {k: v for k, v in filter_params.items() if k != 'page'}
    pagination_query = urlencode(pagination_params) if pagination_params else ''

    context = {
        'violations': violations,
        'search': search,
        'current_type': content_type,
        'current_status': status_filter,
        'analysis_id': analysis_id,
        'filter_qs': filter_qs,
        'pagination_query': pagination_query,
    }
    return render(request, 'admin/moderation/content_violations.html', context)


def _violation_author_id(v):
    """Resolve author id behind a violation (post or comment), tolerant to soft-delete."""
    if v.item_id:
        item = Item.all_objects.filter(pk=v.item_id).only('author_id').first()
        if item:
            return item.author_id
    if v.comment_id:
        comment = Comment.all_objects.filter(pk=v.comment_id).only('author_id').first()
        if comment:
            return comment.author_id
    return v.snapshot_author_id


@admin_required
@require_POST
def content_violation_check(request, pk):
    """Mark violation as checked. Checked = admin acquits author (no trust penalty)."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False}, status=403)
    v = get_object_or_404(ContentViolation, pk=pk)
    v.status = ContentViolation.STATUS_CHECKED
    v.save(update_fields=['status'])
    _schedule_trust_recalc(_violation_author_id(v))
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'new_status': v.status,
        })
    filter_qs = request.GET.urlencode()
    url = reverse('admin_panel:content_violations_list')
    if filter_qs:
        url += '?' + filter_qs
    return redirect(url)


@admin_required
@require_POST
def content_violation_ignore(request, pk):
    """Mark violation as ignored (still counts toward trust score)."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False}, status=403)
    v = get_object_or_404(ContentViolation, pk=pk)
    previous_status = v.status
    v.status = ContentViolation.STATUS_IGNORED
    v.save(update_fields=['status'])
    if previous_status == ContentViolation.STATUS_CHECKED:
        _schedule_trust_recalc(_violation_author_id(v))
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'new_status': v.status,
        })
    filter_qs = request.GET.urlencode()
    url = reverse('admin_panel:content_violations_list')
    if filter_qs:
        url += '?' + filter_qs
    return redirect(url)


@admin_required
@require_GET
def content_violation_confirm_delete(request, pk):
    """Show confirmation page before deleting violation (and soft-deleting content)."""
    if not request.user.is_superuser:
        return redirect('admin_panel:dashboard')
    v = get_object_or_404(ContentViolation, pk=pk)
    target_name = ''
    target_type = ''
    item = Item.all_objects.filter(pk=v.item_id).first() if v.item_id else None
    comment = Comment.all_objects.filter(pk=v.comment_id).first() if v.comment_id else None
    if item:
        target_name = item.title or '(no title)'
        target_type = 'post'
    elif comment:
        target_name = (comment.text or '')[:80]
        target_type = 'comment'
    else:
        target_name = v.target_preview or v.detected_word or 'orphan violation'
        target_type = v.content_type or 'violation'
    filter_qs = request.GET.urlencode()
    return render(request, 'admin/moderation/content_violation_confirm_delete.html', {
        'violation': v,
        'target_name': target_name,
        'target_type': target_type,
        'filter_qs': filter_qs,
    })


def _delete_violation_and_content(v):
    """Soft-delete the linked post/comment (if live) and permanently remove the violation row."""
    author_id = None
    post_was_deleted = False
    if v.item_id:
        item = Item.all_objects.filter(pk=v.item_id).first()
        if item and item.deleted_at is None:
            author_id = item.author_id
            item.deleted_at = timezone.now()
            item.is_published = False
            item.save(update_fields=['deleted_at', 'is_published'])
            post_was_deleted = True
    elif v.comment_id:
        comment = Comment.all_objects.filter(pk=v.comment_id).first()
        if comment and comment.deleted_at is None:
            author_id = comment.author_id
            comment.deleted_at = timezone.now()
            comment.save(update_fields=['deleted_at'])
    v.delete()
    return author_id, post_was_deleted


@admin_required
@require_POST
def content_violation_delete_content(request, pk):
    """Permanently delete violation + soft-delete linked post/comment."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False}, status=403)
    v = get_object_or_404(ContentViolation, pk=pk)
    author_id, post_was_deleted = _delete_violation_and_content(v)
    if post_was_deleted:
        invalidate_public_listing_caches(bump_home=True)
    _schedule_trust_recalc(author_id)
    messages.success(request, 'Violation removed.')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'removed': True})
    filter_qs = request.GET.urlencode()
    url = reverse('admin_panel:content_violations_list')
    if filter_qs:
        url += '?' + filter_qs
    return redirect(url)


@admin_required
@require_POST
def content_violations_bulk_delete_content(request):
    """Bulk permanently delete violations + soft-delete linked posts/comments."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False}, status=403)
    ids = request.POST.getlist('ids[]') or request.POST.getlist('ids')
    valid_ids = []
    for x in ids:
        try:
            valid_ids.append(int(x))
        except (ValueError, TypeError):
            pass
    if valid_ids:
        viols = list(ContentViolation.objects.filter(pk__in=valid_ids))
        authors_to_recalc = set()
        deleted_count = 0
        any_post_deleted = False
        for v in viols:
            author_id, post_was_deleted = _delete_violation_and_content(v)
            if author_id:
                authors_to_recalc.add(author_id)
            if post_was_deleted:
                any_post_deleted = True
            deleted_count += 1
        if any_post_deleted:
            invalidate_public_listing_caches(bump_home=True)
        for uid in authors_to_recalc:
            _schedule_trust_recalc(uid)
        messages.success(request, f'{deleted_count} violation(s) removed.')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    filter_qs = request.GET.urlencode()
    url = reverse('admin_panel:content_violations_list')
    if filter_qs:
        url += '?' + filter_qs
    return redirect(url)


@admin_required
@require_POST
def content_violations_bulk_clear(request):
    """Bulk soft-clear: mark violations as 'cleared' (hidden from default list, kept in DB).

    Cleared rows can later be reviewed via ?status=cleared. Linked content (posts/comments)
    is NOT touched, and trust score still reflects these violations until they are
    explicitly Checked or Deleted.
    """
    if not request.user.is_superuser:
        return JsonResponse({'success': False}, status=403)
    ids = request.POST.getlist('ids[]') or request.POST.getlist('ids')
    valid_ids = []
    for x in ids:
        try:
            valid_ids.append(int(x))
        except (ValueError, TypeError):
            pass
    cleared = 0
    if valid_ids:
        cleared = ContentViolation.objects.filter(pk__in=valid_ids).exclude(
            status=ContentViolation.STATUS_CLEARED
        ).update(status=ContentViolation.STATUS_CLEARED)
        if cleared:
            messages.success(request, f'{cleared} violation(s) cleared.')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'cleared': cleared})
    filter_qs = request.GET.urlencode()
    url = reverse('admin_panel:content_violations_list')
    if filter_qs:
        url += '?' + filter_qs
    return redirect(url)
