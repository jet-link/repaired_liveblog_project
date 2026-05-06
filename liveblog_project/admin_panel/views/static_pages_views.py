"""Edit public About / Contacts / Home page copy (superuser only)."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from admin_panel.decorators import admin_required
from pages.models import HomePageContent, HomeQuickLink
from pages.home_content import get_home_page
from pages.static_pages import get_about_page, get_contacts_page


def _superuser_or_dashboard(request):
    if not request.user.is_superuser:
        return redirect('admin_panel:dashboard')
    return None


@admin_required
def about_page_edit(request):
    redir = _superuser_or_dashboard(request)
    if redir:
        return redir
    page = get_about_page()
    if request.method == 'POST':
        page.browser_title = request.POST.get('browser_title', '').strip()[:120]
        page.title_h1 = request.POST.get('title_h1', '').strip()[:200]
        page.lede = request.POST.get('lede', '').strip()
        page.mission_heading = request.POST.get('mission_heading', '').strip()[:200]
        page.mission_item_1 = request.POST.get('mission_item_1', '').strip()
        page.mission_item_2 = request.POST.get('mission_item_2', '').strip()
        page.mission_item_3 = request.POST.get('mission_item_3', '').strip()
        page.facts_heading_hidden = request.POST.get('facts_heading_hidden', '').strip()[:120]
        page.fact1_label = request.POST.get('fact1_label', '').strip()[:120]
        page.fact1_value = request.POST.get('fact1_value', '').strip()
        page.fact2_label = request.POST.get('fact2_label', '').strip()[:120]
        page.fact2_value = request.POST.get('fact2_value', '').strip()
        page.fact3_label = request.POST.get('fact3_label', '').strip()[:120]
        page.fact3_value = request.POST.get('fact3_value', '').strip()
        page.cta_link_text = request.POST.get('cta_link_text', '').strip()[:120]
        page.cta_hint = request.POST.get('cta_hint', '').strip()[:255]
        page.updated_by = request.user
        page.save()
        messages.success(request, 'About page saved.')
        return redirect('admin_panel:about_page_edit')
    return render(request, 'admin/pages/about_page_edit.html', {'page': page})


@admin_required
def contacts_page_edit(request):
    redir = _superuser_or_dashboard(request)
    if redir:
        return redir
    page = get_contacts_page()
    if request.method == 'POST':
        page.browser_title = request.POST.get('browser_title', '').strip()[:120]
        page.title_h1 = request.POST.get('title_h1', '').strip()[:200]
        page.lede_before = request.POST.get('lede_before', '').strip()[:255]
        page.lede_emphasis = request.POST.get('lede_emphasis', '').strip()[:120]
        page.lede_after = request.POST.get('lede_after', '').strip()
        page.channels_heading = request.POST.get('channels_heading', '').strip()[:200]
        page.email_key = request.POST.get('email_key', '').strip()[:120]
        page.email_address = request.POST.get('email_address', '').strip()[:255]
        page.email_note = request.POST.get('email_note', '').strip()[:255]
        page.community_key = request.POST.get('community_key', '').strip()[:120]
        page.community_text = request.POST.get('community_text', '').strip()
        page.no_section_heading = request.POST.get('no_section_heading', '').strip()[:200]
        page.no_section_body = request.POST.get('no_section_body', '').strip()
        page.footer_about_link_text = request.POST.get('footer_about_link_text', '').strip()[:120]
        page.updated_by = request.user
        page.save()
        messages.success(request, 'Contacts page saved.')
        return redirect('admin_panel:contacts_page_edit')
    return render(request, 'admin/pages/contacts_page_edit.html', {'page': page})


def _parse_item_pk(raw):
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return int(str(raw).strip())
    except ValueError:
        return None


@admin_required
def home_page_edit(request):
    redir = _superuser_or_dashboard(request)
    if redir:
        return redir

    home = get_home_page()
    quick_links = list(HomeQuickLink.objects.all().order_by("order", "pk"))

    if request.method == "POST":
        form_type = request.POST.get("form_type", "home")

        if form_type == "quicklink_delete":
            pk = request.POST.get("ql_id")
            try:
                HomeQuickLink.objects.filter(pk=int(pk)).delete()
                messages.success(request, "Quick link removed.")
            except (TypeError, ValueError):
                messages.error(request, "Invalid quick link.")
            return redirect("admin_panel:home_page_edit")

        if form_type == "quicklink_save":
            pk = request.POST.get("ql_id")
            try:
                ql = HomeQuickLink.objects.get(pk=int(pk))
                ql.label = request.POST.get("label", "").strip()[:120]
                ql.url = request.POST.get("url", "").strip()[:500]
                ql.icon_class = request.POST.get("icon_class", "").strip()[:80]
                ql.order = int(request.POST.get("order", 0) or 0)
                ql.is_active = request.POST.get("is_active") == "on"
                ql.save()
                messages.success(request, "Quick link saved.")
            except (TypeError, ValueError, HomeQuickLink.DoesNotExist):
                messages.error(request, "Could not save quick link.")
            return redirect("admin_panel:home_page_edit")

        if form_type == "quicklink_add":
            label = request.POST.get("new_label", "").strip()[:120]
            url = request.POST.get("new_url", "").strip()[:500]
            if label and url:
                HomeQuickLink.objects.create(
                    label=label,
                    url=url,
                    icon_class=request.POST.get("new_icon_class", "").strip()[:80],
                    order=int(request.POST.get("new_order", 0) or 0),
                    is_active=request.POST.get("new_is_active") == "on",
                )
                messages.success(request, "Quick link added.")
            else:
                messages.error(request, "Label and URL are required for a new quick link.")
            return redirect("admin_panel:home_page_edit")

        # Main home content form
        home.browser_title = request.POST.get("browser_title", "").strip()[:120]
        home.meta_description = request.POST.get("meta_description", "").strip()[:320]
        home.hero_h1 = request.POST.get("hero_h1", "").strip()[:200]
        home.hero_lede = request.POST.get("hero_lede", "").strip()
        home.cta_primary_label = request.POST.get("cta_primary_label", "").strip()[:120]
        home.cta_primary_url = request.POST.get("cta_primary_url", "").strip()[:500]
        home.cta_secondary_label = request.POST.get("cta_secondary_label", "").strip()[:120]
        home.cta_secondary_url = request.POST.get("cta_secondary_url", "").strip()[:500]
        home.trust_line = request.POST.get("trust_line", "").strip()[:255]
        home.trust_link_url = request.POST.get("trust_link_url", "").strip()[:500]
        home.show_quick_links = request.POST.get("show_quick_links") == "on"
        home.show_decorative_astronauts = request.POST.get("show_decorative_astronauts") == "on"
        home.content_strip_mode = request.POST.get("content_strip_mode", HomePageContent.STRIP_POPULAR)
        if home.content_strip_mode not in dict(HomePageContent.STRIP_CHOICES):
            home.content_strip_mode = HomePageContent.STRIP_POPULAR
        try:
            home.content_strip_limit = int(request.POST.get("content_strip_limit", 6) or 6)
        except ValueError:
            home.content_strip_limit = 6
        try:
            home.popular_min_likes = int(request.POST.get("popular_min_likes", 6) or 6)
        except ValueError:
            home.popular_min_likes = 6
        home.show_editor_picks = request.POST.get("show_editor_picks") == "on"
        home.editor_pick_order_after_strip = request.POST.get("editor_pick_order_after_strip") == "on"
        home.show_in_trend = request.POST.get("show_in_trend") == "on"
        home.show_for_you_section = request.POST.get("show_for_you_section") == "on"
        home.show_explore_topics = request.POST.get("show_explore_topics") == "on"
        home.show_latest_brainews = request.POST.get("show_latest_brainews") == "on"
        home.show_bottom_cta = request.POST.get("show_bottom_cta") == "on"
        home.cta_footer_title = request.POST.get("cta_footer_title", "").strip()
        home.cta_footer_label = request.POST.get("cta_footer_label", "").strip()[:120]
        home.cta_footer_url = request.POST.get("cta_footer_url", "").strip()[:500]

        hero_feat = _parse_item_pk(request.POST.get("hero_featured_item"))
        home.hero_featured_item_id = hero_feat

        p1 = _parse_item_pk(request.POST.get("editor_pick_1"))
        p2 = _parse_item_pk(request.POST.get("editor_pick_2"))
        p3 = _parse_item_pk(request.POST.get("editor_pick_3"))
        home.editor_pick_1_id = p1
        home.editor_pick_2_id = p2
        home.editor_pick_3_id = p3

        home.updated_by = request.user
        try:
            home.full_clean()
        except ValidationError as e:
            if hasattr(e, "error_dict") and e.error_dict:
                first_errs = next(iter(e.error_dict.values()))
                messages.error(request, first_errs[0])
            else:
                messages.error(request, e.messages[0] if e.messages else str(e))
            return redirect("admin_panel:home_page_edit")
        home.save()
        messages.success(request, "Home page saved.")
        return redirect("admin_panel:home_page_edit")

    return render(
        request,
        "admin/pages/home_page_edit.html",
        {"page": home, "quick_links": quick_links, "strip_choices": HomePageContent.STRIP_CHOICES},
    )
