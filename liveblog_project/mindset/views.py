"""Mindset views: listing, theme creation, theme detail and JSON APIs.

Live updates use a hybrid model:
- Author of an action sees DOM injection immediately via the JSON response from
  ``api_theme_reply`` / ``api_theme_like`` / ``api_theme_repost``.
- Other tabs poll ``api_theme_state`` and ``api_themes_state`` for new replies
  and refreshed counters every few seconds.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import (
    BooleanField,
    Exists,
    ExpressionWrapper,
    F,
    FloatField,
    OuterRef,
    Prefetch,
    Q,
    Value,
)
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from smart_blog.notification_utils import (
    notify_mindset_theme_reply,
    notify_or_bump_mindset_theme_repost,
)
from smart_blog.utils import breadcrumb, build_breadcrumbs, count_convert

from .body_html import (
    extract_hashtags,
    html_to_plain_text,
    normalise_hashtags,
)
from .forms import ReplyForm, ThemeForm
from .image_service import (
    MAX_REPLY_IMAGES,
    MAX_THEME_IMAGES,
    MindsetImageError,
    attach_reply_image,
    attach_theme_images,
)
from .models import (
    Hashtag,
    MindsetFollow,
    Reply,
    ReplyImage,
    ReplyLike,
    ReplyRepost,
    Theme,
    ThemeImage,
    ThemeLike,
    ThemeRepost,
)

User = get_user_model()

THEME_PAGE_SIZE = 20
MINDSET_LIST_PAGE_SIZE = 50
SIDEBAR_LIMIT = 5
REPLY_COOLDOWN_SECONDS = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _annotate_user_state(qs, user):
    """Add user_liked / user_reposted booleans to a Theme/Reply queryset.

    For Theme querysets we additionally annotate ``user_following_author`` so
    the theme card can render the correct Follow/Unfollow link state without
    triggering an extra query per row.
    """
    model = qs.model
    if not user.is_authenticated:
        annotations = {
            'user_liked': Value(False, output_field=BooleanField()),
            'user_reposted': Value(False, output_field=BooleanField()),
        }
        if model is Theme:
            annotations['user_following_author'] = Value(False, output_field=BooleanField())
        return qs.annotate(**annotations)

    if model is Theme:
        like_qs = ThemeLike.objects.filter(theme=OuterRef('pk'), user=user)
        repost_qs = ThemeRepost.objects.filter(theme=OuterRef('pk'), user=user)
        follow_qs = MindsetFollow.objects.filter(
            follower=user, followee=OuterRef('author')
        )
        return qs.annotate(
            user_liked=Exists(like_qs),
            user_reposted=Exists(repost_qs),
            user_following_author=Exists(follow_qs),
        )

    like_qs = ReplyLike.objects.filter(reply=OuterRef('pk'), user=user)
    repost_qs = ReplyRepost.objects.filter(reply=OuterRef('pk'), user=user)
    # Reply Follow/Followed — disabled for now (main themes only):
    # follow_qs = MindsetFollow.objects.filter(
    #     follower=user, followee=OuterRef('author')
    # )
    return qs.annotate(
        user_liked=Exists(like_qs),
        user_reposted=Exists(repost_qs),
        # user_following_author=Exists(follow_qs),
    )


def _annotate_popularity(qs):
    """Discussion popularity = replies + 0.5*reposts + 0.2*likes, with a recency
    factor (older themes decay slowly)."""
    return qs.annotate(
        popularity=ExpressionWrapper(
            (F('replies_count') * 1.0)
            + (F('reposts_count') * 0.5)
            + (F('likes_count') * 0.2),
            output_field=FloatField(),
        )
    )


def _theme_images_prefetch():
    """Prefetch ThemeImage rows once per Theme queryset so feed cards never
    issue N+1 queries to render the image grid. We deliberately omit
    ``to_attr`` so the template can keep using ``theme.images.all`` and
    still benefit from the prefetched, ordered result set."""
    return Prefetch(
        'images',
        queryset=ThemeImage.objects.order_by('sort_order', 'pk'),
    )


def _theme_base_qs():
    return (
        Theme.objects.filter(is_deleted=False)
        .select_related('author', 'author__profile')
        .prefetch_related('hashtags', _theme_images_prefetch())
    )


def _body_has_hashtag(body: str, slug: str) -> bool:
    """True if ``body`` (HTML or plain) contains ``#tag`` with this canonical slug."""
    if not body or not slug:
        return False
    return any(s == slug for _, s in normalise_hashtags(extract_hashtags(body)))


