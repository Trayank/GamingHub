from typing import Dict, Any, List, Optional, Tuple
from django.core.cache import cache
from .base import BaseGameEngine


class TicTacToeEngine(BaseGameEngine):
    """
    Pure server-side 2-Player Tic-Tac-Toe Game Engine.
    Handles 3x3 board state, symbol assignment ('X' / 'O'),
    turn validation, row/col/diag win checking, and draw detection.
    """
    game_id = "tic_tac_toe"
    name = "Tic-Tac-Toe"
    min_players = 2
    max_players = 2

    WINNING_COMBINATIONS = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
        [0, 4, 8], [2, 4, 6]               # Diagonals
    ]

    def initialize_state(self, players: List[str]) -> Dict[str, Any]:
        if len(players) < 2:
            players = players + [f"Player_{i}" for i in range(len(players), 2)]

        player1, player2 = players[0], players[1]

        return {
            'board': [""] * 9,
            'current_turn': player1,
            'players': {
                player1: 'X',
                player2: 'O'
            },
            'winning_line': None,
            'winner': None,
            'is_over': False,
            'move_history': [],
        }

    def validate_move(self, player: str, move_data: Dict[str, Any], state: Dict[str, Any]) -> bool:
        if not state or state.get('is_over'):
            return False

        if state.get('current_turn') != player:
            return False

        cell_index = move_data.get('cell_index')
        if cell_index is None or not (isinstance(cell_index, int) and 0 <= cell_index < 9):
            return False

        board = state.get('board', [])
        return board[cell_index] == ""

    def apply_move(self, player: str, move_data: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        cell_index = move_data['cell_index']
        symbol = state['players'][player]

        # Apply cell symbol
        state['board'][cell_index] = symbol
        state['move_history'].append({
            'player': player,
            'symbol': symbol,
            'cell_index': cell_index
        })

        # Check win / draw
        is_over, winner, winning_line = self._evaluate_game_over(state)
        if is_over:
            state['is_over'] = True
            state['winner'] = winner
            state['winning_line'] = winning_line
        else:
            # Switch turn to opponent
            player_list = list(state['players'].keys())
            state['current_turn'] = player_list[1] if player_list[0] == player else player_list[0]

        return state

    def check_game_over(self, state: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        is_over, winner, _ = self._evaluate_game_over(state)
        return is_over, winner

    def _evaluate_game_over(self, state: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[List[int]]]:
        board = state.get('board', [])
        players = state.get('players', {})

        # Check winning lines
        for combo in self.WINNING_COMBINATIONS:
            a, b, c = combo
            if board[a] and board[a] == board[b] == board[c]:
                symbol = board[a]
                winner_name = next((p for p, sym in players.items() if sym == symbol), symbol)
                return True, winner_name, combo

        # Check draw (all cells filled)
        if all(cell != "" for cell in board):
            return True, "draw", None

        return False, None, None

    def get_public_state(self, state: Dict[str, Any], player: Optional[str] = None) -> Dict[str, Any]:
        return {
            'board': state.get('board', [""] * 9),
            'current_turn': state.get('current_turn'),
            'players': state.get('players', {}),
            'winning_line': state.get('winning_line'),
            'winner': state.get('winner'),
            'is_over': state.get('is_over', False),
            'your_symbol': state.get('players', {}).get(player, "") if player else "",
        }


# Global engine instance
tictactoe_engine = TicTacToeEngine()


# Redis Cache State Helper Functions
def get_game_cache_key(room_code: str) -> str:
    return f"game_state_{room_code.upper()}"


def save_game_state(room_code: str, state: Dict[str, Any], timeout: int = 7200):
    """Caches live game state in Redis (or Django Cache backend)."""
    key = get_game_cache_key(room_code)
    cache.set(key, state, timeout=timeout)


def get_game_state(room_code: str) -> Optional[Dict[str, Any]]:
    """Retrieves live game state from Redis Cache."""
    key = get_game_cache_key(room_code)
    return cache.get(key)


def delete_game_state(room_code: str):
    """Deletes game state from Redis Cache."""
    key = get_game_cache_key(room_code)
    cache.delete(key)
