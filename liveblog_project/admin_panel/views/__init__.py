from .dashboard_views import dashboard_view
from .post_views import posts_list, post_edit, post_create, post_delete, post_view_stats
from .comment_views import comments_list, comment_delete, comment_confirm_draft, comment_confirm_activate
from .user_views import (
    users_list,
    user_profile,
    user_ban,
    user_unban,
    user_delete,
    banned_users_list,
    recently_deleted_list,
    deleted_users_recover,
    deleted_users_permanent_delete,
)
from .category_views import categories_list, category_create, category_edit, category_delete
from .tag_views import tags_list, tag_create, tag_edit, tag_delete
from .report_views import reports_list, report_resolve, report_dismiss, report_delete_content, report_ban_user
from .assistant_views import assistant_view, assistant_analyze, assistant_status, assistant_check_running, assistant_clear_history
from .moderation_views import (
    content_violations_list,
    content_violation_check,
    content_violation_ignore,
    content_violation_confirm_delete,
    content_violation_delete_content,
    content_violations_bulk_delete_content,
    content_violations_bulk_clear,
)
from .backup_views import backups_list, backup_status, backup_create, backup_download, backup_restore, backup_delete
from .analytics_views import analytics_view
from .sitemap_views import sitemap_stats_view
from .logs_views import logs_view
from .notification_views import (
    notification_from_admin_detail,
    notification_send_manual,
    notification_user_search,
    notifications_list,
    notifications_bulk_clear,
    notifications_bulk_delete,
)
from .recent_deleted_views import recent_deleted_content, recent_deleted_restore, recent_deleted_purge
from .faq_views import faq_list, faq_create, faq_edit, faq_delete
from .static_pages_views import about_page_edit, contacts_page_edit, home_page_edit
from .bulk_views import (
    posts_bulk_delete,
    comments_bulk_delete,
    users_bulk_delete,
    users_bulk_ban,
    banned_users_bulk_unban,
    banned_users_bulk_delete,
    deleted_logs_bulk_delete,
    tags_bulk_delete,
    categories_bulk_delete,
    reports_bulk_clear,
    reports_bulk_delete,
    faq_bulk_delete,
    backups_bulk_delete,
)

__all__ = [
    'dashboard_view', 'posts_list', 'post_edit', 'post_create', 'post_delete', 'post_view_stats',
    'comments_list', 'comment_delete', 'comment_confirm_draft', 'comment_confirm_activate',
    'users_list', 'user_profile', 'user_ban', 'user_unban', 'user_delete', 'banned_users_list', 'recently_deleted_list',
    'deleted_users_recover', 'deleted_users_permanent_delete',
    'categories_list', 'category_create', 'category_edit', 'category_delete',
    'tags_list', 'tag_create', 'tag_edit', 'tag_delete',
    'reports_list', 'report_resolve', 'report_dismiss', 'report_delete_content', 'report_ban_user',
    'assistant_view', 'assistant_analyze', 'assistant_status', 'assistant_check_running', 'assistant_clear_history',
    'content_violations_list', 'content_violation_check', 'content_violation_ignore',
    'content_violation_confirm_delete', 'content_violation_delete_content',
    'content_violations_bulk_delete_content', 'content_violations_bulk_clear',
    'backups_list', 'backup_status', 'backup_create', 'backup_download', 'backup_restore', 'backup_delete',
    'analytics_view',
    'sitemap_stats_view',
    'logs_view',
    'notifications_list', 'notifications_bulk_clear', 'notifications_bulk_delete',
    'notification_user_search', 'notification_from_admin_detail', 'notification_send_manual',
    'recent_deleted_content', 'recent_deleted_restore', 'recent_deleted_purge',
    'faq_list', 'faq_create', 'faq_edit', 'faq_delete',
    'about_page_edit', 'contacts_page_edit', 'home_page_edit',
    'posts_bulk_delete', 'comments_bulk_delete', 'users_bulk_delete', 'users_bulk_ban',
    'banned_users_bulk_unban', 'banned_users_bulk_delete', 'deleted_logs_bulk_delete', 'tags_bulk_delete', 'categories_bulk_delete',
    'reports_bulk_clear', 'reports_bulk_delete', 'faq_bulk_delete', 'backups_bulk_delete',
]