def _replies_with_hashtag_qs(theme_id: int, tag: Hashtag, user):
    """Top-level replies under ``theme_id`` whose body precisely matches ``tag``.

    Uses ``icontains`` only to narrow the SQL set, then a precise Python pass via
    ``_body_has_hashtag`` so noise like ``#loveisresquelife2`` doesn't leak.
    """
    qs = (
        Reply.objects.filter(theme_id=theme_id, parent__isnull=True, is_deleted=False)
        .select_related('author', 'author__profile', 'image')
    )
    needles = {tag.slug, tag.name}
    icontains = Q()
    for needle in needles:
        icontains |= Q(body__icontains=f'#{needle}')
    qs = qs.filter(icontains).order_by('-created_at')
    qs = _annotate_user_state(qs, user)
    return [r for r in qs if _body_has_hashtag(r.body, tag.slug)]


def _apply_hashtag_reply_filter(themes, tag: Hashtag, user) -> None:
    """Replace ``annotated_replies`` with the hashtag-matching subset only."""
    for theme in themes:
        theme.annotated_replies = _replies_with_hashtag_qs(theme.pk, tag, user)


def _theme_ids_with_hashtag_reply(tag: Hashtag) -> list[int]:
    """Theme ids that have at least one top-level reply matching ``tag`` precisely."""
    needles = {tag.slug, tag.name}
    icontains = Q()
    for needle in needles:
        icontains |= Q(body__icontains=f'#{needle}')
    candidate_replies = (
        Reply.objects.filter(parent__isnull=True, is_deleted=False)
        .filter(icontains)
        .values_list('theme_id', 'body')
    )
    return [tid for tid, body in candidate_replies if _body_has_hashtag(body, tag.slug)]


def _annotated_top_level_replies_prefetch(user):
    """Prefetch top-level replies with user_liked / user_reposted annotated.

    Required so that ``_theme_card.html`` renders the correct heart state for
    each reply on the listing — without this, ``theme.replies.all`` returns
    bare ``Reply`` objects whose ``user_liked``/``user_reposted`` fall back to
    ``False`` and the icon stays as ``fa-heart-o`` even after a like.
    """
    qs = (
        Reply.objects.filter(is_deleted=False, parent__isnull=True)
        .select_related('author', 'author__profile', 'image')
        .order_by('-created_at')
    )
    return Prefetch(
        'replies',
        queryset=_annotate_user_state(qs, user),
        to_attr='annotated_replies',
    )


def _theme_qs_for_listing(user):
    """Theme queryset annotated with user state and replies prefetched + annotated."""
    return _annotate_user_state(_theme_base_qs(), user).prefetch_related(
        _annotated_top_level_replies_prefetch(user)
    )


def _persist_hashtags(theme: Theme) -> None:
    """Parse #tags from the saved theme body and replace M2M with canonical Hashtag rows."""
    plain = html_to_plain_text(theme.body)
    names = extract_hashtags(plain)
    pairs = normalise_hashtags(names)
    if not pairs:
        theme.hashtags.clear()
        return
    tags: list[Hashtag] = []
    for name, slug in pairs:
        tag, _created = Hashtag.objects.get_or_create(slug=slug, defaults={'name': name})
        tags.append(tag)
    theme.hashtags.set(tags)


