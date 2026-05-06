"""Post (Item) management views."""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone

from admin_panel.decorators import admin_required
from admin_panel.forms import ItemAdminEditForm, ItemAdminCreateForm
from smart_blog.models import Item, Category
from smart_blog.services.item_write import (
    MAX_ITEM_IMAGES,
    attach_item_images_from_uploads,
    delete_item_images_by_ids,
    merge_item_tags,
)
from smart_blog.video_utils import delete_item_videos_by_ids
from django.db import transaction

@admin_required
def posts_list(request):
    """List posts with search, filter, pagination."""
    qs = (
        Item.objects.select_related("author", "category")
        .annotate(
            comments_count=Count(
                "comments",
                filter=Q(comments__parent__isnull=True),
                distinct=True,
            )
        )
        .order_by("-published_date")
    )

    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(
            Q(title__icontains=search) | Q(text__icontains=search)
        )

    category_id = request.GET.get('category')
    if category_id:
        qs = qs.filter(category_id=category_id)

    status = request.GET.get('status')
    if status == 'published':
        qs = qs.filter(is_published=True)
    elif status == 'draft':
        qs = qs.filter(is_published=False)

    sort = request.GET.get('sort', 'date')
    if sort == 'views':
        qs = qs.order_by('-views_count')
    elif sort == 'likes':
        qs = qs.order_by('-likes_count')
    elif sort == 'comments':
        qs = qs.order_by('-comments_count')

    paginator = Paginator(qs, 30)
    page = request.GET.get('page', 1)
    posts = paginator.get_page(page)
    categories = Category.objects.only("id", "name", "slug").order_by("name")

    context = {
        'posts': posts,
        'categories': categories,
        'search': search,
        'current_category': category_id,
        'current_status': status,
        'current_sort': sort,
    }
    return render(request, 'admin/posts/posts_list.html', context)


@admin_required
def post_create(request):
    """Create new post."""
    selected_tag_ids = []
    if request.method == 'POST':
        form = ItemAdminCreateForm(request.POST, request.FILES)
        files = request.FILES.getlist('images')
        selected_tag_ids = [int(x) for x in request.POST.getlist('tags') if str(x).isdigit()]
        if form.is_valid():
            with transaction.atomic():
                item = form.save(commit=False)
                item.author = request.user
                item.save()
                item.tags.set(merge_item_tags(form.cleaned_data))
                file_list = [f for f in files[:MAX_ITEM_IMAGES] if f]
                attach_item_images_from_uploads(item, file_list)
            messages.success(request, 'Post created successfully.')
            return redirect('admin_panel:posts_list')
    else:
        form = ItemAdminCreateForm()
    return render(request, 'admin/posts/post_create.html', {'form': form, 'selected_tag_ids': selected_tag_ids})


@admin_required
def post_edit(request, pk):
    """Edit existing post."""
    item = get_object_or_404(
        Item.objects.select_related("author", "category"),
        pk=pk,
    )
    if request.method == 'POST':
        delete_ids = request.POST.getlist('delete_images')
        delete_video_ids = request.POST.getlist('delete_videos')
        form = ItemAdminEditForm(request.POST, instance=item)
        if form.is_valid():
            body_pin_clear = bool(form.cleaned_data.get('body_pin_clear'))
            with transaction.atomic():
                if delete_ids or delete_video_ids:
                    delete_item_images_by_ids(item, delete_ids)
                    delete_item_videos_by_ids(item, delete_video_ids)
                instance = form.save(commit=False)
                if body_pin_clear:
                    if instance.body_pin_original:
                        instance.body_pin_original.delete(save=False)
                    instance.body_pin_original = None
                    instance.body_pin_content_type = 'text'
                    instance.body_pin_content_html = ''
                    instance.body_pin_plain_snapshot = ''
                    instance.body_sourced_from_document = False
                if delete_ids or delete_video_ids or body_pin_clear:
                    instance.edited = True
                instance.save()
                form.save_m2m()
            messages.success(request, 'Post updated.')
            url = reverse('admin_panel:posts_list')
            qs = request.GET.urlencode()
            if qs:
                url += '?' + qs
            return redirect(url)
    else:
        form = ItemAdminEditForm(instance=item)
    return render(request, 'admin/posts/post_edit.html', {
        'form': form,
        'item': item,
        'existing_images': item.images.all(),
        'existing_videos': item.videos.all(),
    })


@admin_required
def post_delete(request, pk):
    """Delete post."""
    item = get_object_or_404(
        Item.objects.select_related("author", "category"),
        pk=pk,
    )
    if request.method == 'POST':
        item.deleted_at = timezone.now()
        item.is_published = False
        item.save(update_fields=['deleted_at', 'is_published'])
        messages.success(request, 'Post moved to Recent deleted.')
        url = reverse('admin_panel:posts_list')
        qs = request.GET.urlencode()
        if qs:
            url += '?' + qs
        return redirect(url)
    return render(request, 'admin/posts/post_confirm_delete.html', {'item': item})


@admin_required
def post_view_stats(request, pk):
    """View post statistics."""
    import json

    from admin_panel.services.analytics_service import get_post_activity_chart_data

    item = get_object_or_404(
        Item.objects.annotate(
            _admin_root_comments=Count(
                "comments",
                filter=Q(comments__parent__isnull=True),
            ),
            _admin_reports_count=Count("reports"),
        ),
        pk=pk,
    )
    comments_count = item._admin_root_comments
    reports_count = item._admin_reports_count
    activity_data = get_post_activity_chart_data(item, days=14)
    activity_json = json.dumps(activity_data)
    return render(request, 'admin/posts/post_stats.html', {
        'item': item,
        'comments_count': comments_count,
        'reports_count': reports_count,
        'activity_json': activity_json,
    })
