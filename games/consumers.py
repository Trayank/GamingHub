import json
import asyncio
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rooms.models import Room, Player
from .models import GameSession
from .engine.tictactoe import (
    tictactoe_engine,
    get_game_state,
    save_game_state,
    delete_game_state
)
from .engine.trivia import trivia_engine, censor_profanity

User = get_user_model()


class GameConsumer(AsyncJsonWebsocketConsumer):
    """
    Real-time WebSocket consumer for live Tic-Tac-Toe execution.
    """
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code'].upper()
        self.game_group_name = f'game_{self.room_code}'
        self.user = self.scope.get('user')

        room = await self.get_room()
        if not room:
            await self.close(code=4004)
            return

        await self.channel_layer.group_add(
            self.game_group_name,
            self.channel_name
        )
        await self.accept()

        state = await self.get_or_create_game_state(room)
        player_name = self.get_player_name()

        public_state = tictactoe_engine.get_public_state(state, player=player_name)
        await self.send_json({
            'type': 'game_state_update',
            'state': public_state,
        })

    async def disconnect(self, close_code):
        if hasattr(self, 'game_group_name'):
            await self.channel_layer.group_discard(
                self.game_group_name,
                self.channel_name
            )

    async def receive_json(self, content):
        event_type = content.get('type') or content.get('event')
        player_name = self.get_player_name()

        if event_type == 'make_move':
            cell_index = content.get('cell_index')
            move_data = {'cell_index': cell_index}

            state = await self.fetch_cached_state()
            if not state:
                return

            is_valid = tictactoe_engine.validate_move(player_name, move_data, state)
            if not is_valid:
                await self.send_json({
                    'type': 'invalid_move',
                    'message': 'Invalid move. Either it is not your turn or cell is occupied.'
                })
                return

            updated_state = tictactoe_engine.apply_move(player_name, move_data, state)
            await self.cache_state(updated_state)

            if updated_state.get('is_over'):
                winner = updated_state.get('winner')
                is_draw = (winner == 'draw')
                winner_name = None if is_draw else winner
                await self.archive_game(self.room_code, winner_name, is_draw, updated_state)

            await self.channel_layer.group_send(
                self.game_group_name,
                {
                    'type': 'game_broadcast_event',
                    'state': updated_state,
                    'last_move': {
                        'player': player_name,
                        'cell_index': cell_index
                    }
                }
            )

        elif event_type == 'restart_game':
            room = await self.get_room()
            if room:
                new_state = await self.reset_game_state(room)
                await self.channel_layer.group_send(
                    self.game_group_name,
                    {
                        'type': 'game_broadcast_event',
                        'state': new_state,
                    }
                )

    async def game_broadcast_event(self, event):
        player_name = self.get_player_name()
        state = event.get('state', {})
        public_state = tictactoe_engine.get_public_state(state, player=player_name)
        
        await self.send_json({
            'type': 'game_state_update',
            'state': public_state,
            'last_move': event.get('last_move')
        })

    def get_player_name(self):
        if self.user and self.user.is_authenticated:
            return getattr(self.user, 'display_name', self.user.username)
        session = self.scope.get('session', {})
        return session.get('guest_name', 'Guest')

    @database_sync_to_async
    def get_room(self):
        return Room.objects.filter(code=self.room_code).first()

    @database_sync_to_async
    def get_or_create_game_state(self, room):
        state = get_game_state(room.code)
        if not state:
            players = list(room.players.values_list('name', flat=True))
            if len(players) < 2:
                players = players + ['Guest_Opponent']
            state = tictactoe_engine.initialize_state(players)
            save_game_state(room.code, state)
        return state

    @database_sync_to_async
    def reset_game_state(self, room):
        players = list(room.players.values_list('name', flat=True))
        if len(players) < 2:
            players = players + ['Guest_Opponent']
        new_state = tictactoe_engine.initialize_state(players)
        save_game_state(room.code, new_state)
        return new_state

    @database_sync_to_async
    def fetch_cached_state(self):
        return get_game_state(self.room_code)

    @database_sync_to_async
    def cache_state(self, state):
        save_game_state(self.room_code, state)

    @database_sync_to_async
    def archive_game(self, room_code, winner_name, is_draw, final_state):
        room = Room.objects.filter(code=room_code).first()
        if room:
            GameSession.objects.create(
                room=room,
                game_type=room.game_type,
                winner=winner_name,
                is_draw=is_draw,
                final_state=final_state
            )
            room.status = Room.Status.FINISHED
            room.save()


