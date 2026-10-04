from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional, List

class BaseGameEngine(ABC):
    """
    Unified abstract base class for server-authoritative game engines.
    """

    @abstractmethod
    def initialize_state(self, player_count: int, variant: str = 'default', seats_info: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Initializes and returns the game state dictionary.
        """
        pass

    @abstractmethod
    def apply_action(self, state: Dict[str, Any], player_index: int, action: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, str]:
        """
        Validates and applies a player's intent to the state.
        Returns: (updated_state, is_valid, error_message)
        """
        pass

    @abstractmethod
    def get_valid_moves(self, state: Dict[str, Any], player_index: int) -> Dict[str, Any]:
        """
        Returns valid actions/moves available to the specified player.
        """
        pass

    @abstractmethod
    def check_win_condition(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Checks if the game has ended.
        Returns None if active, or dict with winner_seat, rankings, and reason.
        """
        pass

    @abstractmethod
    def serialize_state(self, state: Dict[str, Any], player_index: Optional[int] = None) -> Dict[str, Any]:
        """
        Serializes the game state for broadcasting over WebSockets.
        Optionally tailors state per player_index (e.g. hiding hidden cards, adding valid moves).
        """
        pass
