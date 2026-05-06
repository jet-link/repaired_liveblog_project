"""Item CRUD views: create_item, edit_item, delete_item, delete_item_image, video_chunk_upload."""
import hashlib
import logging
import os
import tempfile
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from smart_blog.forms import ItemCreateForm
from smart_blog.models import BodyPinContentType, Item, ItemImage, ItemVideo
from smart_blog.services.document_converter import process_item_document
from smart_blog.services.item_write import (
    attach_item_images_from_uploads,
    delete_item_images_by_ids,
    merge_item_tags,
    validate_edit_image_totals,
    validate_uploaded_image_files,
)
from smart_blog.video_utils import (
    ALLOWED_VIDEO_MIME_TYPES,
    MAX_VIDEO_FILE_SIZE_BYTES,
    attach_chunked_videos,
    attach_item_videos_from_uploads,
    delete_item_videos_by_ids,
    validate_edit_video_totals,
    validate_uploaded_video_files,
)

logger = logging.getLogger(__name__)

CHUNK_UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "video_chunks")


def find_existing_media_path(filename, subdir=None):
    if not filename:
        return None
    try:
        base_root = settings.MEDIA_ROOT
        if base_root:
            search_root = os.path.join(base_root, subdir) if subdir else base_root
            if os.path.isdir(search_root):
                for root, _dirs, files in os.walk(search_root):
                    if filename in files:
                        full_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(full_path, base_root)
                        return rel_path.replace(os.sep, '/')
    except Exception:
        pass
    if subdir:
        rel_path = f"{subdir}/{filename}"
        try:
            if default_storage.exists(rel_path):
                return rel_path
        except Exception:
            pass
    return None


def _ensure_can_create_item(request):
    if request.user.is_superuser:
        return None
    profile = getattr(request.user, 'profile', None)
    can_post = getattr(profile, 'can_post', True)
    shadow_banned = getattr(profile, 'shadow_banned', False)
    if can_post and not shadow_banned:
        return None
    msg = (
        "You have been shadow banned. Improve your trust score to restore access."
        if shadow_banned
        else "Create post is disabled. Improve your trust score to restore access."
    )
    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"success": False, "error": msg}, status=403)
    return redirect('smart_blog:items_list')


def _json_form_errors(form):
    return {k: [str(x) for x in v] for k, v in form.errors.items()}


def _image_validation_ok_create(form, files) -> bool:
    return validate_uploaded_image_files(files, form)


def _image_validation_ok_edit(form, item, files, delete_ids) -> bool:
    return validate_uploaded_image_files(files, form) and validate_edit_image_totals(
        item, files, delete_ids, form
    )


@login_required
def create_item(request):
    denied = _ensure_can_create_item(request)
    if denied is not None:
        return denied

    if request.method != "POST":
        form = ItemCreateForm(is_create=True)
        return render(
            request,
            "smart_blog/create_item.html",
            {"form": form, "selected_tag_ids": []},
        )

    form = ItemCreateForm(request.POST, request.FILES, is_create=True)
    if not form.is_valid():
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": False, "errors": _json_form_errors(form)}, status=400)
        selected_tag_ids = [int(x) for x in request.POST.getlist("tags") if x.isdigit()]
        return render(
            request,
            "smart_blog/create_item.html",
            {"form": form, "selected_tag_ids": selected_tag_ids},
        )

    files = request.FILES.getlist("images")
    video_files = request.FILES.getlist("videos")
    if not _image_validation_ok_create(form, files):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": False, "errors": _json_form_errors(form)}, status=400)
        selected_tag_ids = [int(x) for x in request.POST.getlist("tags") if x.isdigit()]
        return render(
            request,
            "smart_blog/create_item.html",
            {"form": form, "selected_tag_ids": selected_tag_ids},
        )

    if video_files and not validate_uploaded_video_files(video_files, form):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": False, "errors": _json_form_errors(form)}, status=400)
        selected_tag_ids = [int(x) for x in request.POST.getlist("tags") if x.isdigit()]
        return render(
            request,
            "smart_blog/create_item.html",
            {"form": form, "selected_tag_ids": selected_tag_ids},
        )

    chunked_video_ids = request.POST.getlist("chunked_video_ids")

    try:
        with transaction.atomic():
            item = form.save(commit=False)
            item.author = request.user
            item.body_sourced_from_document = getattr(
                form, "_body_sourced_from_document", False
            )
            pin = form.cleaned_data.get("body_pin_file")
            if pin:
                item.body_pin_original = pin
                pn = pin.name.lower()
                if pn.endswith(".pdf"):
                    item.body_pin_content_type = BodyPinContentType.PDF
                elif pn.endswith(".docx"):
                    item.body_pin_content_type = BodyPinContentType.DOCX
            item.body_pin_plain_snapshot = getattr(
                form, "_body_pin_plain_snapshot", ""
            ) or ""
            item.save()
            if pin:
                process_item_document(item)
            item.tags.set(merge_item_tags(form.cleaned_data))
            attach_item_images_from_uploads(item, files)
            attach_item_videos_from_uploads(item, video_files)
            if chunked_video_ids:
                attach_chunked_videos(item, chunked_video_ids, request.session)
    except Exception:
        logger.exception("create_item failed for user %s", request.user.pk)
        form.add_error(None, "Could not save the post. Please try again.")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": False, "errors": _json_form_errors(form)}, status=500)
        selected_tag_ids = [int(x) for x in request.POST.getlist("tags") if x.isdigit()]
        return render(
            request,
            "smart_blog/create_item.html",
            {"form": form, "selected_tag_ids": selected_tag_ids},
        )

    profile_url = redirect('login_app:profile', username=request.user.username).url
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"success": True, "redirect": profile_url})
    messages.success(request, "Post created successfully.")
    return redirect(profile_url)