def _ensure_hashtags_exist(body: str) -> None:
    """Make sure Hashtag rows exist for every #tag mentioned in arbitrary body
    HTML (used by replies). Replies don't M2M-attach to themes, so we only
    `get_or_create` the canonical rows — ``themes_count`` stays untouched
    because it is only mutated by Theme.hashtags m2m signals.

    Without this, hashtag links rendered inside reply bodies (which point at
    ``mindset:theme_list_by_tag``) would 404 whenever a tag has been used in a
    reply but never in any theme.
    """
    plain = html_to_plain_text(body or '')
    pairs = normalise_hashtags(extract_hashtags(plain))
    for name, slug in pairs:
        Hashtag.objects.get_or_create(slug=slug, defaults={'name': name})


def _render_theme_card(theme: Theme, request) -> str:
    annotated = _theme_qs_for_listing(request.user).filter(pk=theme.pk).first()
    return render_to_string(
        'mindset/_theme_card.html',
        {'theme': annotated or theme, 'request': request, 'user': request.user},
        request=request,
    )


def _render_reply(reply: Reply, request) -> str:
    annotated = _annotate_user_state(
        Reply.objects.filter(pk=reply.pk).select_related(
            'author', 'author__profile', 'image'
        ),
        request.user,
    ).first()
    return render_to_string(
        'mindset/_reply.html',
        {'reply': annotated or reply, 'request': request, 'user': request.user},
        request=request,
    )


def _theme_state_payload(theme: Theme, request) -> dict:
    author_username = getattr(getattr(theme, 'author', None), 'username', '') or ''
    return {
        'id': theme.pk,
        'replies_count': theme.replies_count,
        'replies_count_human': count_convert(theme.replies_count),
        'likes_count': theme.likes_count,
        'likes_count_human': count_convert(theme.likes_count),
        'reposts_count': theme.reposts_count,
        'reposts_count_human': count_convert(theme.reposts_count),
        'user_liked': bool(getattr(theme, 'user_liked', False)),
        'user_reposted': bool(getattr(theme, 'user_reposted', False)),
        'user_following_author': bool(getattr(theme, 'user_following_author', False)),
        'author_username': author_username,
    }


def _reply_state_payload(reply: Reply) -> dict:
    return {
        'id': reply.pk,
        'theme_id': reply.theme_id,
        'parent_id': reply.parent_id,
        'replies_count': reply.replies_count,
        'replies_count_human': count_convert(reply.replies_count),
        'likes_count': reply.likes_count,
        'likes_count_human': count_convert(reply.likes_count),
        'reposts_count': reply.reposts_count,
        'reposts_count_human': count_convert(reply.reposts_count),
        'user_liked': bool(getattr(reply, 'user_liked', False)),
        'user_reposted': bool(getattr(reply, 'user_reposted', False)),
    }


def _sidebar_theme_entry(theme: Theme) -> dict:
    return {
        'id': theme.pk,
        'preview': theme.preview,
        'likes': theme.likes_count,
        'likes_human': count_convert(theme.likes_count),
        'replies': theme.replies_count,
        'replies_human': count_convert(theme.replies_count),
        'reposts': theme.reposts_count,
        'reposts_human': count_convert(theme.reposts_count),
        'url': f'/mindset/theme/{theme.pk}/',
    }


def _sidebar_payload() -> dict:
    # Sidebar "Most popular themes": popularity = likes + reposts. We re-evaluate
    # the ordering on every payload build so periodic polling
    # (mindset_feed.js → pollSidebar) automatically promotes themes that just
    # earned a like/repost above their neighbours.
    popular = list(
        _theme_base_qs()
        .annotate(
            popular_score=ExpressionWrapper(
                F('likes_count') + F('reposts_count'),
                output_field=FloatField(),
            )
        )
        .order_by('-popular_score', '-created_at')[:SIDEBAR_LIMIT]
    )
    top = list(
        _annotate_popularity(_theme_base_qs())
        .order_by('-popularity', '-created_at')[:SIDEBAR_LIMIT]
    )
    return {
        'last': [_sidebar_theme_entry(t) for t in popular],
        'top': [_sidebar_theme_entry(t) for t in top],
    }


