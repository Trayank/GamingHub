from typing import Dict, Type, List, Optional
from .base import BaseGameEngine


class GameRegistry:
    """
    Central registry singleton for managing and discovering available game engines.
    """
    def __init__(self):
        self._registry: Dict[str, Type[BaseGameEngine]] = {}

    def register(self, engine_cls: Type[BaseGameEngine]):
        """Registers a game engine class."""
        if not issubclass(engine_cls, BaseGameEngine):
            raise TypeError("Engine class must inherit from BaseGameEngine")
        self._registry[engine_cls.game_id] = engine_cls
        return engine_cls

    def get(self, game_id: str) -> Optional[BaseGameEngine]:
        """Instantiates and returns an instance of the requested game engine."""
        engine_cls = self._registry.get(game_id)
        if engine_cls:
            return engine_cls()
        return None

    def list_games(self) -> List[Dict[str, Any]]:
        """Returns metadata list of all registered games with defensive attribute lookups."""
        games = []
        for game_id, engine_cls in self._registry.items():
            games.append({
                'game_id': getattr(engine_cls, 'game_id', game_id),
                'slug': getattr(engine_cls, 'slug', game_id),
                'name': getattr(engine_cls, 'name', 'Untitled Game'),
                'description': getattr(engine_cls, 'description', 'No description provided.'),
                'category': getattr(engine_cls, 'category', 'General'),
                'icon': getattr(engine_cls, 'icon', 'fa-gamepad'),
                'min_players': getattr(engine_cls, 'min_players', 2),
                'max_players': getattr(engine_cls, 'max_players', 2),
            })
        return games

    def get_game_info(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Returns metadata for a single game with defensive attribute lookups."""
        engine_cls = self._registry.get(game_id)
        if engine_cls:
            return {
                'game_id': getattr(engine_cls, 'game_id', game_id),
                'slug': getattr(engine_cls, 'slug', game_id),
                'name': getattr(engine_cls, 'name', 'Untitled Game'),
                'description': getattr(engine_cls, 'description', 'No description provided.'),
                'category': getattr(engine_cls, 'category', 'General'),
                'icon': getattr(engine_cls, 'icon', 'fa-gamepad'),
                'min_players': getattr(engine_cls, 'min_players', 2),
                'max_players': getattr(engine_cls, 'max_players', 2),
            }
        return None


# Global registry instance
game_registry = GameRegistry()
