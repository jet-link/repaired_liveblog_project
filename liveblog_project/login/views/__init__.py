"""login views package -- re-exports all view functions for backward compatibility."""

from login.views._helpers import (  # noqa: F401
    annotate_user_liked,
    apply_human_counts,
    build_profile_field,
    build_trust_rating_field,
)
from login.views.auth_views import login_view, register_view, logout_view  # noqa: F401
from login.views.profile_views import (  # noqa: F401
    profile_view,
    profile_online_status,
    profile_section_view,
    api_trust_status,
    profile_edit,
    remove_avatar,
)
from login.views.notification_views import (  # noqa: F401
    notifications_view,
    mark_notification_read,
    mark_all_notifications_read,
    delete_notifications,
    check_notification_target,
)
from login.views.vanished_views import (  # noqa: F401
    vanished_generic_view,
    vanished_created_view,
    user_not_found_view,
)
