"""User management views."""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth import get_user_model

from admin_panel.decorators import admin_required, superuser_required
from admin_panel.models import DeletedUserLog
from smart_blog.models import Item, Comment

User = get_user_model()


@admin_required
def users_list(request):
    """List users with search, pagination."""
    qs = User.objects.select_related('profile').annotate(
        posts_count=Count('items', distinct=True),
        comments_count=Count('comments', distinct=True),
    )
    qs = qs.order_by('-date_joined')

    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(
            Q(username__icontains=search) | Q(email__icontains=search)
        )

    status = request.GET.get('status')
    if status == 'banned':
        qs = qs.filter(is_active=False)
    else:
        qs = qs.filter(is_active=True)

    paginator = Paginator(qs, 30)
    page = request.GET.get('page', 1)
    users = paginator.get_page(page)

    context = {'users': users, 'search': search, 'current_status': status}
    return render(request, 'admin/users/users_list.html', context)


@admin_required
def banned_users_list(request):
    """List banned users only (inactive, not in Deleted queue). Search + bulk Unban."""
    qs = (
        User.objects.filter(is_active=False, deleted_queue_entry__isnull=True)
        .select_related("profile", "deleted_queue_entry")
        .annotate(
            posts_count=Count("items", distinct=True),
            comments_count=Count("comments", distinct=True),
        )
        .order_by("-date_joined")
    )

    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(
            Q(username__icontains=search) | Q(email__icontains=search)
        )

    paginator = Paginator(qs, 30)
    page = request.GET.get('page', 1)
    users = paginator.get_page(page)
    return render(request, 'admin/users/banned_users_list.html', {'users': users, 'search': search})


@admin_required
def user_profile(request, pk):
    """View user profile (admin detail)."""
    user = get_object_or_404(User.objects.select_related('profile'), pk=pk)
    posts = (
        Item.objects.filter(author=user, is_published=True)
        .select_related("category")
        .order_by("-published_date")[:10]
    )
    comments = (
        Comment.objects.filter(author=user, item__is_published=True, is_draft=False)
        .select_related("item")
        .order_by("-created")[:10]
    )
    context = {'user_obj': user, 'posts': posts, 'comments': comments}
    return render(request, 'admin/users/user_profile.html', context)


@admin_required
def user_ban(request, pk):
    """Ban user (set is_active=False)."""
    user = get_object_or_404(User, pk=pk)
    if user.is_staff:
        messages.error(request, 'Cannot ban admin users.')
        url = reverse('admin_panel:users_list')
        qs = request.GET.urlencode()
        if qs:
            url += '?' + qs
        return redirect(url)
    if request.method == 'POST':
        if user == request.user:
            messages.error(request, 'You cannot ban yourself.')
        elif user.is_superuser:
            messages.error(request, 'Cannot ban superuser.')
        else:
            user.is_active = False
            user.save()
            messages.success(request, f'User {user.username} has been banned.')
        url = reverse('admin_panel:users_list')
        qs = request.GET.copy()
        qs['status'] = 'active'
        return redirect(url + '?' + qs.urlencode())
    return render(request, 'admin/users/user_confirm_ban.html', {'user_obj': user})


@admin_required
def user_unban(request, pk):
    """Unban user (set is_active=True)."""
    user = get_object_or_404(User, pk=pk)
    if user.is_staff:
        messages.error(request, 'Cannot unban admin users.')
        url = reverse('admin_panel:banned_users') if request.GET.get('from') == 'banned' else reverse('admin_panel:users_list')
        qs = request.GET.copy()
        qs.pop('from', None)
        qs = qs.urlencode()
        if qs:
            url += '?' + qs
        return redirect(url)
    if request.method == 'POST':
        user.is_active = True
        user.save()
        messages.success(request, f'User {user.username} has been unbanned.')
        if request.GET.get('from') == 'banned':
            url = reverse('admin_panel:banned_users')
            qs = request.GET.copy()
            qs.pop('from', None)
            qs = qs.urlencode()
            if qs:
                url += '?' + qs
            return redirect(url)
        url = reverse('admin_panel:users_list')
        qs = request.GET.copy()
        qs.pop('from', None)
        qs['status'] = 'active'
        return redirect(url + '?' + qs.urlencode())
    from_banned = request.GET.get('from') == 'banned'
    qs = request.GET.copy()
    qs.pop('from', None)
    qs = qs.urlencode()
    if from_banned:
        cancel_url = reverse('admin_panel:banned_users') + ('?' + qs if qs else '')
    else:
        cancel_url = reverse('admin_panel:users_list') + ('?' + qs if qs else '')
    return render(request, 'admin/users/user_confirm_unban.html', {
        'user_obj': user,
        'cancel_url': cancel_url,
    })


