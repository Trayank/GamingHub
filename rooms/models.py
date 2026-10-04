import uuid
import random
import string
from django.db import models, OperationalError, ProgrammingError

GAME_TYPE_CHOICES = [
    ('LUDO', 'Ludo'),
    ('CHESS_STANDARD', 'Standard Chess (2 Players)'),
    ('CHESS_4WAY', '4-Way Chess (4 Players)'),
    ('CHESS_BUGHOUSE', 'Bughouse / Double Chess (4 Players)'),
]

ROOM_STATUS_CHOICES = [
    ('LOBBY', 'Lobby'),
    ('PLAYING', 'In Progress'),
    ('FINISHED', 'Finished'),
]

def generate_room_code():
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=6))
        try:
            if not GameRoom.objects.filter(code=code).exists():
                return code
        except (OperationalError, ProgrammingError, Exception):
            return code


class GameRoom(models.Model):
    code = models.CharField(max_length=6, unique=True, default=generate_room_code, db_index=True)
    host_session_key = models.CharField(max_length=128)
    game_type = models.CharField(max_length=32, choices=GAME_TYPE_CHOICES, default='LUDO')
    variant = models.CharField(max_length=32, default='4P')
    max_players = models.IntegerField(default=4)
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