# In-memory dictionary tracking running trivia timer loops per room
TRIVIA_TIMER_TASKS = {}


class TriviaConsumer(AsyncJsonWebsocketConsumer):
    """
    Real-Time Multiplayer Trivia Consumer.
    Manages server-authoritative 15-second question countdown timers,
    speed/streak scoring, profanity-filtered side chat, and live leaderboards.
    """
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code'].upper()
        self.trivia_group_name = f'game_trivia_{self.room_code}'
        self.user = self.scope.get('user')

        room = await self.get_room()
        if not room:
            await self.close(code=4004)
            return

        await self.channel_layer.group_add(
            self.trivia_group_name,
            self.channel_name
        )
        await self.accept()

        state = await self.get_or_create_trivia_state(room)
        player_name = self.get_player_name()

        # Check if timer loop is already active for this room; if not, launch it
        if self.room_code not in TRIVIA_TIMER_TASKS or TRIVIA_TIMER_TASKS[self.room_code].done():
            TRIVIA_TIMER_TASKS[self.room_code] = asyncio.create_task(self.run_server_timer_loop())

        public_state = trivia_engine.get_public_state(state, player=player_name)
        await self.send_json({
            'type': 'trivia_state_update',
            'state': public_state,
        })

    async def disconnect(self, close_code):
        if hasattr(self, 'trivia_group_name'):
            await self.channel_layer.group_discard(
                self.trivia_group_name,
                self.channel_name
            )

    async def receive_json(self, content):
        event_type = content.get('type') or content.get('event')
        player_name = self.get_player_name()

        if event_type == 'submit_answer':
            option_index = content.get('option_index')
            move_data = {'option_index': option_index}

            state = await self.fetch_cached_state()
            if state and trivia_engine.validate_move(player_name, move_data, state):
                updated_state = trivia_engine.apply_move(player_name, move_data, state)
                await self.cache_state(updated_state)

                # Send feedback to answering player immediately
                user_ans = updated_state['round_answers'].get(player_name, {})
                await self.send_json({
                    'type': 'answer_ack',
                    'is_correct': user_ans.get('is_correct', False),
                    'points_earned': user_ans.get('points_earned', 0),
                    'streak': updated_state['player_streaks'].get(player_name, 0),
                })

        elif event_type == 'chat_message':
            message = content.get('message', '').strip()
            if message:
                # Apply server-side profanity filter
                clean_message = censor_profanity(message)
                
                # Fetch player's current score for chat badge
                state = await self.fetch_cached_state()
                player_score = state.get('player_scores', {}).get(player_name, 0) if state else 0

                await self.channel_layer.group_send(
                    self.trivia_group_name,
                    {
                        'type': 'chat_broadcast_event',
                        'sender': player_name,
                        'message': clean_message,
                        'score_badge': player_score,
                    }
                )

    async def run_server_timer_loop(self):
        """
        Server-authoritative timer driving 15s questions and 5s intermissions.
        Ensures all clients are 100% synchronized without relying on client clocks.
        """
        try:
            while True:
                state = await self.fetch_cached_state()
                if not state or state.get('is_over'):
                    break

                # 1. Start or advance round
                state, is_over = trivia_engine.start_next_round(state)
                await self.cache_state(state)

                if is_over:
                    # Game Over - Archive Session
                    winner = state.get('winner')
                    is_draw = (winner == 'draw')
                    winner_name = None if is_draw else winner
                    await self.archive_game(self.room_code, winner_name, is_draw, state)

                    await self.channel_layer.group_send(
                        self.trivia_group_name,
                        {
                            'type': 'trivia_game_over_event',
                            'state': state,
                            'leaderboard': trivia_engine.get_leaderboard(state)
                        }
                    )
                    break

                # Broadcast new question start
                await self.channel_layer.group_send(
                    self.trivia_group_name,
                    {
                        'type': 'trivia_question_start_event',
                        'round_num': state['current_round'],
                        'total_rounds': state['total_rounds'],
                        'question': state['current_question'],
                    }
                )

                # 2. 15-Second Question Countdown Loop
                for seconds_left in range(trivia_engine.QUESTION_DURATION_SECONDS, 0, -1):
                    await asyncio.sleep(1)
                    await self.channel_layer.group_send(
                        self.trivia_group_name,
                        {
                            'type': 'timer_tick_event',
                            'seconds_remaining': seconds_left,
                            'total_seconds': trivia_engine.QUESTION_DURATION_SECONDS,
                        }
                    )

                # 3. Intermission & Answer Reveal (5 seconds)
                state = await self.fetch_cached_state()
                if state:
                    state['is_intermission'] = True
                    await self.cache_state(state)

                round_idx = state['current_round'] - 1 if state else 0
                correct_idx = trivia_engine.questions[round_idx]['correct_index'] if round_idx < len(trivia_engine.questions) else 0

                await self.channel_layer.group_send(
                    self.trivia_group_name,
                    {
                        'type': 'round_intermission_event',
                        'correct_index': correct_idx,
                        'explanation': trivia_engine.questions[round_idx]['explanation'],
                        'leaderboard': trivia_engine.get_leaderboard(state) if state else [],
                    }
                )
                await asyncio.sleep(trivia_engine.INTERMISSION_DURATION_SECONDS)

        except asyncio.CancelledError:
            pass
        finally:
            TRIVIA_TIMER_TASKS.pop(self.room_code, None)

    # Event Handlers
    async def trivia_state_update(self, event):
        await self.send_json(event)

    async def trivia_question_start_event(self, event):
        await self.send_json(event)

    async def timer_tick_event(self, event):
        await self.send_json(event)

    async def round_intermission_event(self, event):
        await self.send_json(event)

    async def trivia_game_over_event(self, event):
        await self.send_json(event)

    async def chat_broadcast_event(self, event):
        await self.send_json(event)

    # Database Helpers
    def get_player_name(self):
        if self.user and self.user.is_authenticated:
            return getattr(self.user, 'display_name', self.user.username)
        session = self.scope.get('session', {})
        return session.get('guest_name', 'Guest')

    @database_sync_to_async
    def get_room(self):
        return Room.objects.filter(code=self.room_code).first()

    @database_sync_to_async
    def get_or_create_trivia_state(self, room):
        state = get_game_state(room.code)
        if not state:
            players = list(room.players.values_list('name', flat=True))
            if not players:
                players = ['Player_1', 'Player_2']
            state = trivia_engine.initialize_state(players)
            save_game_state(room.code, state)
        return state

    @database_sync_to_async
    def fetch_cached_state(self):
        return get_game_state(self.room_code)

    @database_sync_to_async
    def cache_state(self, state):
        save_game_state(self.room_code, state)

    @database_sync_to_async
    def archive_game(self, room_code, winner_name, is_draw, final_state):
        room = Room.objects.filter(code=room_code).first()
        if room:
            GameSession.objects.create(
                room=room,
                game_type='trivia',
                winner=winner_name,
                is_draw=is_draw,
                final_state=final_state
            )
            room.status = Room.Status.FINISHED
            room.save()
