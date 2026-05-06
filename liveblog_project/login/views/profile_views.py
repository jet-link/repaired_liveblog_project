"""Profile views: view, edit, section, avatar, trust status, online status."""
from collections import OrderedDict

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.http import require_POST

from login.forms import UserEditForm, PasswordChangeSimpleForm
from login.middleware import is_user_online
from login.models import Profile
from login.views._helpers import (
    annotate_user_liked,
    annotate_user_bookmarked,
    apply_human_counts,
    build_breadcrumbs,
    build_profile_field,
    build_trust_rating_field,
    breadcrumb,
    _trending_item_ids_for_items,
)
from login.views.vanished_views import user_not_found_view
from smart_blog.models import Item
from smart_blog.feed_queryset import feed_list_optimizations

PROFILE_CREATED_PREVIEW_LIMIT = 12


def profile_view(request, username):
    user_obj = User._base_manager.select_related("profile", "deleted_queue_entry").filter(username=username).first()
    if not user_obj:
        raise Http404
    if not user_obj.is_active:
        status = "deleted" if getattr(user_obj, "deleted_queue_entry", None) else "banned"
        return user_not_found_view(request, user_obj, vanished_status=status)

    is_owner = request.user.is_authenticated and request.user == user_obj

    user_items_qs = feed_list_optimizations(
        Item.objects
        .filter(is_published=True, author=user_obj)
        .select_related("category")
        .prefetch_related("tags")
        .with_counters()
        .order_by('-published_date')
    )
    user_items_qs = annotate_user_liked(user_items_qs, request.user)
    user_items_qs = annotate_user_bookmarked(user_items_qs, request.user)

    all_count = user_items_qs.count()
    if all_count > PROFILE_CREATED_PREVIEW_LIMIT:
        created_items = list(user_items_qs[:PROFILE_CREATED_PREVIEW_LIMIT])
    else:
        created_items = list(user_items_qs)
    apply_human_counts(created_items)
    trending_item_ids = _trending_item_ids_for_items(created_items)

    profile = getattr(user_obj, 'profile', None)
    if profile is None:
        profile, _ = Profile.objects.get_or_create(user=user_obj)

    trust_score = 10.0
    try:
        trust_score = float(getattr(user_obj.profile, 'trust_score', 10.0))
    except Exception:
        pass

    def _non_empty(value):
        return bool(value and str(value).strip())

    personal_fields = {}
    if is_owner:
        personal_fields["Username"] = build_profile_field(user_obj.username, "text")
    elif profile.public_username and _non_empty(user_obj.username):
        personal_fields["Username"] = build_profile_field(user_obj.username, "text")

    if is_owner:
        personal_fields["First name"] = build_profile_field(user_obj.first_name, "text")
    elif profile.public_first_name and _non_empty(user_obj.first_name):
        personal_fields["First name"] = build_profile_field(user_obj.first_name, "text")

    if is_owner:
        personal_fields["Last name"] = build_profile_field(user_obj.last_name, "text")
    elif profile.public_last_name and _non_empty(user_obj.last_name):
        personal_fields["Last name"] = build_profile_field(user_obj.last_name, "text")

    if is_owner:
        personal_fields["Email"] = build_profile_field(
            user_obj.email, "email", is_owner=True,
        )
    elif profile.public_email and _non_empty(user_obj.email):
        personal_fields["Email"] = build_profile_field(
            user_obj.email, "email", is_owner=False,
        )

    fields = OrderedDict()
    fields["Trust rating"] = build_trust_rating_field(trust_score)
    fields.update(personal_fields)

    show_no_public_details = (not is_owner) and len(personal_fields) == 0
    has_uploaded_avatar = bool(profile.avatar_file or profile.avatar_url)
    is_online = is_user_online(user_obj)

    context = {
        'fields': fields,
        'show_no_public_details': show_no_public_details,
        'show_profile_avatar_thumbs': has_uploaded_avatar,
        'user_obj': user_obj,
        'created_items': created_items,
        'trending_item_ids': trending_item_ids,
        'is_owner': is_owner,
        'is_online': is_online,
        'trust_score': trust_score,
        'all_count': all_count,
        'show_view_all_created': all_count > PROFILE_CREATED_PREVIEW_LIMIT,
    }
    return render(request, 'accounts/profile.html', context)


