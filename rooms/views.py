from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Room, Player
from accounts.utils import get_or_create_guest_user
from games.registry import game_registry


def ensure_user(request):
    """Ensures request has either an authenticated user or guest session user."""
    if not request.user.is_authenticated:
        guest_user = get_or_create_guest_user(request)
        from django.contrib.auth import login
        login(request, guest_user, backend='django.contrib.auth.backends.ModelBackend')
        return guest_user
    return request.user


def lobby_view(request):
    """Renders room lobby overview or redirects to landing page."""
    return redirect('core:landing')


def create_room_view(request):
    """Generates a new room with a unique 6-character code and redirects to lobby."""
    user = ensure_user(request)
    if request.method == 'POST':
        game_type = request.POST.get('game_type', 'tic_tac_toe')
        max_players = int(request.POST.get('max_players', 2))
        is_private = request.POST.get('is_private') == 'on' or True

        room = Room.objects.create(
            host=user if user.is_authenticated else None,
            host_session_key=request.session.session_key or "",
            game_type=game_type,
            max_players=max_players,
            is_private=is_private,
            status=Room.Status.WAITING,
        )

        player_name = getattr(user, 'display_name', user.username) if user.is_authenticated else request.session.get('guest_name', 'Host')

        Player.objects.create(
            room=room,
            name=player_name,
            user=user if user.is_authenticated else None,
            session_key=request.session.session_key or "",
            is_host=True,
            is_ready=True,
            slot_index=0
        )

        return redirect('rooms:room_detail', room_code=room.code)

    return redirect('rooms:lobby')


def join_room_view(request):
    """Joins an existing room via 6-character code form."""
    user = ensure_user(request)
    if request.method == 'POST':
        room_code = request.POST.get('room_code', '').strip().upper()
        if not room_code:
            messages.error(request, "Please enter a valid 6-character room code.")
            return redirect('core:landing')

        room = Room.objects.filter(code=room_code).first()
        if not room:
            messages.error(request, f"Room with code '{room_code}' was not found.")
            return redirect('core:landing')

        if room.is_full:
            player_name = getattr(user, 'display_name', user.username)
            if not Player.objects.filter(room=room, name=player_name).exists():
                messages.error(request, f"Room '{room_code}' is currently full.")
                return redirect('core:landing')

        return redirect('rooms:room_detail', room_code=room.code)

    return redirect('core:landing')


def room_detail_view(request, room_code):
    """Renders the main Lobby UI (lobby.html)."""
    user = ensure_user(request)
    room = get_object_or_404(Room, code=room_code.upper())
    
    player_name = getattr(user, 'display_name', user.username)
    player, _ = Player.objects.get_or_create(
        room=room,
        name=player_name,
        defaults={
            'user': user if user.is_authenticated else None,
            'session_key': request.session.session_key or "",
            'is_host': (room.host == user) if user.is_authenticated else False,
            'is_ready': False,
            'slot_index': room.get_next_slot_index(),
        }
    )

    game_info = game_registry.get_game_info(room.game_type) or {
        'name': room.get_game_type_display(),
        'description': 'Multiplayer Browser Game'
    }

    return render(request, 'rooms/lobby.html', {
        'room': room,
        'player': player,
        'game_info': game_info,
        'current_username': player_name,
    })