@login_required
def edit_item(request, slug):
    slug = (slug or '').strip()
    item = get_object_or_404(Item, slug=slug)

    if request.user != item.author:
        return HttpResponseForbidden("You are not allowed to edit this post.")

    if not item.is_editable and not request.user.is_staff:
        return HttpResponseForbidden("Editing period expired (24 hours after publication).")

    if request.method != "POST":
        form = ItemCreateForm(
            item=item,
            initial={
                "title": item.title,
                "text": item.text,
                "category": item.category_id,
                "tags": item.tags.all(),
            },
        )
        selected_tag_ids = list(item.tags.values_list("pk", flat=True))
        return render(request, "smart_blog/edit_item.html", {
            "form": form,
            "item": item,
            "existing_images": item.images.all(),
            "existing_videos": item.videos.all(),
            "selected_tag_ids": selected_tag_ids,
        })

    form = ItemCreateForm(request.POST, request.FILES, item=item)
    delete_ids = request.POST.getlist("delete_images")
    delete_video_ids = request.POST.getlist("delete_videos")

    if not form.is_valid():
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": False, "errors": _json_form_errors(form)}, status=400)
        selected_tag_ids = [int(x) for x in request.POST.getlist("tags") if x.isdigit()]
        return render(request, "smart_blog/edit_item.html", {
            "form": form,
            "item": item,
            "existing_images": item.images.all(),
            "existing_videos": item.videos.all(),
            "selected_tag_ids": selected_tag_ids,
        })

    files = request.FILES.getlist("images")
    video_files = request.FILES.getlist("videos")
    if not _image_validation_ok_edit(form, item, files, delete_ids):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": False, "errors": _json_form_errors(form)}, status=400)
        selected_tag_ids = [int(x) for x in request.POST.getlist("tags") if x.isdigit()]
        return render(request, "smart_blog/edit_item.html", {
            "form": form,
            "item": item,
            "existing_images": item.images.all(),
            "existing_videos": item.videos.all(),
            "selected_tag_ids": selected_tag_ids,
        })

    if video_files and not validate_uploaded_video_files(video_files, form):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": False, "errors": _json_form_errors(form)}, status=400)
        selected_tag_ids = [int(x) for x in request.POST.getlist("tags") if x.isdigit()]
        return render(request, "smart_blog/edit_item.html", {
            "form": form,
            "item": item,
            "existing_images": item.images.all(),
            "existing_videos": item.videos.all(),
            "selected_tag_ids": selected_tag_ids,
        })

    if video_files and not validate_edit_video_totals(item, video_files, delete_video_ids, form):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": False, "errors": _json_form_errors(form)}, status=400)
        selected_tag_ids = [int(x) for x in request.POST.getlist("tags") if x.isdigit()]
        return render(request, "smart_blog/edit_item.html", {
            "form": form,
            "item": item,
            "existing_images": item.images.all(),
            "existing_videos": item.videos.all(),
            "selected_tag_ids": selected_tag_ids,
        })

    chunked_video_ids = request.POST.getlist("chunked_video_ids")

    try:
        with transaction.atomic():
            merged_tags = merge_item_tags(form.cleaned_data)
            old_tag_ids = frozenset(item.tags.values_list("pk", flat=True))
            new_tag_ids = frozenset(t.pk for t in merged_tags)

            pin_new = form.cleaned_data.get("body_pin_file")
            body_pin_clear = bool(form.cleaned_data.get("body_pin_clear"))

            if pin_new:
                if item.body_pin_original:
                    item.body_pin_original.delete(save=False)
                item.body_pin_original = pin_new
                item.body_sourced_from_document = True
            elif body_pin_clear:
                if item.body_pin_original:
                    item.body_pin_original.delete(save=False)
                item.body_pin_original = None
                item.body_pin_content_type = BodyPinContentType.TEXT
                item.body_pin_content_html = ""
                item.body_pin_plain_snapshot = ""
                item.body_sourced_from_document = False

            if pin_new or body_pin_clear:
                item.edited = True

            item.title = form.cleaned_data["title"]
            item.text = form.cleaned_data["text"]

            new_category = form.cleaned_data.get("category")
            new_category_id = new_category.pk if new_category else None
            if item.category_id != new_category_id:
                item.edited = True

            item.category = new_category

            if old_tag_ids != new_tag_ids:
                item.edited = True

            if delete_ids or files or delete_video_ids or video_files or chunked_video_ids:
                item.edited = True

            item.save()
            item.tags.set(merged_tags)
            delete_item_images_by_ids(item, delete_ids)
            attach_item_images_from_uploads(item, files)
            delete_item_videos_by_ids(item, delete_video_ids)
            attach_item_videos_from_uploads(item, video_files)
            if chunked_video_ids:
                attach_chunked_videos(item, chunked_video_ids, request.session)
            if pin_new:
                process_item_document(item)
    except Exception:
        logger.exception("edit_item failed for item %s user %s", item.pk, request.user.pk)
        form.add_error(None, "Could not save changes. Please try again.")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": False, "errors": _json_form_errors(form)}, status=500)
        selected_tag_ids = [int(x) for x in request.POST.getlist("tags") if x.isdigit()]
        return render(request, "smart_blog/edit_item.html", {
            "form": form,
            "item": item,
            "existing_images": item.images.all(),
            "existing_videos": item.videos.all(),
            "selected_tag_ids": selected_tag_ids,
        })

    messages.success(request, "Post was successfully edited")
    redirect_url = (
        f"{item.get_absolute_url()}?{request.GET.urlencode()}" if request.GET else item.get_absolute_url()
    )
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": True, "redirect": redirect_url})
    return redirect(redirect_url)


