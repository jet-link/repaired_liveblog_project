from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from smart_blog.services.for_you_recommendations import for_you_items_for_authenticated_user
from smart_blog.utils import breadcrumb, build_breadcrumbs
from smart_blog.views._helpers import annotate_feed_page_items

LIST_PER_PAGE = 40


@login_required
def for_you_list(request):
    result = for_you_items_for_authenticated_user(request.user)

    paginator = Paginator(result.items, LIST_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    page_range = paginator.get_elided_page_range(
        number=page_obj.number,
        on_each_side=1,
        on_ends=1,
    )

    items = annotate_feed_page_items(request.user, page_obj)

    breadcrumbs = build_breadcrumbs(
        breadcrumb("For you", None),
    )

    return render(
        request,
        "smart_blog/for_you_list.html",
        {
            "page_obj": page_obj,
            "page_range": page_range,
            "items": items,
            "low_personal_signal": result.low_personal_signal,
            "breadcrumbs": breadcrumbs,
        },
    )
