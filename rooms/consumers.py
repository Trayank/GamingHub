import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Room, Player

User = get_user_model()


class LobbyConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket Consumer for managing room matchmaking, slot assignments, 
    ready synchronization, and host game start triggers.
    """
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code'].upper()
        self.room_group_name = f'room_{self.room_code}'
        self.user = self.scope.get('user')
        self.session_key = self.scope.get('session', {}).session_key or ""

        # Verify room existence
        room_exists = await self.check_room_exists()
        if not room_exists:
            await self.close(code=4004)
            return

        # Join group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Register or sync player in room
        player_info = await self.sync_player_join()

        # Broadcast player_joined event to all connected clients in group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'player_joined_event',
                'player': player_info,
                'lobby_state': await self.get_lobby_state(),
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            # Broadcast player departure / disconnect notice
            lobby_state = await self.get_lobby_state()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'player_left_event',
                    'sender': getattr(self, 'user', None) and getattr(self.user, 'username', 'Guest'),
                    'lobby_state': lobby_state,
                }
            )
            # Leave group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive_json(self, content):
        """
        Receives WebSocket JSON messages from client.
        Events handled: player_ready, host_start_game, chat_message
        """
        event_type = content.get('event') or content.get('type')

        if event_type == 'player_ready':
            is_ready = await self.toggle_player_ready()
            lobby_state = await self.get_lobby_state()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'player_ready_event',
                    'username': self.get_player_identifier(),
                    'is_ready': is_ready,
                    'lobby_state': lobby_state,
                }
            )

        elif event_type == 'host_start_game':
            is_host, can_start = await self.validate_start_game()
            if is_host and can_start:
                await self.update_room_status(Room.Status.IN_PROGRESS)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'host_start_game_event',
                        'status': 'in_progress',
                        'game_url': f'/rooms/{self.room_code}/play/',
                    }
                )
            else:
                await self.send_json({
                    'type': 'error',
                    'message': 'Cannot start game. Not all players are ready or you are not the host.'
                })

        elif event_type == 'chat_message':
            message = content.get('message', '').strip()
            if message:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message_event',
                        'sender': self.get_player_identifier(),
                        'message': message,
                    }
                )

    # Event handlers dispatched by channel_layer.group_send
    async def player_joined_event(self, event):
        await self.send_json(event)

    async def player_left_event(self, event):
        await self.send_json(event)

    async def player_ready_event(self, event):
        await self.send_json(event)

    async def host_start_game_event(self, event):
        await self.send_json(event)

    async def chat_message_event(self, event):
        await self.send_json(event)

    # Helpers & Database Sync Methods
    def get_player_identifier(self):
        if self.user and self.user.is_authenticated:
            return getattr(self.user, 'display_name', self.user.username)
        session = self.scope.get('session', {})
        return session.get('guest_name', 'Guest')

    @database_sync_to_async
    def check_room_exists(self):
        return Room.objects.filter(code=self.room_code).exists()

    @database_sync_to_async
    def sync_player_join(self):
        room = Room.objects.get(code=self.room_code)
        player_name = self.get_player_identifier()
        
        user_obj = self.user if (self.user and self.user.is_authenticated) else None
        
        player, created = Player.objects.get_or_create(
            room=room,
            name=player_name,
            defaults={
                'user': user_obj,
                'session_key': self.session_key,
                'is_host': (room.host == user_obj) if user_obj else False,
                'slot_index': room.get_next_slot_index(),
            }
        )

        return {
            'id': player.id,
            'name': player.name,
            'slot_index': player.slot_index,
            'is_host': player.is_host,
            'is_ready': player.is_ready,
        }

    @database_sync_to_async
    def toggle_player_ready(self):
        player_name = self.get_player_identifier()
        player = Player.objects.filter(room__code=self.room_code, name=player_name).first()
        if player:
            player.is_ready = not player.is_ready
            player.save()
            return player.is_ready
        return False

    @database_sync_to_async
    def validate_start_game(self):
        try:
            room = Room.objects.get(code=self.room_code)
            player_name = self.get_player_identifier()
            player = Player.objects.filter(room=room, name=player_name).first()
            
            is_host = player.is_host if player else (room.host == self.user)
            players = list(room.players.all())
            
            # Everyone except host (or all players) must be ready, and min 2 players present
            all_ready = all(p.is_ready for p in players) and len(players) >= 2
            return is_host, all_ready
        except Room.DoesNotExist:
            return False, False

    @database_sync_to_async
    def update_room_status(self, new_status):
        Room.objects.filter(code=self.room_code).update(status=new_status)

    @database_sync_to_async
    def get_lobby_state(self):
        try:
            room = Room.objects.get(code=self.room_code)
            players = room.players.all()
            
            slots = []
            player_map = {p.slot_index: p for p in players}

            for idx in range(room.max_players):
                p = player_map.get(idx)
                if p:
                    slots.append({
                        'slot_index': idx,
                        'occupied': True,
                        'name': p.name,
                        'is_host': p.is_host,
                        'is_ready': p.is_ready,
                    })
                else:
                    slots.append({
                        'slot_index': idx,
                        'occupied': False,
                        'name': None,
                        'is_host': False,
                        'is_ready': False,
                    })

            all_ready = len(players) >= 2 and all(p.is_ready for p in players)

            return {
                'room_code': room.code,
                'game_type': room.game_type,
                'game_type_display': room.get_game_type_display(),
                'status': room.status,
                'max_players': room.max_players,
                'player_count': len(players),
                'slots': slots,
                'can_start': all_ready,
            }
        except Room.DoesNotExist:
            return {}


# Alias for backward compatibility
RoomConsumer = LobbyConsumer
