import copy
import chess
from typing import Dict, Any, Tuple, Optional, List
from games.base import BaseGameEngine
from games.chess.standard_engine import StandardChessEngine

class BughouseEngine(BaseGameEngine):
    """
    Bughouse / Double Chess Engine pairing two simultaneous 8x8 boards (Board A & Board B).
    Teammates:
      - Team 1: Seat 0 (Board A White) & Seat 3 (Board B Black)
      - Team 2: Seat 1 (Board A Black) & Seat 2 (Board B White)
    """

    def __init__(self):
        self.sub_engine = StandardChessEngine()

    def initialize_state(self, player_count: int = 4, variant: str = 'default', seats_info: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        board_a_state = self.sub_engine.initialize_state(2, variant, seats_info[:2] if seats_info else None)
        board_b_state = self.sub_engine.initialize_state(2, variant, seats_info[2:] if seats_info else None)

        players = [
            {'index': 0, 'board': 'A', 'color': 'w', 'team': 1, 'name': seats_info[0]['name'] if seats_info and len(seats_info) > 0 else 'Board A White'},
            {'index': 1, 'board': 'A', 'color': 'b', 'team': 2, 'name': seats_info[1]['name'] if seats_info and len(seats_info) > 1 else 'Board A Black'},
            {'index': 2, 'board': 'B', 'color': 'w', 'team': 2, 'name': seats_info[2]['name'] if seats_info and len(seats_info) > 2 else 'Board B White'},
            {'index': 3, 'board': 'B', 'color': 'b', 'team': 1, 'name': seats_info[3]['name'] if seats_info and len(seats_info) > 3 else 'Board B Black'}
        ]

        return {
            'board_a': board_a_state,
            'board_b': board_b_state,
            'reserves': {
                0: [], # Seat 0 (Team 1, Board A White)
                1: [], # Seat 1 (Team 2, Board A Black)
                2: [], # Seat 2 (Team 2, Board B White)
                3: []  # Seat 3 (Team 1, Board B Black)
            },
            'players': players,
            'phase': 'PLAYING',
            'winning_team': None,
            'last_action_text': 'Bughouse match started across Boards A & B.'
        }

    def _get_teammate_seat(self, seat_index: int) -> int:
        mapping = {0: 3, 3: 0, 1: 2, 2: 1}
        return mapping[seat_index]

    def get_valid_moves(self, state: Dict[str, Any], player_index: int) -> Dict[str, Any]:
        if state['phase'] == 'GAME_OVER':
            return {'moves': [], 'drops': []}

        player = state['players'][player_index]
        sub_state = state['board_a'] if player['board'] == 'A' else state['board_b']
        sub_valid = self.sub_engine.get_valid_moves(sub_state, 0 if player['color'] == 'w' else 1)

        # Drop options from reserve palette
        reserve = state['reserves'][player_index]
        drops = []
        if sub_state['current_turn'] == player['color'] and reserve:
            board_matrix = sub_state['board_matrix']
            for r in range(8):
                for c in range(8):
                    if board_matrix[r][c] == '.':
                        for piece in set(reserve):
                            if piece.upper() == 'P' and (r == 0 or r == 7):
                                continue  # Pawns cannot be dropped on 1st or 8th rank
                            drops.append({'piece': piece, 'to': [r, c]})

        return {
            'moves': sub_valid.get('moves', []),
            'drops': drops
        }

    def apply_action(self, state: Dict[str, Any], player_index: int, action: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, str]:
        if state['phase'] == 'GAME_OVER':
            return state, False, "Bughouse match is over."

        player = state['players'][player_index]
        board_key = 'board_a' if player['board'] == 'A' else 'board_b'
        sub_state = state[board_key]

        action_type = action.get('type')

        if action_type == 'move_piece':
            captures_before = len(sub_state['captured_pieces'][player['color']])

            updated_sub_state, success, msg = self.sub_engine.apply_action(
                sub_state, 0 if player['color'] == 'w' else 1, action
            )

            if not success:
                return state, False, msg

            state[board_key] = updated_sub_state

            # Transfer captured piece to teammate reserve
            captures_after = updated_sub_state['captured_pieces'][player['color']]
            if len(captures_after) > captures_before:
                captured_piece = captures_after[-1]
                teammate_seat = self._get_teammate_seat(player_index)
                state['reserves'][teammate_seat].append(captured_piece.upper())
                state['last_action_text'] = f"🔄 {player['name']} captured {captured_piece}! Transferred to teammate reserve!"

            # Immediate Checkmate Trigger for both boards
            if updated_sub_state['phase'] == 'GAME_OVER':
                if updated_sub_state['winner'] and updated_sub_state['winner'] != 'draw':
                    winning_team = player['team'] if updated_sub_state['winner'] == player['color'] else (3 - player['team'])
                    state['phase'] = 'GAME_OVER'
                    state['winning_team'] = winning_team
                    state['last_action_text'] = f"🏆 Checkmate on Board {player['board']}! Team {winning_team} wins Bughouse!"
                    return state, True, "Bughouse victory!"

            return state, True, "Move applied."

        elif action_type == 'drop_piece':
            if sub_state['current_turn'] != player['color']:
                return state, False, "Not your turn to move/drop on your board."

            piece_symbol = action.get('piece')
            to_sq = action.get('to')  # [r, c]

            if not piece_symbol or not to_sq:
                return state, False, "Invalid drop payload."

            reserve = state['reserves'][player_index]
            upper_piece = piece_symbol.upper()
            if upper_piece not in [p.upper() for p in reserve]:
                return state, False, f"Piece {upper_piece} is not in your reserve."

            r, c = to_sq
            if not (0 <= r < 8 and 0 <= c < 8) or sub_state['board_matrix'][r][c] != '.':
                return state, False, "Target square must be empty for a reserve drop."

            if upper_piece == 'P' and (r == 0 or r == 7):
                return state, False, "Pawns cannot be dropped on the 1st or 8th rank."

            # Remove piece from reserve
            for idx, p in enumerate(reserve):
                if p.upper() == upper_piece:
                    reserve.pop(idx)
                    break

            # Modify FEN / board matrix to place piece
            board_obj = chess.Board(sub_state['fen'])
            square = self.sub_engine._rc_to_square(r, c)
            piece_type = getattr(chess, {'P': 'PAWN', 'N': 'KNIGHT', 'B': 'BISHOP', 'R': 'ROOK', 'Q': 'QUEEN'}[upper_piece])
            piece_obj = chess.Piece(piece_type, chess.WHITE if player['color'] == 'w' else chess.BLACK)
            board_obj.set_piece_at(square, piece_obj)

            # Switch turn
            board_obj.turn = not board_obj.turn

            sub_state['fen'] = board_obj.fen()
            sub_state['board_matrix'] = self.sub_engine._board_to_matrix(board_obj)
            sub_state['current_turn'] = 'w' if board_obj.turn == chess.WHITE else 'b'
            sub_state['current_player_index'] = 0 if board_obj.turn == chess.WHITE else 1
            sub_state['is_check'] = board_obj.is_check()

            state['last_action_text'] = f"✨ {player['name']} dropped a {upper_piece} onto Board {player['board']}!"
            return state, True, "Piece dropped."

        return state, False, f"Unknown action: {action_type}"

    def check_win_condition(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if state['phase'] == 'GAME_OVER':
            return {'winning_team': state['winning_team']}
        return None

    def serialize_state(self, state: Dict[str, Any], player_index: Optional[int] = None) -> Dict[str, Any]:
        valid_moves = {}
        if player_index is not None:
            valid_moves = self.get_valid_moves(state, player_index)

        serialized = dict(state)
        serialized['valid_moves_for_client'] = valid_moves
        return serialized