# ---------------------------------------------------------------------------
# Page views
# ---------------------------------------------------------------------------


def _resolve_filter(request) -> tuple[str, Hashtag | None]:
    fil = (request.GET.get('filter') or '').strip().lower()
    if fil not in ('latest', 'popular'):
        fil = 'latest'
    tag_slug = (request.GET.get('tag') or '').strip().lower() or None
    tag = None
    if tag_slug:
        tag = Hashtag.objects.filter(slug=tag_slug).first()
    return fil, tag


def _mindset_main_wall_path(active_tag: Hashtag | None) -> str:
    if active_tag is not None and getattr(active_tag, 'slug', None):
        return reverse('mindset:theme_list_by_tag', kwargs={'slug': active_tag.slug})
    return reverse('mindset:theme_list')


def _mindset_wall_mode(request) -> str:
    """``main`` (default) or ``following`` — only for display; guests ignore ``following``."""
    if not request.user.is_authenticated:
        return 'main'
    if (request.GET.get('wall') or '').strip().lower() == 'following':
        return 'following'
    return 'main'


def theme_list(request, *, active_tag: Hashtag | None = None):
    fil, tag = _resolve_filter(request)
    if active_tag is not None:
        tag = active_tag

    wall_mode = _mindset_wall_mode(request)
    if tag is not None:
        wall_mode = 'main'
    main_path = _mindset_main_wall_path(tag)
    following_path = f'{main_path}?wall=following'

    qs = _theme_qs_for_listing(request.user)
    if tag is not None:
        reply_theme_ids = _theme_ids_with_hashtag_reply(tag)
        qs = qs.filter(Q(hashtags__slug=tag.slug) | Q(pk__in=reply_theme_ids)).distinct()

    if request.user.is_authenticated and wall_mode == 'following' and tag is None:
        followee_ids = list(
            MindsetFollow.objects.filter(follower=request.user).values_list(
                'followee_id', flat=True
            )
        )
        qs = qs.filter(author_id__in=followee_ids)
        qs = qs.order_by('-created_at')
    else:
        qs = _annotate_popularity(qs)
        if fil == 'popular':
            qs = qs.order_by('-popularity', '-created_at')
        else:
            qs = qs.order_by('-created_at')

    paginator = Paginator(qs, MINDSET_LIST_PAGE_SIZE)
    page_number = request.GET.get('page') or 1
    page_obj = paginator.get_page(page_number)

    if tag is not None:
        _apply_hashtag_reply_filter(page_obj.object_list, tag, request.user)

    page_range = paginator.get_elided_page_range(
        number=page_obj.number,
        on_each_side=1,
        on_ends=1,
    )
    q_extra = request.GET.copy()
    q_extra.pop('page', None)
    q_extra.pop('partial', None)
    extra_encoded = q_extra.urlencode()
    pagination_extra = f'&{extra_encoded}' if extra_encoded else ''

    context = {
        'page_obj': page_obj,
        'page_range': page_range,
        'pagination_extra': pagination_extra,
        'themes': page_obj.object_list,
        'active_filter': fil,
        'active_tag': tag,
        'mindset_wall': wall_mode,
        'mindset_main_wall_url': main_path,
        'mindset_following_wall_url': following_path,
        'mindset_has_themes': Theme.objects.filter(is_deleted=False).exists(),
    }

    is_partial = (
        request.GET.get('partial') == '1'
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    )
    if is_partial:
        return render(request, 'mindset/_themes_feed.html', context)

    context['sidebar'] = _sidebar_payload()
    return render(request, 'mindset/theme_list.html', context)


