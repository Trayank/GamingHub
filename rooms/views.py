import os
import json
import uuid
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseServerError
from django.db import OperationalError, ProgrammingError
from django.core.management import call_command
from django.views.decorators.cache import never_cache
from rooms.models import GameRoom, PlayerSession, PlayerProfile, AVATAR_PRESETS

logger = logging.getLogger(__name__)

def get_or_create_profile(request):
    # Ensure session exists and generate a persistent UUID for this visitor
    player_uuid = request.session.get('player_uuid')
    if not player_uuid:
        player_uuid = str(uuid.uuid4())
        request.session['player_uuid'] = player_uuid
        request.session.modified = True

    try:
        # Clean up legacy orphaned profiles with empty or generic keys
        PlayerProfile.objects.filter(session_key__in=['guest_session', 'None', '', None]).delete()
    except Exception:
        pass

    try:
        profile, created = PlayerProfile.objects.get_or_create(
            session_key=player_uuid,
            defaults={
                'display_name': f"Player_{player_uuid[:4].upper()}",
                'avatar': 'wizard'
            }
        )
        return profile
    except (OperationalError, ProgrammingError) as e:
        logger.warning(f"PlayerProfile database table missing ({e}). Executing auto-migration fallback...")
        try:
            call_command('migrate', interactive=False)
            profile, created = PlayerProfile.objects.get_or_create(
                session_key=player_uuid,
                defaults={
                    'display_name': f"Player_{player_uuid[:4].upper()}",
                    'avatar': 'wizard'
                }
            )
            return profile
        except Exception as retry_err:
            logger.error(f"Failed auto-migration or profile retrieval: {retry_err}")
            return PlayerProfile(session_key=player_uuid, display_name=f"Player_{player_uuid[:4].upper()}", avatar="wizard")

@never_cache
def home_view(request):
    profile = get_or_create_profile(request)
    context = {
        'profile': profile,
        'avatar_presets': AVATAR_PRESETS
    }
    return render(request, 'rooms/home.html', context)

@never_cache
def update_profile_view(request):
    if request.method == 'POST':
        profile = get_or_create_profile(request)
        display_name = request.POST.get('display_name', '').strip()
        avatar = request.POST.get('avatar', '').strip()

        if display_name:
            profile.display_name = display_name
        if avatar and avatar in AVATAR_PRESETS:
            profile.avatar = avatar
        profile.save()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'ok',
                'display_name': profile.display_name,
                'avatar': profile.avatar,
                'avatar_emoji': profile.avatar_emoji,
                'win_rate': profile.win_rate,
                'rating_elo': profile.rating_elo
            })
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    return redirect('home')

@never_cache
def create_room_view(request):
    profile = get_or_create_profile(request)

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
                host_session_key=profile.session_key,
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
                        host_session_key=profile.session_key,
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

@never_cache
def join_room_view(request):
    code = request.POST.get('room_code', '').strip().upper()
    if code:
        try:
            if GameRoom.objects.filter(code=code).exists():
                return redirect('room_detail', room_code=code)
        except Exception as e:
            logger.error(f"Error checking room code: {e}")
    return redirect('home')

@never_cache
def room_detail_view(request, room_code):
    profile = get_or_create_profile(request)

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

    session_key = profile.session_key
    if not room.host_session_key:
        room.host_session_key = session_key
        room.save()

    is_host = (session_key == room.host_session_key)

    player_session = PlayerSession.objects.filter(room=room, session_key=session_key).first()
    if not player_session:
        existing_seats = set(room.players.values_list('seat_index', flat=True))
        seat_index = 0
        for i in range(room.max_players):
            if i not in existing_seats:
                seat_index = i
                break
        colors = ['red', 'blue', 'yellow', 'green', 'purple', 'orange', 'cyan', 'pink']
        color = colors[seat_index % len(colors)]
        player_session = PlayerSession.objects.create(
            room=room,
            session_key=session_key,
            player_name=profile.display_name,
            seat_index=seat_index,
            color=color,
            is_host=is_host,
            is_ready=is_host,
            is_connected=True
        )
    else:
        player_session.is_connected = True
        player_session.is_host = is_host
        player_session.save()

    context = {
        'room': room,
        'profile': profile,
        'avatar_presets': AVATAR_PRESETS,
        'session_key': session_key,
        'reconnect_token': str(player_session.reconnect_token) if player_session else '',
        'player_name': player_session.player_name if player_session else profile.display_name,
        'seat_index': player_session.seat_index if player_session else -1
    }
    return render(request, 'rooms/room.html', context)

from django.views.decorators.csrf import csrf_exempt

@never_cache
def room_status_api(request, room_code):
    profile = get_or_create_profile(request)
    try:
        room = get_object_or_404(GameRoom, code=room_code.upper())
        player_uuid = profile.session_key
        is_current_user_host = (player_uuid == room.host_session_key)

        players_list = list(room.players.all().order_by('seat_index'))
        players_data = []
        for p in players_list:
            prof = PlayerProfile.objects.filter(session_key=p.session_key).first()
            avatar = prof.avatar if prof else 'wizard'
            players_data.append({
                "session_key": p.session_key,
                "name": p.player_name,
                "avatar": avatar,
                "is_ready": p.is_ready,
                "is_host": p.is_host
            })

        can_start = (len(players_data) >= 2) and all(p["is_ready"] for p in players_data)
        status_str = "in_progress" if room.status in ['PLAYING', 'in_progress'] else "waiting"
        game_url = f"/room/{room.code}/"

        return JsonResponse({
            "status": status_str,
            "game_type": room.game_type.lower(),
            "variant": room.variant.lower(),
            "is_current_user_host": is_current_user_host,
            "player_count": len(players_data),
            "max_players": room.max_players,
            "players": players_data,
            "can_start": can_start,
            "game_url": game_url
        })
    except Exception as e:
        logger.error(f"Error in room_status_api: {e}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@never_cache
def toggle_ready_api(request, room_code):
    profile = get_or_create_profile(request)
    try:
        room = get_object_or_404(GameRoom, code=room_code.upper())
        player_session = PlayerSession.objects.filter(room=room, session_key=profile.session_key).first()
        if player_session:
            player_session.is_ready = not player_session.is_ready
            player_session.save()
            return JsonResponse({'status': 'ok', 'is_ready': player_session.is_ready})
        return JsonResponse({'status': 'error', 'message': 'Player session not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in toggle_ready_api: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@never_cache
def start_game_api(request, room_code):
    profile = get_or_create_profile(request)
    try:
        room = get_object_or_404(GameRoom, code=room_code.upper())
        if profile.session_key != room.host_session_key:
            return JsonResponse({'success': False, 'error': 'Only host can start the game'}, status=403)

        room.status = 'PLAYING'
        if not room.state_data:
            from games.registry import get_game_engine
            engine = get_game_engine(room.game_type)
            if engine:
                seats_info = [
                    {'name': p.player_name, 'color': p.color}
                    for p in room.players.all().order_by('seat_index')
                ]
                room.state_data = engine.initialize_state(
                    player_count=room.players.count(),
                    variant=room.variant,
                    seats_info=seats_info
                )
        room.save()
        redirect_url = f"/room/{room.code}/"
        return JsonResponse({'success': True, 'redirect_url': redirect_url})
    except Exception as e:
        logger.error(f"Error in start_game_api: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
