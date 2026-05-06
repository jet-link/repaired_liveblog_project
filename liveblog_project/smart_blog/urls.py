from django.urls import include, path
from django.views.generic import RedirectView

from . import views
from . import views_for_you
from . import views_reports
from . import views_topics
from . import views_trending

app_name = "smart_blog"

# Everything that stays under the /blog/ prefix (legacy URLs → redirects + REST under /blog/).
blog_urlpatterns = [
    path(
        "brainews/",
        RedirectView.as_view(pattern_name="smart_blog:items_list", permanent=True),
    ),
    path(
        "brainews/filter/",
        RedirectView.as_view(pattern_name="smart_blog:items_filtered", permanent=True),
    ),
    path(
        "for-you/",
        RedirectView.as_view(pattern_name="smart_blog:for_you_list", permanent=True),
    ),
    path(
        "brainews/trending/",
        RedirectView.as_view(pattern_name="smart_blog:trending_list", permanent=True),
    ),
    path(
        "brainews/popular/",
        RedirectView.as_view(pattern_name="smart_blog:for_you_list", permanent=True),
        name="items_popular",
    ),
    path(
        "topics/<slug:slug>/",
        RedirectView.as_view(pattern_name="smart_blog:topic_detail", permanent=True),
    ),
    path(
        "topics/",
        RedirectView.as_view(pattern_name="smart_blog:topics_list", permanent=True),
    ),
    path(
        "tag/<slug:slug>/",
        RedirectView.as_view(pattern_name="smart_blog:tag_list", permanent=True),
    ),
    path("brainews/category/<slug:slug>/", views.category_list, name="category_list"),
    # Legacy /blog/item/... (old public paths) → /post/...
    path(
        "item/create/",
        RedirectView.as_view(pattern_name="smart_blog:create_post", permanent=True),
    ),
    path(
        "item/<slug:slug>/edit/",
        RedirectView.as_view(pattern_name="smart_blog:edit_post", permanent=True),
    ),
    path(
        "item/<slug:slug>/comments/",
        RedirectView.as_view(pattern_name="smart_blog:post_comments", permanent=True),
    ),
    path(
        "item/<slug:slug>/",
        RedirectView.as_view(pattern_name="smart_blog:post_detail", permanent=True),
    ),
    # Redirect old /blog/post/... to top-level /post/...
    path(
        "post/create/",
        RedirectView.as_view(pattern_name="smart_blog:create_post", permanent=True),
    ),
    path(
        "post/<slug:slug>/edit/",
        RedirectView.as_view(pattern_name="smart_blog:edit_post", permanent=True),
    ),
    path("post/image/<int:pk>/delete/", views.delete_item_image, name="delete_post_image"),
    path(
        "post/<slug:slug>/comments/",
        RedirectView.as_view(pattern_name="smart_blog:post_comments", permanent=True),
    ),
    path(
        "post/<slug:slug>/",
        RedirectView.as_view(pattern_name="smart_blog:post_detail", permanent=True),
    ),
    path("post/<slug:slug>/delete/", views.delete_item, name="delete_post"),
    path("post/<slug:slug>/comment/", views.add_comment, name="add_comment"),
    path("comment/<int:pk>/edit/", views.edit_comment, name="edit_comment"),
    path("comment/<int:pk>/delete/", views.delete_comment, name="delete_comment"),
    path("comment/<int:pk>/like/", views.toggle_comment_like, name="toggle_comment_like"),
    path("comment/<int:pk>/thread/", views.comment_thread_blog_redirect),
    path("post/<slug:slug>/like/", views.toggle_like, name="toggle_like"),
    path("post/<slug:slug>/bookmark/", views.toggle_bookmark, name="toggle_bookmark"),
    path("report/", views.submit_report, name="submit_report"),
    path("api/report/post/<int:pk>/", views_reports.api_report_post, name="api_report_post"),
    path("api/report/comment/<int:pk>/", views_reports.api_report_comment, name="api_report_comment"),
    path("report/post/<int:pk>/", views_reports.report_post, name="report_post"),
    path("report/comment/<int:pk>/", views_reports.report_comment, name="report_comment"),
    path("report/<int:pk>/delete/", views_reports.cancel_report, name="cancel_report"),
    path("api/post/<int:post_id>/counters/", views.post_counters, name="post_counters"),
    path("api/repost/", views.api_repost, name="api_repost"),
    path("api/search-suggest/", views.api_search_suggest, name="api_search_suggest"),
    path("api/search-history/", views.api_search_history_list, name="api_search_history_list"),
    path(
        "api/search-history/<int:pk>/clicked/",
        views.api_search_history_clicked,
        name="api_search_history_clicked",
    ),
    path("api/search-history/clear/", views.api_search_history_clear, name="api_search_history_clear"),
    path(
        "api/search-history/<int:pk>/delete/",
        views.api_search_history_delete,
        name="api_search_history_delete",
    ),
    path("api/trending/", views_trending.trending_api, name="api_trending"),
    path("api/video-chunk-upload/", views.video_chunk_upload, name="video_chunk_upload"),
]

urlpatterns = [
    path("for-you/", views_for_you.for_you_list, name="for_you_list"),
    path("trending/", views_trending.trending_list, name="trending_list"),
    path("topics/", views_topics.topics_list, name="topics_list"),
    path("topics/<slug:slug>/", views_topics.topic_detail, name="topic_detail"),
    path("tag/<slug:slug>/", views.tag_list, name="tag_list"),
    path("brainews/filter/", views.items_filtered, name="items_filtered"),
    path("brainews/", views.items_list, name="items_list"),
    path("post/create/", views.create_item, name="create_post"),
    path("post/<slug:slug>/edit/", views.edit_item, name="edit_post"),
    path(
        "post/<slug:slug>/clear-body-pin/",
        views.clear_item_body_pin,
        name="clear_body_pin",
    ),
    path("post/<slug:slug>/comments/", views.item_comments, name="post_comments"),
    path(
        "post/<slug:slug>/comment/<int:pk>/thread/",
        views.comment_thread,
        name="comment_thread",
    ),
    path("post/<slug:slug>/", views.item_detail, name="post_detail"),
    path(
        "item/create/",
        RedirectView.as_view(pattern_name="smart_blog:create_post", permanent=True),
    ),
    path(
        "item/<slug:slug>/edit/",
        RedirectView.as_view(pattern_name="smart_blog:edit_post", permanent=True),
    ),
    path(
        "item/<slug:slug>/comments/",
        RedirectView.as_view(pattern_name="smart_blog:post_comments", permanent=True),
    ),
    path(
        "item/<slug:slug>/comment/<int:pk>/thread/",
        RedirectView.as_view(pattern_name="smart_blog:comment_thread", permanent=True),
    ),
    path(
        "item/<slug:slug>/",
        RedirectView.as_view(pattern_name="smart_blog:post_detail", permanent=True),
    ),
    path("blog/", include(blog_urlpatterns)),
]
