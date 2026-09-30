from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple


class BaseGameEngine(ABC):
    """
    Abstract Base Class for extensible turn-based and real-time game engines.
    Defines strict contracts for initial state generation, move validation,
    state transitions, victory checking, and public payload serialization.
    """
    game_id: str = "base"
    slug: str = "base"
    name: str = "Base Engine"
    description: str = "Generic browser-based game engine template."
    category: str = "General"
    icon: str = "fa-gamepad"
    min_players: int = 2
    max_players: int = 2

    @abstractmethod
    def initialize_state(self, players: List[str]) -> Dict[str, Any]:
        """Initializes a clean game state dictionary for the provided list of player identifiers."""
        pass

    @abstractmethod
    def validate_move(self, player: str, move_data: Dict[str, Any], state: Dict[str, Any]) -> bool:
        """Validates whether a move submitted by player is valid according to game rules."""
        pass

    @abstractmethod
    def apply_move(self, player: str, move_data: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """Applies move_data to state, returning updated state dictionary."""
        pass

    @abstractmethod
    def check_game_over(self, state: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Evaluates current state for victory/draw condition.
        Returns Tuple[is_over: bool, winner_name: str | 'draw' | None].
        """
        pass

    def get_public_state(self, state: Dict[str, Any], player: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns serialized game state suitable for broadcasting over WebSockets.
        Override to obscure hidden information (e.g. secret cards) per player.
        """
        return state
