from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_guest', 'games_played', 'games_won', 'is_staff')
    list_filter = ('is_guest', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Gaming Profile', {'fields': ('is_guest', 'avatar_url', 'games_played', 'games_won')}),
    )
