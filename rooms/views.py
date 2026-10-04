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
    player_session = PlayerSession.objects.filter(room=room, session_key=session_key).first()

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
