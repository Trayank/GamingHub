from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from rooms.models import Room, Player
from accounts.utils import get_or_create_guest_user
from .registry import game_registry


def ensure_user(request):
    if not request.user.is_authenticated:
        guest_user = get_or_create_guest_user(request)
        from django.contrib.auth import login
        login(request, guest_user, backend='django.contrib.auth.backends.ModelBackend')
        return guest_user
    return request.user


def game_library_view(request):
    """Lists all available games registered on the platform."""
    games = game_registry.list_games()
    return render(request, 'games/library.html', {'games': games})


def game_detail_view(request, game_id):
    """Displays game details, rules, and quick play options."""
    game_info = game_registry.get_game_info(game_id)
    if not game_info:
        raise Http404("Game not found")
    return render(request, 'games/detail.html', {'game': game_info})


def tictactoe_play_view(request, room_code):
    """Renders the interactive 3x3 Tic-Tac-Toe game board UI."""
    user = ensure_user(request)
    room = get_object_or_404(Room, code=room_code.upper())
    
    player_name = getattr(user, 'display_name', user.username)
    player = Player.objects.filter(room=room, name=player_name).first()
    if not player:
        player, _ = Player.objects.get_or_create(
            room=room,
            name=player_name,
            defaults={
                'user': user if user.is_authenticated else None,
                'session_key': request.session.session_key or "",
                'slot_index': room.get_next_slot_index()
            }
        )

    return render(request, 'games/tictactoe.html', {
        'room': room,
        'player': player,
        'current_username': player_name,
    })


def trivia_play_view(request, room_code):
    """Renders the interactive Trivia Party game view."""
    user = ensure_user(request)
    room = get_object_or_404(Room, code=room_code.upper())
    
    player_name = getattr(user, 'display_name', user.username)
    player = Player.objects.filter(room=room, name=player_name).first()
    if not player:
        player, _ = Player.objects.get_or_create(
            room=room,
            name=player_name,
            defaults={
                'user': user if user.is_authenticated else None,
                'session_key': request.session.session_key or "",
                'slot_index': room.get_next_slot_index()
            }
        )

    return render(request, 'games/trivia.html', {
        'room': room,
        'player': player,
        'current_username': player_name,
    })


def ludo_play_view(request, room_code):
    """Renders the 2-10 player dynamic Ludo game board UI."""
    user = ensure_user(request)
    room = get_object_or_404(Room, code=room_code.upper())
    
    player_name = getattr(user, 'display_name', user.username)
    player = Player.objects.filter(room=room, name=player_name).first()
    if not player:
        player, _ = Player.objects.get_or_create(
            room=room,
            name=player_name,
            defaults={
                'user': user if user.is_authenticated else None,
                'session_key': request.session.session_key or "",
                'slot_index': room.get_next_slot_index()
            }
        )

    return render(request, 'games/ludo.html', {
        'room': room,
        'player': player,
        'current_username': player_name,
    })
