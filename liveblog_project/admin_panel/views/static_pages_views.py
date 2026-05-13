"""Edit public About / Contacts page copy (superuser only)."""
from django.contrib import messages
from django.shortcuts import redirect, render

from admin_panel.decorators import admin_required
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