def theme_list_by_tag(request, slug):
    # Hashtags can appear inside replies, which don't M2M-attach to themes,
    # so the canonical Hashtag row may not exist yet even though the
    # linkified URL is valid. Render an empty themes list with the slug as
    # the active tag instead of 404. We deliberately do NOT auto-create the
    # row from a GET to avoid letting anyone pollute the table by hitting
    # random URLs — rows are only persisted via theme/reply save paths.
    cleaned = slug.strip().lower()
    tag = Hashtag.objects.filter(slug=cleaned).first()
    if tag is None:
        tag = Hashtag(name=cleaned, slug=cleaned)
    return theme_list(request, active_tag=tag)


THEME_BREADCRUMB_LABEL_MAX = 36


def _theme_breadcrumb_label(theme, max_len=THEME_BREADCRUMB_LABEL_MAX):
    text = (theme.body_text or '').strip()
    if not text:
        return f'Theme #{theme.pk}'
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + '…'


def theme_detail(request, pk):
    theme = get_object_or_404(_theme_base_qs(), pk=pk)
    annotated = _theme_qs_for_listing(request.user).filter(pk=theme.pk).first()
    theme_obj = annotated or theme
    crumb_title = _theme_breadcrumb_label(theme_obj)
    breadcrumbs = build_breadcrumbs(
        breadcrumb('Mindset', reverse('mindset:theme_list')),
        breadcrumb(crumb_title, None),
    )
    return render(
        request,
        'mindset/theme_detail.html',
        {
            'theme': theme_obj,
            'sidebar': _sidebar_payload(),
            'breadcrumbs': breadcrumbs,
        },
    )


@login_required
def theme_create(request):
    if request.method == 'POST':
        form = ThemeForm(request.POST, request.FILES)
        files = request.FILES.getlist('images')
        if len(files) > MAX_THEME_IMAGES:
            form.add_error(
                None,
                f'You can attach up to {MAX_THEME_IMAGES} images per theme.',
            )
        if form.is_valid():
            try:
                with transaction.atomic():
                    theme = form.save(commit=False)
                    theme.author = request.user
                    theme.body_text = html_to_plain_text(theme.body)
                    theme.save()
                    _persist_hashtags(theme)
                    if files:
                        attach_theme_images(theme, files)
            except MindsetImageError as exc:
                form.add_error(None, str(exc))
            else:
                return redirect(f"{reverse('mindset:theme_list')}?theme_posted=1")
    else:
        form = ThemeForm()

    return render(
        request,
        'mindset/create_theme.html',
        {
            'form': form,
            'max_theme_images': MAX_THEME_IMAGES,
        },
    )


# ---------------------------------------------------------------------------
# JSON APIs
# ---------------------------------------------------------------------------


@require_GET
def api_themes_state(request):
    """Return state for visible themes (counters + flags) for polling.

    ``ids`` query param is comma-separated theme ids the client cares about.
    """
    ids_raw = request.GET.get('ids') or ''
    ids: list[int] = []
    for chunk in ids_raw.split(','):
        chunk = chunk.strip()
        if chunk.isdigit():
            ids.append(int(chunk))
            if len(ids) >= 100:
                break
    if not ids:
        return JsonResponse({'ok': True, 'themes': []})

    qs = _annotate_user_state(_theme_base_qs().filter(pk__in=ids), request.user)
    payload = [_theme_state_payload(t, request) for t in qs]
    return JsonResponse({'ok': True, 'themes': payload})


@require_GET
def api_sidebar(request):
    return JsonResponse({'ok': True, **_sidebar_payload()})