@login_required
@require_POST
def clear_item_body_pin(request, slug):
    """Remove the post's pinned PDF/DOCX immediately (edit screen)."""
    slug = (slug or "").strip()
    item = get_object_or_404(Item, slug=slug)

    if request.user != item.author:
        return HttpResponseForbidden("You are not allowed to edit this post.")

    if not item.is_editable and not request.user.is_staff:
        return HttpResponseForbidden("Editing period expired (24 hours after publication).")

    try:
        with transaction.atomic():
            if item.body_pin_original:
                item.body_pin_original.delete(save=False)
            item.body_pin_original = None
            item.body_pin_content_type = BodyPinContentType.TEXT
            item.body_pin_content_html = ""
            item.body_pin_plain_snapshot = ""
            item.body_sourced_from_document = False
            item.edited = True
            item.save()
    except Exception:
        logger.exception(
            "clear_item_body_pin failed for item %s user %s", item.pk, request.user.pk
        )
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "error": "Could not remove file."}, status=500
            )
        messages.error(request, "Could not remove file.")
        return redirect("smart_blog:edit_post", slug=slug)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": True})

    messages.success(request, "Attached document was removed.")
    return redirect("smart_blog:edit_post", slug=slug)


@require_POST
@login_required
def delete_item_image(request, pk):
    img = get_object_or_404(ItemImage, pk=pk)
    item = img.item

    if request.user != item.author and not request.user.is_staff:
        return JsonResponse({"success": False, "error": "Permission denied."}, status=403)

    try:
        for field_name in ("image", "image_thumbnail", "image_medium"):
            try:
                field = getattr(img, field_name, None)
                if field and getattr(field, "name", None):
                    field.delete(save=False)
            except Exception:
                logger.exception("Failed to delete %s file for ItemImage %s", field_name, pk)

        img.delete()
        item.edited = True
        item.save(update_fields=["edited"])
    except Exception:
        logger.exception("Failed to delete ItemImage %s", pk)
        return JsonResponse({"success": False, "error": "Delete failed."}, status=500)

    remaining = item.images.count()
    return JsonResponse({"success": True, "image_id": pk, "remaining": remaining})


