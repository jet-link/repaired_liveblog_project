"""smart_blog views package — re-exports all view functions for backward compatibility."""

from smart_blog.feed_queryset import feed_list_optimizations  # noqa: F401
from smart_blog.views._helpers import (  # noqa: F401
    annotate_user_bookmarked,
    annotate_user_liked,
)

from smart_blog.views.listing_views import (  # noqa: F401
    items_list,
    items_filtered,
    tag_list,
    category_list,
)

from smart_blog.views.detail_views import (  # noqa: F401
    item_detail,
    item_comments,
    comment_thread,
    comment_thread_blog_redirect,
    register_item_view,
)

from smart_blog.views.comment_views import (  # noqa: F401
    add_comment,
    edit_comment,
    delete_comment,
    toggle_comment_like,
)

from smart_blog.views.item_crud_views import (  # noqa: F401
    clear_item_body_pin,
    create_item,
    edit_item,
    delete_item,
    delete_item_image,
    find_existing_media_path,
    video_chunk_upload,
)

from smart_blog.views.interaction_views import (  # noqa: F401
    toggle_like,
    toggle_bookmark,
    post_counters,
    api_repost,
)

from smart_blog.views.search_views import (  # noqa: F401
    search_view,
    api_search_suggest,
    api_search_history_list,
    api_search_history_clicked,
    api_search_history_clear,
    api_search_history_delete,
)

from smart_blog.views.report_views import submit_report  # noqa: F401