@require_GET
def api_theme_state(request, pk):
    theme = get_object_or_404(_theme_base_qs(), pk=pk)
    annotated = _annotate_user_state(_theme_base_qs().filter(pk=pk), request.user).first() or theme
    payload = _theme_state_payload(annotated, request)

    tag_slug = (request.GET.get('tag') or '').strip().lower() or None
    tag = Hashtag.objects.filter(slug=tag_slug).first() if tag_slug else None
    if tag is None and tag_slug:
        tag = Hashtag(name=tag_slug, slug=tag_slug)

    since_id = request.GET.get('since_id')
    new_replies_html: list[str] = []
    new_ids: list[int] = []
    if since_id and since_id.isdigit():
        new_qs = (
            _annotate_user_state(
                Reply.objects.filter(theme_id=pk, pk__gt=int(since_id), is_deleted=False)
                .select_related('author', 'author__profile', 'image')
                .order_by('created_at'),
                request.user,
            )[:50]
        )
        for reply in new_qs:
            if tag is not None and not _body_has_hashtag(reply.body, tag.slug):
                continue
            new_replies_html.append(
                render_to_string(
                    'mindset/_reply.html',
                    {'reply': reply, 'request': request, 'user': request.user},
                    request=request,
                )
            )
            new_ids.append(reply.pk)
        payload['new_replies_html'] = new_replies_html
        payload['new_reply_ids'] = new_ids

    return JsonResponse({'ok': True, **payload})


@login_required
@require_POST
def api_theme_reply(request, pk):
    theme = get_object_or_404(_theme_base_qs(), pk=pk)
    if theme.author_id == request.user.id:
        return JsonResponse({'ok': False, 'error': 'You cannot reply to your own theme.'}, status=403)

    cooldown_key = f'mindset_reply_cooldown_theme_{pk}'
    now_ts = timezone.now().timestamp()
    last_ts = request.session.get(cooldown_key)
    if last_ts and (now_ts - float(last_ts)) < REPLY_COOLDOWN_SECONDS:
        remaining = int(REPLY_COOLDOWN_SECONDS - (now_ts - float(last_ts)))
        return JsonResponse(
            {'ok': False, 'error': f'Please wait {max(remaining, 1)}s before replying again.'},
            status=429,
        )

    form = ReplyForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    body = form.cleaned_data['body']
    image_files = request.FILES.getlist('image')[:MAX_REPLY_IMAGES]
    try:
        with transaction.atomic():
            reply = Reply.objects.create(
                theme=theme,
                author=request.user,
                body=body,
            )
            if image_files:
                attach_reply_image(reply, image_files)
    except MindsetImageError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    _ensure_hashtags_exist(body)
    notify_mindset_theme_reply(theme=theme, reply=reply)
    request.session[cooldown_key] = now_ts

    annotated = _annotate_user_state(
        Reply.objects.filter(pk=reply.pk).select_related(
            'author', 'author__profile', 'image'
        ),
        request.user,
    ).first() or reply

    html = render_to_string(
        'mindset/_reply.html',
        {'reply': annotated, 'request': request, 'user': request.user},
        request=request,
    )

    theme.refresh_from_db(fields=['replies_count', 'likes_count', 'reposts_count'])
    return JsonResponse({
        'ok': True,
        'reply_html': html,
        'reply_id': reply.pk,
        'theme': _theme_state_payload(
            _annotate_user_state(_theme_base_qs().filter(pk=theme.pk), request.user).first() or theme,
            request,
        ),
    })


@login_required
@require_POST
def api_reply_reply(request, pk):
    parent = get_object_or_404(Reply.objects.filter(is_deleted=False), pk=pk)
    if parent.author_id == request.user.id:
        return JsonResponse({'ok': False, 'error': 'You cannot reply to your own reply.'}, status=403)

    cooldown_key = f'mindset_reply_cooldown_reply_{pk}'
    now_ts = timezone.now().timestamp()
    last_ts = request.session.get(cooldown_key)
    if last_ts and (now_ts - float(last_ts)) < REPLY_COOLDOWN_SECONDS:
        remaining = int(REPLY_COOLDOWN_SECONDS - (now_ts - float(last_ts)))
        return JsonResponse(
            {'ok': False, 'error': f'Please wait {max(remaining, 1)}s before replying again.'},
            status=429,
        )

    form = ReplyForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    image_files = request.FILES.getlist('image')[:MAX_REPLY_IMAGES]
    try:
        with transaction.atomic():
            reply = Reply.objects.create(
                theme=parent.theme,
                parent=parent,
                author=request.user,
                body=form.cleaned_data['body'],
            )
            if image_files:
                attach_reply_image(reply, image_files)
    except MindsetImageError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    _ensure_hashtags_exist(reply.body)
    notify_mindset_theme_reply(theme=parent.theme, reply=reply)
    request.session[cooldown_key] = now_ts

    annotated = _annotate_user_state(
        Reply.objects.filter(pk=reply.pk).select_related(
            'author', 'author__profile', 'image'
        ),
        request.user,
    ).first() or reply

    html = render_to_string(
        'mindset/_reply.html',
        {'reply': annotated, 'request': request, 'user': request.user},
        request=request,
    )

    parent.refresh_from_db(fields=['replies_count', 'likes_count', 'reposts_count'])
    return JsonResponse({
        'ok': True,
        'reply_html': html,
        'reply_id': reply.pk,
        'parent_id': parent.pk,
        'parent': _reply_state_payload(parent),
    })