@require_POST
@login_required
def delete_item(request, slug):
    item = get_object_or_404(Item, slug=slug)

    if request.user != item.author and not request.user.is_staff:
        return HttpResponseForbidden("Permission denied.")

    if not item.is_editable and not request.user.is_staff:
        return HttpResponseForbidden("Deletion period expired.")

    item_title = item.title
    try:
        item.delete()
    except Exception:
        return HttpResponse("Delete failed", status=500)

    messages.info(request, f'Post {item_title} was deleted')
    redirect_to = request.POST.get('redirect_to') or ''
    if redirect_to and url_has_allowed_host_and_scheme(redirect_to, allowed_hosts={request.get_host()}):
        return redirect(redirect_to)

    return redirect("smart_blog:items_list")


# ---------------------------------------------------------------------------
# Chunked video upload API
# ---------------------------------------------------------------------------

def _chunk_dir_for(upload_id):
    safe_id = upload_id.replace("/", "").replace("..", "")
    return os.path.join(CHUNK_UPLOAD_DIR, safe_id)


@require_POST
@login_required
@csrf_protect
def video_chunk_upload(request):
    """Accept a single chunk of a video file.

    Frontend sends each chunk as form-data with:
      - ``chunk``      : the binary blob
      - ``upload_id``  : client-generated UUID for this upload session
      - ``chunk_index``: 0-based index
      - ``total_chunks``: total expected
      - ``filename``   : original file name
    """
    chunk = request.FILES.get("chunk")
    upload_id = request.POST.get("upload_id", "").strip()
    chunk_index = request.POST.get("chunk_index")
    total_chunks = request.POST.get("total_chunks")
    filename = request.POST.get("filename", "video.mp4").strip()

    if not chunk or not upload_id or chunk_index is None or total_chunks is None:
        return JsonResponse({"error": "Missing required fields."}, status=400)

    chunk_index = int(chunk_index)
    total_chunks = int(total_chunks)

    dest_dir = _chunk_dir_for(upload_id)
    os.makedirs(dest_dir, exist_ok=True)

    chunk_path = os.path.join(dest_dir, f"{chunk_index:05d}")
    with open(chunk_path, "wb") as fp:
        for part in chunk.chunks():
            fp.write(part)

    received = len([f for f in os.listdir(dest_dir) if f not in (".", "..", "_assembled") and not f.startswith("_")])

    if received < total_chunks:
        return JsonResponse({"status": "ok", "received": received, "total": total_chunks})

    # All chunks received — reassemble
    assembled_path = os.path.join(dest_dir, "_assembled")
    try:
        with open(assembled_path, "wb") as out:
            for i in range(total_chunks):
                cp = os.path.join(dest_dir, f"{i:05d}")
                with open(cp, "rb") as inp:
                    while True:
                        buf = inp.read(1024 * 1024)
                        if not buf:
                            break
                        out.write(buf)

        actual_size = os.path.getsize(assembled_path)
        if actual_size > MAX_VIDEO_FILE_SIZE_BYTES:
            _cleanup_chunks(dest_dir)
            return JsonResponse(
                {"error": f"Assembled file too large ({actual_size // (1024*1024)} MB)."},
                status=400,
            )

        # Store assembled file path in a session-scoped dict so the
        # create/edit view can pick it up later.
        pending = request.session.get("pending_video_uploads", {})
        pending[upload_id] = {
            "path": assembled_path,
            "filename": filename,
            "size": actual_size,
        }
        request.session["pending_video_uploads"] = pending
        request.session.modified = True

        # Cleanup individual chunks (keep assembled)
        for i in range(total_chunks):
            cp = os.path.join(dest_dir, f"{i:05d}")
            try:
                os.remove(cp)
            except OSError:
                pass

    except Exception:
        logger.exception("Failed to assemble chunked upload %s", upload_id)
        _cleanup_chunks(dest_dir)
        return JsonResponse({"error": "Assembly failed."}, status=500)

    return JsonResponse({
        "status": "complete",
        "upload_id": upload_id,
        "filename": filename,
        "size": actual_size,
    })


def _cleanup_chunks(dest_dir):
    """Remove chunk directory and all its contents."""
    try:
        import shutil
        shutil.rmtree(dest_dir, ignore_errors=True)
    except Exception:
        pass
