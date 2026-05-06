"""FAQ management views."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from admin_panel.decorators import admin_required
from admin_panel.utils import redirect_preserve_query
from pages.models import FAQItem


@admin_required
def faq_list(request):
    """List FAQ items with search."""
    qs = FAQItem.objects.all().order_by('order', 'pk')
    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(Q(question__icontains=search) | Q(answer__icontains=search))
    paginator = Paginator(qs, 30)
    page = request.GET.get('page', 1)
    items = paginator.get_page(page)
    return render(request, 'admin/faq/faq_list.html', {'items': items, 'search': search})


@admin_required
def faq_create(request):
    """Create FAQ item."""
    if request.method == 'POST':
        question = request.POST.get('question', '').strip()
        answer = request.POST.get('answer', '').strip()
        order = request.POST.get('order', '0')
        if question and answer:
            try:
                order = int(order)
            except ValueError:
                order = 0
            is_active = request.POST.get('is_active') == 'on'
            FAQItem.objects.create(question=question, answer=answer, order=order, is_active=is_active)
            messages.success(request, 'FAQ item created.')
            return redirect('admin_panel:faq_list')
        messages.error(request, 'Question and answer are required.')
    return render(request, 'admin/faq/faq_form.html', {'is_create': True})


@admin_required
def faq_edit(request, pk):
    """Edit FAQ item."""
    item = get_object_or_404(FAQItem, pk=pk)
    if request.method == 'POST':
        item.question = request.POST.get('question', '').strip()
        item.answer = request.POST.get('answer', '').strip()
        try:
            item.order = int(request.POST.get('order', '0'))
        except ValueError:
            pass
        if item.question and item.answer:
            item.is_active = request.POST.get('is_active') == 'on'
            item.save()
            messages.success(request, 'FAQ item updated.')
            return redirect('admin_panel:faq_list')
        messages.error(request, 'Question and answer are required.')
    return render(request, 'admin/faq/faq_form.html', {'item': item, 'is_create': False})


@admin_required
def faq_delete(request, pk):
    """Delete FAQ item."""
    item = get_object_or_404(FAQItem, pk=pk)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'FAQ item deleted.')
        return redirect_preserve_query(request, 'faq_list')
    return render(request, 'admin/faq/faq_confirm_delete.html', {'item': item})