def _toggle(model, *, lookup_kwargs, user) -> bool:
    """Return True when a new like/repost was created, False when an existing
    one was removed."""
    obj = model.objects.filter(user=user, **lookup_kwargs).first()
    if obj:
        obj.delete()
        return False
    model.objects.create(user=user, **lookup_kwargs)
    return True


def _fresh_theme_state(theme_pk: int, request) -> dict:
    """Re-annotate user_liked / user_reposted from DB so toggle responses don't
    accidentally un-toggle the OTHER button on the client."""
    annotated = _annotate_user_state(_theme_base_qs().filter(pk=theme_pk), request.user).first()
    if annotated is None:
        annotated = Theme.objects.get(pk=theme_pk)
    return _theme_state_payload(annotated, request)


def _fresh_reply_state(reply_pk: int, request) -> dict:
    annotated = _annotate_user_state(
        Reply.objects.filter(pk=reply_pk).select_related('author'),
        request.user,
    ).first()
    if annotated is None:
        annotated = Reply.objects.get(pk=reply_pk)
    return _reply_state_payload(annotated)


@login_required
@require_POST
def api_theme_like(request, pk):
    theme = get_object_or_404(_theme_base_qs(), pk=pk)
    if theme.author_id == request.user.id:
        return JsonResponse({'ok': False, 'error': 'You cannot like your own theme.'}, status=403)
    created = _toggle(ThemeLike, lookup_kwargs={'theme': theme}, user=request.user)
    return JsonResponse({
        'ok': True,
        'liked': created,
        'theme': _fresh_theme_state(theme.pk, request),
    })


@login_required
@require_POST
def api_theme_repost(request, pk):
    theme = get_object_or_404(_theme_base_qs(), pk=pk)
    created = _toggle(ThemeRepost, lookup_kwargs={'theme': theme}, user=request.user)
    if created:
        notify_or_bump_mindset_theme_repost(theme=theme, actor_user=request.user)
    return JsonResponse({
        'ok': True,
        'reposted': created,
        'theme': _fresh_theme_state(theme.pk, request),
    })


@login_required
@require_POST
def api_reply_like(request, pk):
    reply = get_object_or_404(Reply.objects.filter(is_deleted=False), pk=pk)
    if reply.author_id == request.user.id:
        return JsonResponse({'ok': False, 'error': 'You cannot like your own reply.'}, status=403)
    created = _toggle(ReplyLike, lookup_kwargs={'reply': reply}, user=request.user)
    return JsonResponse({
        'ok': True,
        'liked': created,
        'reply': _fresh_reply_state(reply.pk, request),
    })


@login_required
@require_POST
def api_reply_repost(request, pk):
    reply = get_object_or_404(Reply.objects.filter(is_deleted=False), pk=pk)
    created = _toggle(ReplyRepost, lookup_kwargs={'reply': reply}, user=request.user)
    return JsonResponse({
        'ok': True,
        'reposted': created,
        'reply': _fresh_reply_state(reply.pk, request),
    })


