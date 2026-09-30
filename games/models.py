from django.db import models
from rooms.models import Room


class GameSession(models.Model):
    """
    Archives completed game sessions to the database for leaderboards and stat history.
    """
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='game_sessions'
    )
    game_type = models.CharField(max_length=50, default='tic_tac_toe')
    winner = models.CharField(max_length=100, blank=True, null=True)
    is_draw = models.BooleanField(default=False)
    final_state = models.JSONField(default=dict)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-ended_at']

    def __str__(self):
        result = "Draw" if self.is_draw else f"Winner: {self.winner}"
        return f"GameSession {self.id} ({self.game_type}) in Room {self.room.code} - {result}"
