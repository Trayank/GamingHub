import os
import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseServerError
from django.db import OperationalError
from django.core.management import call_command
from rooms.models import GameRoom, PlayerSession

logger = logging.getLogger(__name__)

def home_view(request):
    if not request.session.session_key:
        try:
            request.session.create()
        except Exception as e:
            logger.warning(f"Session creation notice: {e}")
    return render(request, 'rooms/home.html')

def create_room_view(request):
    if not request.session.session_key:
        try:
            request.session.create()
        except Exception as e:
            logger.warning(f"Session creation notice: {e}")

    if request.method == 'POST':
        game_type = request.POST.get('game_type', 'LUDO')
        variant = request.POST.get('variant', '4P')
        try:
            max_players = int(request.POST.get('max_players', 4))
        except ValueError:
            max_players = 4

        raw_rules = request.POST.get('rules_config', '{}')
        rules_config = {}
        if raw_rules:
            try:
                rules_config = json.loads(raw_rules) if isinstance(raw_rules, str) else raw_rules
            except Exception:
                rules_config = {}

        try:
            room = GameRoom.objects.create(
                host_session_key=request.session.session_key or 'guest',
                game_type=game_type,
                variant=variant,
                max_players=max_players,
                rules_config=rules_config,
                status='LOBBY'
            )
            return redirect('room_detail', room_code=room.code)
        except OperationalError as e:
            logger.error(f"OperationalError during room creation: {e}")
            if os.getenv('VERCEL') and not os.getenv('DATABASE_URL'):
                try:
                    call_command('migrate', interactive=False)
                    room = GameRoom.objects.create(
                        host_session_key=request.session.session_key or 'guest',
                        game_type=game_type,
                        variant=variant,
                        max_players=max_players,
                        rules_config=rules_config,
                        status='LOBBY'
                    )
                    return redirect('room_detail', room_code=room.code)
                except Exception as retry_err:
                    logger.error(f"Room creation retry failed: {retry_err}")
            return HttpResponseServerError(f"Database error creating room: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in create_room_view: {e}", exc_info=True)
            return HttpResponseServerError(f"Failed to create game room: {e}")

    return redirect('home')

def join_room_view(request):
    code = request.POST.get('room_code', '').strip().upper()
    if code:
        try:
            if GameRoom.objects.filter(code=code).exists():
                return redirect('room_detail', room_code=code)
        except Exception as e:
            logger.error(f"Error checking room code: {e}")
    return redirect('home')

def room_detail_view(request, room_code):
    if not request.session.session_key:
        try:
            request.session.create()
        except Exception as e:
            logger.warning(f"Session creation notice: {e}")

    try:
        room = get_object_or_404(GameRoom, code=room_code.upper())
    except OperationalError as e:
        logger.error(f"OperationalError in room_detail_view: {e}")
        if os.getenv('VERCEL') and not os.getenv('DATABASE_URL'):
            try:
                call_command('migrate', interactive=False)
                room = get_object_or_404(GameRoom, code=room_code.upper())
            except Exception as retry_err:
                return HttpResponseServerError(f"Database error: {retry_err}")
        else:
            return HttpResponseServerError(f"Database error: {e}")

    session_key = request.session.session_key
    player_session = PlayerSession.objects.filter(room=room, session_key=session_key).first()

    context = {
        'room': room,
        'session_key': session_key,
        'reconnect_token': str(player_session.reconnect_token) if player_session else '',
        'player_name': player_session.player_name if player_session else '',
        'seat_index': player_session.seat_index if player_session else -1
    }
    return render(request, 'rooms/room.html', context)
