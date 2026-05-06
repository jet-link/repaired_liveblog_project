"""Category management views."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from admin_panel.decorators import admin_required
from admin_panel.utils import redirect_preserve_query
from smart_blog.models import Category


@admin_required
def categories_list(request):
    """List categories with search."""
    qs = Category.objects.all().order_by('name')
    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(slug__icontains=search))
    paginator = Paginator(qs, 30)
    page = request.GET.get('page', 1)
    categories = paginator.get_page(page)
    return render(request, 'admin/categories/categories_list.html', {'categories': categories, 'search': search})


@admin_required
def category_create(request):
    """Create category."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        if not name:
            messages.error(request, 'Name is required.')
        elif Category.objects.filter(name__iexact=name).exists():
            messages.error(request, f'Category "{name}" already exists.')
        else:
            Category.objects.create(name=name, description=description)
            messages.success(request, 'Category created.')
            return redirect('admin_panel:categories_list')
    return render(request, 'admin/categories/category_form.html', {'is_create': True})


@admin_required
def category_edit(request, pk):
    """Edit category."""
    cat = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        cat.name = request.POST.get('name', '').strip()
        cat.description = request.POST.get('description', '').strip()
        if cat.name:
            cat.save()
            messages.success(request, 'Category updated.')
            return redirect('admin_panel:categories_list')
        messages.error(request, 'Name is required.')
    return render(request, 'admin/categories/category_form.html', {'category': cat, 'is_create': False})


@admin_required
def category_delete(request, pk):
    """Delete category."""
    cat = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        cat.soft_delete()
        messages.success(request, 'Category moved to Recent deleted.')
        return redirect_preserve_query(request, 'categories_list')
    return render(request, 'admin/categories/category_confirm_delete.html', {'category': cat})
