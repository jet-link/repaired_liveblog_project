from django.urls import path

from . import views

app_name = 'mindset'

urlpatterns = [
    path('', views.theme_list, name='theme_list'),
    path('new/', views.theme_create, name='theme_create'),
    path('theme/<int:pk>/', views.theme_detail, name='theme_detail'),
    path('tag/<slug:slug>/', views.theme_list_by_tag, name='theme_list_by_tag'),

    # API
    path('api/themes/state/', views.api_themes_state, name='api_themes_state'),
    path('api/sidebar/', views.api_sidebar, name='api_sidebar'),
    path('api/theme/<int:pk>/state/', views.api_theme_state, name='api_theme_state'),
    path('api/theme/<int:pk>/reply/', views.api_theme_reply, name='api_theme_reply'),
    path('api/theme/<int:pk>/like/', views.api_theme_like, name='api_theme_like'),
    path('api/theme/<int:pk>/repost/', views.api_theme_repost, name='api_theme_repost'),
    path('api/theme/<int:pk>/edit/', views.api_theme_edit, name='api_theme_edit'),
    path('api/theme/<int:pk>/delete/', views.api_theme_delete, name='api_theme_delete'),
    path('api/reply/<int:pk>/reply/', views.api_reply_reply, name='api_reply_reply'),
    path('api/reply/<int:pk>/like/', views.api_reply_like, name='api_reply_like'),
    path('api/reply/<int:pk>/repost/', views.api_reply_repost, name='api_reply_repost'),
    path('api/reply/<int:pk>/edit/', views.api_reply_edit, name='api_reply_edit'),
    path('api/reply/<int:pk>/delete/', views.api_reply_delete, name='api_reply_delete'),
    path('api/user/<str:username>/follow/', views.api_user_follow_toggle, name='api_user_follow_toggle'),
]