@admin_required
def user_delete(request, pk):
    """Move user to Deleted queue (deactivate, keep DB row)."""
    user = get_object_or_404(User, pk=pk)
    if user.is_staff:
        messages.error(request, 'Cannot delete admin users.')
        url = reverse('admin_panel:users_list')
        qs = request.GET.urlencode()
        if qs:
            url += '?' + qs
        return redirect(url)
    if request.method == 'POST':
        if user == request.user:
            messages.error(request, 'You cannot delete yourself.')
        elif user.is_superuser:
            messages.error(request, 'Cannot delete superuser.')
        else:
            username = user.username
            DeletedUserLog.objects.update_or_create(
                user=user,
                defaults={
                    'username': username,
                    'deleted_by': request.user,
                },
            )
            user.is_active = False
            user.save(update_fields=['is_active'])
            messages.success(request, f'User {username} moved to Deleted.')
        url = reverse('admin_panel:users_list')
        qs = request.GET.urlencode()
        if qs:
            url += '?' + qs
        return redirect(url)
    return render(request, 'admin/users/user_confirm_delete.html', {'user_obj': user})


@admin_required
def recently_deleted_list(request):
    """Deleted queue: recover or purge user accounts."""
    qs = DeletedUserLog.objects.select_related('deleted_by', 'user').order_by('-deleted_at')

    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(username__icontains=search)

    paginator = Paginator(qs, 30)
    page = request.GET.get('page', 1)
    logs = paginator.get_page(page)
    return render(request, 'admin/users/recently_deleted_list.html', {
        'logs': logs,
        'search': search,
    })


@admin_required
def deleted_users_recover(request):
    if request.method != 'POST':
        return redirect('admin_panel:recently_deleted')
    ids = []
    for x in request.POST.getlist('ids'):
        try:
            ids.append(int(x))
        except (ValueError, TypeError):
            pass
    recovered = 0
    for log in DeletedUserLog.objects.filter(pk__in=ids).select_related('user'):
        if log.user_id:
            u = log.user
            log.delete()
            u.is_active = True
            u.save(update_fields=['is_active'])
            recovered += 1
    if recovered:
        messages.success(request, f'Recovered {recovered} user(s).')
    url = reverse('admin_panel:recently_deleted')
    qs = request.GET.urlencode()
    if qs:
        url += '?' + qs
    return redirect(url)


@admin_required
@superuser_required
def deleted_users_permanent_delete(request):
    if request.method != 'POST':
        return redirect('admin_panel:recently_deleted')
    ids = []
    for x in request.POST.getlist('ids'):
        try:
            ids.append(int(x))
        except (ValueError, TypeError):
            pass
    purged = 0
    for log in DeletedUserLog.objects.filter(pk__in=ids).select_related('user'):
        u = log.user
        if u:
            if u.is_staff or u.is_superuser or u == request.user:
                continue
            u.delete()
            purged += 1
        else:
            log.delete()
            purged += 1
    if purged:
        messages.success(request, f'Permanently removed {purged} record(s).')
    url = reverse('admin_panel:recently_deleted')
    qs = request.GET.urlencode()
    if qs:
        url += '?' + qs
    return redirect(url)
