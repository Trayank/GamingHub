import uuid
import random
import string
from django.db import models, OperationalError, ProgrammingError

GAME_TYPE_CHOICES = [
    ('LUDO', 'Ludo'),
    ('CHESS_STANDARD', 'Standard Chess (2 Players)'),
    ('CHESS_4WAY', '4-Way Chess (4 Players)'),
    ('CHESS_BUGHOUSE', 'Bughouse / Double Chess (4 Players)'),
    ('CARD_UNO', 'Uno / Color Match'),
    ('CARD_POKER', 'Texas Hold\'em Poker'),
    ('CARD_BLACKJACK', 'Blackjack'),
    ('CARD_RUMMY', 'Rummy'),
]

ROOM_STATUS_CHOICES = [
    ('LOBBY', 'Waiting in Lobby'),
    ('PLAYING', 'In Progress'),
    ('FINISHED', 'Finished'),
]

AVATAR_PRESETS = {
    'wizard': {'emoji': '🧙', 'label': 'Wizard'},
    'dragon': {'emoji': '🐉', 'label': 'Dragon'},
    'knight': {'emoji': '⚔️', 'label': 'Knight'},
    'king': {'emoji': '👑', 'label': 'King'},
    'queen': {'emoji': '👸', 'label': 'Queen'},
    'dice_master': {'emoji': '🎲', 'label': 'Dice Master'},
    'ninja': {'emoji': '🥷', 'label': 'Ninja'},
    'cyber_bot': {'emoji': '🤖', 'label': 'Cyber Bot'},
    'phoenix': {'emoji': '🔥', 'label': 'Phoenix'},
    'alien': {'emoji': '👽', 'label': 'Alien'},
    'pirate': {'emoji': '🏴‍☠️', 'label': 'Pirate'},
    'champion': {'emoji': '🏆', 'label': 'Champion'}
}

def generate_room_code():
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=6))
        try:
            if not GameRoom.objects.filter(code=code).exists():
                return code
        except (OperationalError, ProgrammingError, Exception):
            return code

class PlayerProfile(models.Model):
    session_key = models.CharField(max_length=128, unique=True, db_index=True)
    user = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    display_name = models.CharField(max_length=64, default='')
    avatar = models.CharField(max_length=64, default='wizard')
    games_played = models.PositiveIntegerField(default=0)
    games_won = models.PositiveIntegerField(default=0)
    stats_by_game = models.JSONField(default=dict, blank=True)
    rating_elo = models.IntegerField(default=1200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.display_name:
            self.display_name = f"Player_{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)

    @property
    def win_rate(self) -> float:
        if self.games_played == 0:
            return 0.0
        return round((self.games_won / self.games_played) * 100, 1)


    @property
    def avatar_emoji(self) -> str:
        return AVATAR_PRESETS.get(self.avatar, {}).get('emoji', '🧙')

    def record_match_result(self, game_type: str, won: bool = True):
        self.games_played += 1
        if won:
            self.games_won += 1
            self.rating_elo += 25
        else:
            self.rating_elo = max(100, self.rating_elo - 15)

        stats = dict(self.stats_by_game or {})
        game_stats = stats.get(game_type, {'played': 0, 'won': 0, 'lost': 0})
        game_stats['played'] += 1
        if won:
            game_stats['won'] += 1
        else:
            game_stats['lost'] += 1
        stats[game_type] = game_stats
        self.stats_by_game = stats
        self.save()

    def __str__(self):
        return f"{self.display_name} ({self.session_key[:8]})"

class GameRoom(models.Model):
    code = models.CharField(max_length=6, unique=True, default=generate_room_code, db_index=True)
    host_session_key = models.CharField(max_length=128)
    game_type = models.CharField(max_length=32, choices=GAME_TYPE_CHOICES, default='LUDO')
    variant = models.CharField(max_length=32, default='4P')
    max_players = models.IntegerField(default=4)
    rules_config = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=ROOM_STATUS_CHOICES, default='LOBBY')
    state_data = models.JSONField(default=dict, blank=True)
    turn_timer_sec = models.IntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Room {self.code} ({self.game_type} - {self.status})"

class PlayerSession(models.Model):
    room = models.ForeignKey(GameRoom, on_delete=models.CASCADE, related_name='players')
    session_key = models.CharField(max_length=128)
    reconnect_token = models.UUIDField(default=uuid.uuid4, unique=True)
    player_name = models.CharField(max_length=64)
    seat_index = models.IntegerField(default=0)
    color = models.CharField(max_length=32, default='red')
    is_host = models.BooleanField(default=False)
    is_ready = models.BooleanField(default=False)
    is_connected = models.BooleanField(default=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('room', 'seat_index')

    @property
    def nickname(self):
        return self.player_name

    @property
    def seat_number(self):
        return self.seat_index

    def __str__(self):
        return f"{self.player_name} (Seat {self.seat_index} in {self.room.code})"

class MatchHistory(models.Model):
    room_code = models.CharField(max_length=6)
    game_type = models.CharField(max_length=32)
    variant = models.CharField(max_length=32)
    winner_info = models.JSONField(default=dict)
    players_summary = models.JSONField(default=list)
    duration_seconds = models.IntegerField(default=0)
    ended_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Match {self.room_code} - {self.game_type} ({self.ended_at})"
