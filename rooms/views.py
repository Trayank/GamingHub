from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from rooms.models import GameRoom, PlayerSession

def home_view(request):
    if not request.session.session_key:
        request.session.create()
    return render(request, 'rooms/home.html')

def create_room_view(request):
    if not request.session.session_key:
        request.session.create()

    if request.method == 'POST':
        game_type = request.POST.get('game_type', 'LUDO')
        variant = request.POST.get('variant', '4P')
        max_players = int(request.POST.get('max_players', 4))

        room = GameRoom.objects.create(
            host_session_key=request.session.session_key,
            game_type=game_type,
            variant=variant,
            max_players=max_players,
            status='LOBBY'
        )
        return redirect('room_detail', room_code=room.code)

    return redirect('home')

def join_room_view(request):
    code = request.POST.get('room_code', '').strip().upper()
    if code and GameRoom.objects.filter(code=code).exists():
        return redirect('room_detail', room_code=code)
    return redirect('home')

def room_detail_view(request, room_code):
    if not request.session.session_key:
        request.session.create()

    room = get_object_or_404(GameRoom, code=room_code.upper())
    session_key = request.session.session_key

    # Check if user has an existing session in this room
    player_session = PlayerSession.objects.filter(room=room, session_key=session_key).first()

    context = {
        'room': room,
        'session_key': session_key,
        'reconnect_token': str(player_session.reconnect_token) if player_session else '',
        'player_name': player_session.player_name if player_session else '',
        'seat_index': player_session.seat_index if player_session else -1
    }
    return render(request, 'rooms/room.html', context)
