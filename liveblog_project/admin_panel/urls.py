"""Admin panel URL configuration."""
from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),

    # Posts
    path('posts/', views.posts_list, name='posts_list'),
    path('posts/create/', views.post_create, name='post_create'),
    path('posts/<int:pk>/edit/', views.post_edit, name='post_edit'),
    path('posts/<int:pk>/delete/', views.post_delete, name='post_delete'),
    path('posts/bulk-delete/', views.posts_bulk_delete, name='posts_bulk_delete'),
    path('posts/<int:pk>/stats/', views.post_view_stats, name='post_stats'),

    # Comments
    path('comments/', views.comments_list, name='comments_list'),
    path('comments/<int:pk>/delete/', views.comment_delete, name='comment_delete'),
    path('comments/bulk-delete/', views.comments_bulk_delete, name='comments_bulk_delete'),
    path('comments/<int:pk>/draft/', views.comment_confirm_draft, name='comment_confirm_draft'),
    path('comments/<int:pk>/activate/', views.comment_confirm_activate, name='comment_confirm_activate'),

    # Users
    path('users/', views.users_list, name='users_list'),
    path('users/banned/', views.banned_users_list, name='banned_users'),
    path('users/recently-deleted/', views.recently_deleted_list, name='recently_deleted'),
    path('users/recently-deleted/recover/', views.deleted_users_recover, name='deleted_users_recover'),
    path('users/recently-deleted/purge/', views.deleted_users_permanent_delete, name='deleted_users_permanent_delete'),
    path('users/recently-deleted/bulk-delete/', views.deleted_logs_bulk_delete, name='deleted_logs_bulk_delete'),
    path('users/<int:pk>/', views.user_profile, name='user_profile'),
    path('users/<int:pk>/ban/', views.user_ban, name='user_ban'),
    path('users/<int:pk>/unban/', views.user_unban, name='user_unban'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('users/bulk-delete/', views.users_bulk_delete, name='users_bulk_delete'),
    path('users/bulk-ban/', views.users_bulk_ban, name='users_bulk_ban'),
    path('users/banned/bulk-unban/', views.banned_users_bulk_unban, name='banned_users_bulk_unban'),
    path('users/banned/bulk-delete/', views.banned_users_bulk_delete, name='banned_users_bulk_delete'),

    # Categories
    path('categories/', views.categories_list, name='categories_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('categories/bulk-delete/', views.categories_bulk_delete, name='categories_bulk_delete'),

    # Tags
    path('tags/', views.tags_list, name='tags_list'),
    path('tags/create/', views.tag_create, name='tag_create'),
    path('tags/<int:pk>/edit/', views.tag_edit, name='tag_edit'),
    path('tags/<int:pk>/delete/', views.tag_delete, name='tag_delete'),
    path('tags/bulk-delete/', views.tags_bulk_delete, name='tags_bulk_delete'),

    # Moderation: Assistant & Content Violations
    path('assistant/', views.assistant_view, name='assistant'),
    path('assistant/analyze/', views.assistant_analyze, name='assistant_analyze'),
    path('assistant/status/<int:pk>/', views.assistant_status, name='assistant_status'),
    path('assistant/check-running/', views.assistant_check_running, name='assistant_check_running'),
    path('assistant/clear-history/', views.assistant_clear_history, name='assistant_clear_history'),
    path('content-violations/', views.content_violations_list, name='content_violations_list'),
    path('content-violations/<int:pk>/check/', views.content_violation_check, name='content_violation_check'),
    path('content-violations/<int:pk>/ignore/', views.content_violation_ignore, name='content_violation_ignore'),
    path('content-violations/<int:pk>/confirm-delete/', views.content_violation_confirm_delete, name='content_violation_confirm_delete'),
    path('content-violations/<int:pk>/delete-content/', views.content_violation_delete_content, name='content_violation_delete_content'),
    path('content-violations/bulk-delete-content/', views.content_violations_bulk_delete_content, name='content_violations_bulk_delete_content'),
    path('content-violations/bulk-clear/', views.content_violations_bulk_clear, name='content_violations_bulk_clear'),

    path('moderation/notifications/', views.notifications_list, name='notifications_list'),
    path('moderation/notifications/bulk-clear/', views.notifications_bulk_clear, name='notifications_bulk_clear'),
    path('moderation/notifications/bulk-delete/', views.notifications_bulk_delete, name='notifications_bulk_delete'),
    path('moderation/notifications/user-search/', views.notification_user_search, name='notification_user_search'),
    path('moderation/notifications/<int:pk>/from-admin-detail/', views.notification_from_admin_detail, name='notification_from_admin_detail'),
    path('moderation/notifications/send-manual/', views.notification_send_manual, name='notification_send_manual'),

    # Reports
    path('reports/', views.reports_list, name='reports_list'),
    path('reports/<int:pk>/resolve/', views.report_resolve, name='report_resolve'),
    path('reports/<int:pk>/dismiss/', views.report_dismiss, name='report_dismiss'),
    path('reports/<int:pk>/delete-content/', views.report_delete_content, name='report_delete_content'),
    path('reports/bulk-clear/', views.reports_bulk_clear, name='reports_bulk_clear'),
    path('reports/bulk-delete/', views.reports_bulk_delete, name='reports_bulk_delete'),
    path('reports/<int:pk>/ban-user/', views.report_ban_user, name='report_ban_user'),

    # Analytics
    path('analytics/', views.analytics_view, name='analytics'),
    path('analytics/sitemap/', views.sitemap_stats_view, name='sitemap_stats'),

    path('system/recent-deleted/', views.recent_deleted_content, name='recent_deleted_content'),
    path('system/recent-deleted/restore/', views.recent_deleted_restore, name='recent_deleted_restore'),
    path('system/recent-deleted/purge/', views.recent_deleted_purge, name='recent_deleted_purge'),

    # Backups
    path('backups/', views.backups_list, name='backups_list'),
    path('backups/status/', views.backup_status, name='backup_status'),
    path('backups/create/', views.backup_create, name='backup_create'),
    path('backups/<int:pk>/download/', views.backup_download, name='backup_download'),
    path('backups/<int:pk>/restore/', views.backup_restore, name='backup_restore'),
    path('backups/<int:pk>/delete/', views.backup_delete, name='backup_delete'),
    path('backups/bulk-delete/', views.backups_bulk_delete, name='backups_bulk_delete'),

    # Logs (placeholder)
    path('logs/', views.logs_view, name='logs'),

    # Pages / FAQ / static site pages
    path('pages/about/', views.about_page_edit, name='about_page_edit'),
    path('pages/home/', views.home_page_edit, name='home_page_edit'),
    path('pages/contacts/', views.contacts_page_edit, name='contacts_page_edit'),
    path('faq/', views.faq_list, name='faq_list'),
    path('faq/create/', views.faq_create, name='faq_create'),
    path('faq/<int:pk>/edit/', views.faq_edit, name='faq_edit'),
    path('faq/<int:pk>/delete/', views.faq_delete, name='faq_delete'),
    path('faq/bulk-delete/', views.faq_bulk_delete, name='faq_bulk_delete'),
]
