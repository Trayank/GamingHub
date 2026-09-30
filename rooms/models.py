import random
import string
from django.db import models
from django.conf import settings


def generate_room_code(length=6):
    """Generates a unique 6-character uppercase alphanumeric room code."""
    characters = string.ascii_uppercase + string.digits
    characters = characters.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
    return ''.join(random.choices(characters, k=length))


class Room(models.Model):
    class GameType(models.TextChoices):
        TIC_TAC_TOE = 'tic_tac_toe', 'Tic-Tac-Toe'
        ROCK_PAPER_SCISSORS = 'rock_paper_scissors', 'Rock Paper Scissors'
        CONNECT_FOUR = 'connect_four', 'Connect Four'

    class Status(models.TextChoices):
        WAITING = 'waiting', 'Waiting for Players'
        IN_PROGRESS = 'in_progress', 'Game In Progress'
        FINISHED = 'finished', 'Game Finished'

    code = models.CharField(
        max_length=6,
        unique=True,
        db_index=True,
        editable=False,
        help_text="Unique 6-character room code."
    )
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hosted_rooms'
    )
    host_session_key = models.CharField(max_length=100, blank=True, default="")
    game_type = models.CharField(
        max_length=50,
        choices=GameType.choices,
        default=GameType.TIC_TAC_TOE
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.WAITING
    )
    max_players = models.PositiveIntegerField(default=2)
    is_private = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.code:
            code = generate_room_code()
            while Room.objects.filter(code=code).exists():
                code = generate_room_code()
            self.code = code
        super().save(*args, **kwargs)

    @property
    def player_count(self):
        return self.players.count()

    @property
    def is_full(self):
        return self.player_count >= self.max_players

    def get_next_slot_index(self):
        occupied_slots = set(self.players.values_list('slot_index', flat=True))
        for slot in range(self.max_players):
            if slot not in occupied_slots:
                return slot
        return occupied_slots.__len__()

    def __str__(self):
        return f"Room {self.code} ({self.game_type}) - {self.get_status_display()}"


class Player(models.Model):
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='players'
    )
    name = models.CharField(max_length=50)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='room_players'
    )
    session_key = models.CharField(max_length=100, blank=True, default="")
    is_host = models.BooleanField(default=False)
    is_ready = models.BooleanField(default=False)
    slot_index = models.PositiveIntegerField(default=0)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['slot_index']

    def __str__(self):
        return f"{self.name} (Slot {self.slot_index}) in {self.room.code}"


# Backward compatibility alias for RoomPlayer if referenced
RoomPlayer = Player
