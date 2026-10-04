from typing import Dict, Any, List, Optional
from .base import BaseGameEngine
from .registry import game_registry
from .engine.trivia import TriviaEngine
from .engine.ludo import LudoEngine

# Register Engines
game_registry.register(TriviaEngine)
game_registry.register(LudoEngine)


@game_registry.register
class TicTacToeEngine(BaseGameEngine):
    game_id = "tic_tac_toe"
    slug = "tic_tac_toe"
    name = "Tic-Tac-Toe"
    description = "Classic 3x3 grid turn-based strategy game for 2 players."
    category = "Strategy"
    icon = "fa-chess-board"
    min_players = 2
    max_players = 2

    def initialize_state(self, players: List[str]) -> Dict[str, Any]:
        return {
            'board': [""] * 9,
            'current_turn': players[0] if players else "",
            'players': {
                players[0]: 'X',
                players[1]: 'O'
            } if len(players) >= 2 else {},
            'winner': None,
            'is_over': False,
        }

    def validate_move(self, state: Dict[str, Any], player_id: str, action: Dict[str, Any]) -> bool:
        if state.get('is_over'):
            return False
        if state.get('current_turn') != player_id:
            return False
        
        index = action.get('index')
        if index is None or not (0 <= index < 9):
            return False
        
        board = state.get('board', [])
        return board[index] == ""

    def apply_move(self, state: Dict[str, Any], player_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        index = action['index']
        symbol = state['players'][player_id]
        state['board'][index] = symbol

        winner = self.check_winner(state)
        if winner:
            state['winner'] = winner
            state['is_over'] = True
        else:
            player_keys = list(state['players'].keys())
            next_player = player_keys[1] if player_keys[0] == player_id else player_keys[0]
            state['current_turn'] = next_player

        return state

    def check_winner(self, state: Dict[str, Any]) -> Optional[str]:
        board = state.get('board', [])
        lines = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
            [0, 4, 8], [2, 4, 6]               # Diagonals
        ]
        for a, b, c in lines:
            if board[a] and board[a] == board[b] == board[c]:
                for player, sym in state['players'].items():
                    if sym == board[a]:
                        return player

        if all(cell != "" for cell in board):
            return "draw"

        return None


@game_registry.register
class RockPaperScissorsEngine(BaseGameEngine):
    game_id = "rock_paper_scissors"
    slug = "rock_paper_scissors"
    name = "Rock Paper Scissors"
    description = "Simultaneous choice show-down game for 2 players."
    category = "Quick Play"
    icon = "fa-hand-back-fist"
    min_players = 2
    max_players = 2

    def initialize_state(self, players: List[str]) -> Dict[str, Any]:
        return {
            'choices': {},
            'players': players,
            'winner': None,
            'is_over': False,
        }

    def validate_move(self, state: Dict[str, Any], player_id: str, action: Dict[str, Any]) -> bool:
        if state.get('is_over'):
            return False
        choice = action.get('choice')
        return choice in ['rock', 'paper', 'scissors']

    def apply_move(self, state: Dict[str, Any], player_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        state['choices'][player_id] = action['choice']
        if len(state['choices']) >= 2:
            state['winner'] = self.check_winner(state)
            state['is_over'] = True
        return state

    def check_winner(self, state: Dict[str, Any]) -> Optional[str]:
        choices = state.get('choices', {})
        if len(choices) < 2:
            return None

        p1, p2 = list(choices.keys())[:2]
        c1, c2 = choices[p1], choices[p2]

        if c1 == c2:
            return "draw"
        
        wins = {('rock', 'scissors'), ('scissors', 'paper'), ('paper', 'rock')}
        if (c1, c2) in wins:
            return p1
        return p2
