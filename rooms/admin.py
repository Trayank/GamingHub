from django.contrib import admin
from .models import Room, Player


class PlayerInline(admin.TabularInline):
    model = Player
    extra = 0


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('code', 'game_type', 'host', 'status', 'is_private', 'player_count', 'created_at')
    list_filter = ('status', 'game_type', 'is_private')
    search_fields = ('code', 'host__username')
    inlines = [PlayerInline]


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'room', 'slot_index', 'is_host', 'is_ready', 'joined_at')
    list_filter = ('is_host', 'is_ready')
    search_fields = ('name', 'room__code')