def profile_online_status(request, username):
    """API: returns user online status for polling."""
    user_obj = User._base_manager.filter(username=username).first()
    if not user_obj:
        return JsonResponse({"online": False})
    return JsonResponse({"online": is_user_online(user_obj)})


def profile_section_view(request, username, section):
    user_obj = User._base_manager.select_related("deleted_queue_entry").filter(username=username).first()
    if not user_obj:
        raise Http404
    if not user_obj.is_active:
        status = "deleted" if getattr(user_obj, "deleted_queue_entry", None) else "banned"
        return user_not_found_view(request, user_obj, vanished_status=status)

    user_items_qs = feed_list_optimizations(
        Item.objects
        .filter(is_published=True, author=user_obj)
        .select_related("category")
        .prefetch_related("tags")
        .with_counters()
        .order_by('-published_date')
    )
    user_items_qs = annotate_user_liked(user_items_qs, request.user)
    user_items_qs = annotate_user_bookmarked(user_items_qs, request.user)

    section = (section or '').lower()
    if section != 'created':
        raise Http404

    section_title = 'Created'
    section_count = user_items_qs.count()

    paginator = Paginator(user_items_qs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(
        number=page_obj.number, on_each_side=1, on_ends=1,
    )

    apply_human_counts(page_obj)
    trending_item_ids = _trending_item_ids_for_items(list(page_obj))

    if not user_obj.is_active:
        crumb_user_label = "Deleted user" if getattr(user_obj, "deleted_queue_entry", None) else "Banned user"
    else:
        crumb_user_label = user_obj.username
    breadcrumbs = build_breadcrumbs(
        breadcrumb(crumb_user_label, reverse("login_app:profile", kwargs={"username": user_obj.username})),
        breadcrumb(section_title, None),
    )

    link_url = reverse("login_app:profile-section", kwargs={"username": user_obj.username, "section": section})
    context = {
        'user_obj': user_obj,
        'items': page_obj,
        'page_obj': page_obj,
        'page_range': page_range,
        'section': section,
        'section_title': section_title,
        'section_count': section_count,
        'breadcrumbs': breadcrumbs,
        'link_url': link_url,
        'listing_user': user_obj.username,
        'trending_item_ids': trending_item_ids,
    }
    return render(request, 'accounts/profile_section.html', context)


@login_required
def api_trust_status(request):
    """API: returns trust status for polling (shadow_banned, can_post)."""
    profile = getattr(request.user, 'profile', None)
    return JsonResponse({
        "shadow_banned": getattr(profile, 'shadow_banned', False),
        "can_post": getattr(profile, 'can_post', True),
    })


@login_required
def profile_edit(request, username):
    user_obj = get_object_or_404(User, username=username)

    if request.user != user_obj:
        raise PermissionDenied

    if request.method == "POST":
        if 'profile_submit' in request.POST:
            form = UserEditForm(request.POST, request.FILES, instance=user_obj)
            password_form = PasswordChangeSimpleForm()

            if form.is_valid():
                form.save()
                new_username = form.cleaned_data.get('username') or user_obj.username
                messages.success(request, 'Profile was successfully edited')
                return redirect('login_app:profile', username=new_username)

        elif 'password_submit' in request.POST:
            form = UserEditForm(instance=user_obj)
            password_form = PasswordChangeSimpleForm(request.POST)
            if password_form.is_valid():
                new_password = password_form.cleaned_data['new_password1']
                user_obj.set_password(new_password)
                user_obj.save()
                update_session_auth_hash(request, user_obj)
                return redirect('login_app:profile', username=user_obj.username)
        else:
            form = UserEditForm(instance=user_obj)
            password_form = PasswordChangeSimpleForm()
    else:
        form = UserEditForm(instance=user_obj)
        password_form = PasswordChangeSimpleForm()

    return render(request, 'accounts/profile_edit.html', {
        'form': form,
        'password_form': password_form,
        'user_obj': user_obj,
    })


@login_required
@require_POST
def remove_avatar(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No profile found.'}, status=404)

    if profile.avatar_file:
        profile.avatar_file.delete(save=False)
        profile.avatar_file = None

    profile.avatar_url = None
    profile.save()

    return JsonResponse({
        'success': True,
        'default_avatar': static('img/no_avatar.svg'),
    })
