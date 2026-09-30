from django.apps import AppConfig


class GamesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'games'

    def ready(self):
        # Auto-discover and register available game engines on startup
        try:
            from . import sample_games  # noqa
        except ImportError:
            pass
