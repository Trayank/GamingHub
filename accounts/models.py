from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model supporting registered players and guests.
    """
    is_guest = models.BooleanField(
        default=False,
        help_text="Designates whether this account is a temporary guest player session."
    )
    avatar_url = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Optional avatar icon or image URL."
    )
    games_played = models.PositiveIntegerField(default=0)
    games_won = models.PositiveIntegerField(default=0)

    @property
    def display_name(self):
        """Returns username or Guest display title."""
        if self.is_guest:
            return f"{self.username} (Guest)"
        return self.username

    def __str__(self):
        return self.display_name
