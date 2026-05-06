from django.urls import path
from . import views

app_name = "login_app"

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('profile/me/trust-status/', views.api_trust_status, name='api_trust_status'),
    path('profile/vanished/', views.vanished_generic_view, name='vanished'),
    path('profile/vanished/created/', views.vanished_created_view, name='vanished-created'),
    path('profile/edit/<str:username>/', views.profile_edit, name='profile-edit'),
    path('profile/remove-avatar/', views.remove_avatar, name='remove_avatar'),
    path("profile/notifications/read/", views.mark_notification_read, name="notification_read"),
    path("profile/notifications/read-all/", views.mark_all_notifications_read, name="notifications_read_all"),
    path("profile/notifications/delete/", views.delete_notifications, name="notifications_delete"),
    path("profile/notifications/check-target/", views.check_notification_target, name="notification_check_target"),
    path('profile/<str:username>/notifications/', views.notifications_view, name='notifications'),
    path('profile/<str:username>/online/', views.profile_online_status, name='profile-online-status'),
    path('profile/<str:username>/<str:section>/', views.profile_section_view, name='profile-section'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
]