# ---------------------------------------------------------------------------
# Edit / delete (12-hour window, owner only)
# ---------------------------------------------------------------------------


@login_required
@require_POST
def api_theme_edit(request, pk):
    theme = get_object_or_404(_theme_base_qs(), pk=pk)
    if theme.author_id != request.user.id:
        return JsonResponse({'ok': False, 'error': 'Permission denied.'}, status=403)
    if not theme.is_editable:
        return JsonResponse({'ok': False, 'error': 'Editing window has expired.'}, status=403)

    form = ThemeForm(request.POST, instance=theme)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    with transaction.atomic():
        updated = form.save(commit=False)
        updated.body_text = html_to_plain_text(updated.body)
        updated.save()
        _persist_hashtags(updated)

    return JsonResponse({
        'ok': True,
        'theme_html': _render_theme_card(updated, request),
        'theme': _fresh_theme_state(updated.pk, request),
    })


@login_required
@require_POST
def api_theme_delete(request, pk):
    theme = get_object_or_404(_theme_base_qs(), pk=pk)
    if theme.author_id != request.user.id:
        return JsonResponse({'ok': False, 'error': 'Permission denied.'}, status=403)
    if not theme.is_editable:
        return JsonResponse({'ok': False, 'error': 'Delete window has expired.'}, status=403)
    theme.delete()
    return JsonResponse({'ok': True, 'deleted_theme_id': pk})


@login_required
@require_POST
def api_reply_edit(request, pk):
    reply = get_object_or_404(Reply.objects.filter(is_deleted=False), pk=pk)
    if reply.author_id != request.user.id:
        return JsonResponse({'ok': False, 'error': 'Permission denied.'}, status=403)
    if not reply.is_editable:
        return JsonResponse({'ok': False, 'error': 'Editing window has expired.'}, status=403)

    form = ReplyForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    reply.body = form.cleaned_data['body']
    reply.save(update_fields=['body', 'updated_at'])
    _ensure_hashtags_exist(reply.body)

    annotated = _annotate_user_state(
        Reply.objects.filter(pk=reply.pk).select_related('author', 'author__profile'),
        request.user,
    ).first() or reply
    html = render_to_string(
        'mindset/_reply.html',
        {'reply': annotated, 'request': request, 'user': request.user},
        request=request,
    )
    return JsonResponse({
        'ok': True,
        'reply_html': html,
        'reply': _fresh_reply_state(reply.pk, request),
    })


@login_required
@require_POST
def api_user_follow_toggle(request, username):
    """Toggle Mindset subscription on ``username``.

    Self-follow is rejected; deleted/banned users cannot be followed. Returns
    ``following: bool`` so the client can paint every link that points at the
    same author username on the page.
    """
    target = User.objects.filter(username=username, is_active=True).first()
    if not target:
        return JsonResponse({'ok': False, 'error': 'User not found.'}, status=404)
    if target.pk == request.user.pk:
        return JsonResponse({'ok': False, 'error': 'Cannot follow yourself.'}, status=400)

    existing = MindsetFollow.objects.filter(follower=request.user, followee=target).first()
    if existing:
        existing.delete()
        following = False
    else:
        MindsetFollow.objects.create(follower=request.user, followee=target)
        following = True
    return JsonResponse({
        'ok': True,
        'following': following,
        'username': target.username,
    })


@login_required
@require_POST
def api_reply_delete(request, pk):
    reply = get_object_or_404(Reply.objects.filter(is_deleted=False), pk=pk)
    if reply.author_id != request.user.id:
        return JsonResponse({'ok': False, 'error': 'Permission denied.'}, status=403)
    if not reply.is_editable:
        return JsonResponse({'ok': False, 'error': 'Delete window has expired.'}, status=403)
    theme_pk = reply.theme_id
    reply.delete()
    return JsonResponse({
        'ok': True,
        'deleted_reply_id': pk,
        'theme': _fresh_theme_state(theme_pk, request),
    })
