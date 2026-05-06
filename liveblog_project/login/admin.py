from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Profile

User = get_user_model()


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'avatar_url')
    search_fields = ('user__username', 'avatar_url')


@admin.action(description='Soft delete (is_active=False)')
def soft_delete_users(modeladmin, request, queryset):
    """Деактивировать пользователей — посты и комментарии остаются в БД."""
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f'{updated} user(s) deactivated.')


if admin.site.is_registered(User):
    admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    actions = list(BaseUserAdmin.actions) + [soft_delete_users]
