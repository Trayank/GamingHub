import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from rooms.models import GameRoom, PlayerSession, MatchHistory
from games.registry import get_game_engine

logger = logging.getLogger(__name__)

class RoomConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f"room_{self.room_code}"

        # Join room channel group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Parse query params for reconnect_token
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        params = dict(qp.split('=') for qp in query_string.split('&') if '=' in qp)
        reconnect_token = params.get('reconnect_token')

        session_key = self.scope.get('session', {}).session_key

        self.player_session = await self.get_or_create_player(self.room_code, session_key, reconnect_token)

        if not self.player_session:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Room is full or does not exist.'
            }))
            await self.close()
            return

        # Mark player as connected
        await self.set_player_connected(self.player_session.id, True)

        # Broadcast updated lobby/game state to room
        await self.broadcast_room_state()

    async def disconnect(self, close_code):
        if hasattr(self, 'player_session') and self.player_session:
            await self.set_player_connected(self.player_session.id, False)

            # Leave group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

            # Notify room of disconnect with grace period info
            await self.broadcast_room_state()

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except Exception:
            await self.send_error("Invalid JSON format.")
            return

        action = data.get('action')
        payload = data.get('payload', {})

        if action == 'select_seat':
            await self.handle_select_seat(payload)
        elif action == 'toggle_ready':
            await self.handle_toggle_ready()
        elif action == 'start_game':
            await self.handle_start_game()
        elif action == 'kick_player':
            await self.handle_kick_player(payload)
        elif action == 'change_settings':
            await self.handle_change_settings(payload)
        elif action == 'game_action':
            await self.handle_game_action(payload)
        elif action == 'reconnect_claim':
            await self.handle_reconnect_claim(payload)
        else:
            await self.send_error(f"Unknown action: {action}")

    async def handle_select_seat(self, payload):
        target_seat = payload.get('seat_index')
        chosen_color = payload.get('color')

        success, msg = await self.update_player_seat(self.player_session.id, target_seat, chosen_color)
        if success:
            await self.broadcast_room_state()
        else:
            await self.send_error(msg)

    async def handle_toggle_ready(self):
        await self.toggle_player_ready(self.player_session.id)
        await self.broadcast_room_state()

    async def handle_start_game(self):
        room = await self.get_room(self.room_code)
        if not room:
            await self.send_error("Room not found.")
            return

        player = await self.get_player(self.player_session.id)
        if not player.is_host:
            await self.send_error("Only host can start the game.")
            return

        # Check all players ready
        can_start, msg = await self.check_can_start_game(room.id)
        if not can_start:
            await self.send_error(msg)
            return

        # Initialize game engine state
        engine = get_game_engine(room.game_type)
        if not engine:
            await self.send_error("Game engine not found.")
            return

        seats_info = await self.get_seats_info(room.id)
        initial_state = engine.initialize_state(len(seats_info), room.variant, seats_info)

        await self.update_room_game_started(room.id, initial_state)
        await self.broadcast_room_state()

    async def handle_game_action(self, payload):
        room = await self.get_room(self.room_code)
        if not room or room.status != 'PLAYING':
            await self.send_error("Game is not in progress.")
            return

        engine = get_game_engine(room.game_type)
        if not engine:
            await self.send_error("Engine error.")
            return

        player = await self.get_player(self.player_session.id)
        state_data = room.state_data

        new_state, is_valid, err_msg = engine.apply_action(state_data, player.seat_index, payload)

        if not is_valid:
            await self.send_error(err_msg)
            return

        # Save updated state
        win_info = engine.check_win_condition(new_state)
        new_status = 'FINISHED' if win_info else 'PLAYING'

        await self.update_room_state(room.id, new_state, new_status)

        if new_status == 'FINISHED':
            await self.record_match_history(room.id, new_state)

        await self.broadcast_room_state()

    async def handle_kick_player(self, payload):
        player = await self.get_player(self.player_session.id)
        if not player.is_host:
            await self.send_error("Only host can kick players.")
            return

        target_seat = payload.get('seat_index')
        await self.delete_player_by_seat(self.room_code, target_seat)
        await self.broadcast_room_state()

    async def handle_change_settings(self, payload):
        player = await self.get_player(self.player_session.id)
        if not player.is_host:
            await self.send_error("Only host can change settings.")
            return

        await self.update_room_settings(self.room_code, payload)
        await self.broadcast_room_state()

    async def handle_reconnect_claim(self, payload):
        token = payload.get('reconnect_token')
        if token:
            reclaimed_session = await self.reclaim_seat_by_token(self.room_code, token)
            if reclaimed_session:
                self.player_session = reclaimed_session
                await self.set_player_connected(self.player_session.id, True)
                await self.send(json.dumps({
                    'type': 'reconnect_success',
                    'player_name': self.player_session.player_name,
                    'seat_index': self.player_session.seat_index
                }))
                await self.broadcast_room_state()
            else:
                await self.send_error("Invalid reconnect token.")

    async def broadcast_room_state(self):
        room_payload = await self.get_full_room_payload(self.room_code)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'room_state_update',
                'payload': room_payload
            }
        )

    async def room_state_update(self, event):
        payload = dict(event['payload'])
        # Tailor valid moves specifically for this client's seat
        if payload.get('status') == 'PLAYING' and hasattr(self, 'player_session') and self.player_session:
            room = await self.get_room(self.room_code)
            engine = get_game_engine(room.game_type)
            if engine:
                client_valid = engine.get_valid_moves(room.state_data, self.player_session.seat_index)
                payload['client_seat_index'] = self.player_session.seat_index
                payload['client_valid_moves'] = client_valid
                payload['reconnect_token'] = str(self.player_session.reconnect_token)

        await self.send(text_data=json.dumps({
            'type': 'room_state',
            'data': payload
        }))

    async def send_error(self, message):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))

    # DATABASE HELPERS (sync_to_async)

    @database_sync_to_async
    def get_room(self, code):
        return GameRoom.objects.filter(code=code).first()

    @database_sync_to_async
    def get_player(self, player_id):
        return PlayerSession.objects.filter(id=player_id).first()

    @database_sync_to_async
    def get_or_create_player(self, room_code, session_key, reconnect_token):
        room = GameRoom.objects.filter(code=room_code).first()
        if not room:
            return None

        # Check existing token match
        if reconnect_token:
            session = PlayerSession.objects.filter(room=room, reconnect_token=reconnect_token).first()
            if session:
                return session

        # Check existing session key match
        if session_key:
            session = PlayerSession.objects.filter(room=room, session_key=session_key).first()
            if session:
                return session

        if room.status != 'LOBBY':
            return None

        # Assign next free seat
        existing_seats = set(PlayerSession.objects.filter(room=room).values_list('seat_index', flat=True))
        free_seat = None
        for i in range(room.max_players):
            if i not in existing_seats:
                free_seat = i
                break

        if free_seat is None:
            return None

        is_host = (len(existing_seats) == 0) or (room.host_session_key == session_key)
        if is_host and not room.host_session_key and session_key:
            room.host_session_key = session_key
            room.save()

        player_name = f"Guest_{random.randint(1000, 9999)}"
        colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'cyan', 'pink', 'lime', 'brown']

        session = PlayerSession.objects.create(
            room=room,
            session_key=session_key or str(uuid.uuid4()),
            player_name=player_name,
            seat_index=free_seat,
            color=colors[free_seat % len(colors)],
            is_host=is_host,
            is_ready=is_host,
            is_connected=True
        )
        return session

    @database_sync_to_async
    def set_player_connected(self, player_id, connected):
        PlayerSession.objects.filter(id=player_id).update(
            is_connected=connected,
            disconnected_at=None if connected else timezone.now()
        )

    @database_sync_to_async
    def update_player_seat(self, player_id, new_seat, chosen_color):
        player = PlayerSession.objects.filter(id=player_id).first()
        if not player or player.room.status != 'LOBBY':
            return False, "Cannot change seats now."

        if new_seat is not None and new_seat != player.seat_index:
            if new_seat < 0 or new_seat >= player.room.max_players:
                return False, "Invalid seat index."
            if PlayerSession.objects.filter(room=player.room, seat_index=new_seat).exists():
                return False, "Seat already occupied."
            player.seat_index = new_seat

        if chosen_color:
            player.color = chosen_color

        player.save()
        return True, "Seat updated."

    @database_sync_to_async
    def toggle_player_ready(self, player_id):
        player = PlayerSession.objects.filter(id=player_id).first()
        if player and player.room.status == 'LOBBY':
            player.is_ready = not player.is_ready
            player.save()

    @database_sync_to_async
    def check_can_start_game(self, room_id):
        room = GameRoom.objects.get(id=room_id)
        players = list(room.players.all())
        req_count = 2 if room.game_type == 'CHESS_STANDARD' else (4 if room.game_type in ['CHESS_4WAY', 'CHESS_BUGHOUSE'] else 2)

        if len(players) < req_count:
            return False, f"At least {req_count} players required to start."

        unready = [p.player_name for p in players if not p.is_ready]
        if unready:
            return False, f"Waiting for players to be ready: {', '.join(unready)}"

        return True, "Ready"

    @database_sync_to_async
    def get_seats_info(self, room_id):
        room = GameRoom.objects.get(id=room_id)
        players = list(room.players.order_by('seat_index'))
        return [{'seat': p.seat_index, 'name': p.player_name, 'color': p.color} for p in players]

    @database_sync_to_async
    def update_room_game_started(self, room_id, initial_state):
        room = GameRoom.objects.get(id=room_id)
        room.status = 'PLAYING'
        room.state_data = initial_state
        room.save()

    @database_sync_to_async
    def update_room_state(self, room_id, state_data, status):
        room = GameRoom.objects.get(id=room_id)
        room.state_data = state_data
        room.status = status
        room.save()

    @database_sync_to_async
    def delete_player_by_seat(self, room_code, seat_index):
        PlayerSession.objects.filter(room__code=room_code, seat_index=seat_index).delete()

    @database_sync_to_async
    def update_room_settings(self, room_code, settings):
        room = GameRoom.objects.filter(code=room_code, status='LOBBY').first()
        if room:
            if 'max_players' in settings:
                room.max_players = max(2, min(10, int(settings['max_players'])))
            if 'variant' in settings:
                room.variant = str(settings['variant'])
            if 'turn_timer_sec' in settings:
                room.turn_timer_sec = int(settings['turn_timer_sec'])
            room.save()

    @database_sync_to_async
    def reclaim_seat_by_token(self, room_code, reconnect_token):
        return PlayerSession.objects.filter(room__code=room_code, reconnect_token=reconnect_token).first()

    @database_sync_to_async
    def record_match_history(self, room_id, final_state):
        room = GameRoom.objects.get(id=room_id)
        players_info = [
            {
                'seat': p.seat_index,
                'name': p.player_name,
                'color': p.color
            } for p in room.players.all()
        ]
        MatchHistory.objects.create(
            room_code=room.code,
            game_type=room.game_type,
            variant=room.variant,
            winner_info=final_state.get('winner', {}),
            players_summary=players_info,
            duration_seconds=int((timezone.now() - room.created_at).total_seconds())
        )

    @database_sync_to_async
    def get_full_room_payload(self, room_code):
        room = GameRoom.objects.filter(code=room_code).first()
        if not room:
            return {}

        players = list(room.players.order_by('seat_index'))
        players_data = []
        for p in players:
            players_data.append({
                'seat_index': p.seat_index,
                'player_name': p.player_name,
                'color': p.color,
                'is_host': p.is_host,
                'is_ready': p.is_ready,
                'is_connected': p.is_connected,
                'disconnected_at': p.disconnected_at.isoformat() if p.disconnected_at else None,
                'reconnect_token': str(p.reconnect_token)
            })

        return {
            'room_code': room.code,
            'game_type': room.game_type,
            'variant': room.variant,
            'max_players': room.max_players,
            'status': room.status,
            'turn_timer_sec': room.turn_timer_sec,
            'host_session_key': room.host_session_key,
            'players': players_data,
            'state_data': room.state_data
        }
