import chess
from typing import Dict, Any, Tuple, Optional, List
from games.base import BaseGameEngine

class StandardChessEngine(BaseGameEngine):
    """
    FIDE-compliant 2-Player Standard Chess Engine leveraging `python-chess`.
    """

    def initialize_state(self, player_count: int = 2, variant: str = 'default', seats_info: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        board = chess.Board()
        white_name = seats_info[0]['name'] if seats_info and len(seats_info) > 0 else "Player 1 (White)"
        black_name = seats_info[1]['name'] if seats_info and len(seats_info) > 1 else "Player 2 (Black)"

        return {
            'fen': board.fen(),
            'board_matrix': self._board_to_matrix(board),
            'current_turn': 'w' if board.turn == chess.WHITE else 'b',
            'current_player_index': 0 if board.turn == chess.WHITE else 1,
            'is_check': board.is_check(),
            'phase': 'PLAYING',
            'winner': None,
            'result_reason': None,
            'captured_pieces': {'w': [], 'b': []},
            'players': [
                {'index': 0, 'color': 'white', 'name': white_name},
                {'index': 1, 'color': 'black', 'name': black_name}
            ],
            'move_history': [],
            'last_action_text': 'Standard Chess initialized. White to move.'
        }

    def _board_to_matrix(self, board: chess.Board) -> List[List[str]]:
        matrix = []
        for rank in range(7, -1, -1):
            row = []
            for file in range(8):
                square = chess.square(file, rank)
                piece = board.piece_at(square)
                row.append(piece.symbol() if piece else '.')
            matrix.append(row)
        return matrix

    def _rc_to_square(self, r: int, c: int) -> chess.Square:
        # Row 0 = Rank 8, Row 7 = Rank 1
        rank = 7 - r
        file = c
        return chess.square(file, rank)

    def _square_to_rc(self, square: chess.Square) -> List[int]:
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        return [7 - rank, file]

    def get_valid_moves(self, state: Dict[str, Any], player_index: int) -> Dict[str, Any]:
        if state['phase'] == 'GAME_OVER':
            return {'moves': []}

        board = chess.Board(state['fen'])
        current_index = 0 if board.turn == chess.WHITE else 1

        if player_index != current_index:
            return {'moves': []}

        legal_moves = []
        for move in board.legal_moves:
            from_rc = self._square_to_rc(move.from_square)
            to_rc = self._square_to_rc(move.to_square)
            prom = move.promotion.symbol() if move.promotion else None
            legal_moves.append({
                'from': from_rc,
                'to': to_rc,
                'uci': move.uci(),
                'promotion': prom
            })

        return {'moves': legal_moves}

    def apply_action(self, state: Dict[str, Any], player_index: int, action: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, str]:
        if state['phase'] == 'GAME_OVER':
            return state, False, "Game is over."

        board = chess.Board(state['fen'])
        expected_index = 0 if board.turn == chess.WHITE else 1

        if player_index != expected_index:
            return state, False, "Not your turn."

        action_type = action.get('type')
        if action_type != 'move_piece':
            return state, False, f"Unknown action: {action_type}"

        from_sq = action.get('from')  # [r, c]
        to_sq = action.get('to')      # [r, c]
        uci_str = action.get('uci')
        promotion_char = action.get('promotion', 'q')

        move = None
        if uci_str:
            try:
                move = chess.Move.from_uci(uci_str)
            except Exception:
                move = None

        if not move and from_sq and to_sq:
            from_square = self._rc_to_square(from_sq[0], from_sq[1])
            to_square = self._rc_to_square(to_sq[0], to_sq[1])

            # Check promotion requirement
            piece = board.piece_at(from_square)
            if piece and piece.piece_type == chess.PAWN:
                if (piece.color == chess.WHITE and to_sq[0] == 0) or (piece.color == chess.BLACK and to_sq[0] == 7):
                    prom_type = chess.QUEEN
                    if promotion_char.lower() == 'r': prom_type = chess.ROOK
                    elif promotion_char.lower() == 'b': prom_type = chess.BISHOP
                    elif promotion_char.lower() == 'n': prom_type = chess.KNIGHT
                    move = chess.Move(from_square, to_square, promotion=prom_type)
                else:
                    move = chess.Move(from_square, to_square)
            else:
                move = chess.Move(from_square, to_square)

        if not move or move not in board.legal_moves:
            return state, False, "Illegal move according to FIDE chess rules!"

        # Track captured piece and compute SAN before push
        captured_piece = board.piece_at(move.to_square)
        color_str = 'w' if board.turn == chess.WHITE else 'b'
        san_str = board.san(move)

        board.push(move)

        if captured_piece:
            state['captured_pieces'][color_str].append(captured_piece.symbol())

        p_name = state['players'][player_index]['name']

        # Update State
        state['fen'] = board.fen()
        state['board_matrix'] = self._board_to_matrix(board)
        state['current_turn'] = 'w' if board.turn == chess.WHITE else 'b'
        state['current_player_index'] = 0 if board.turn == chess.WHITE else 1
        state['is_check'] = board.is_check()

        if board.is_checkmate():
            state['phase'] = 'GAME_OVER'
            state['winner'] = color_str
            state['result_reason'] = 'checkmate'
            state['last_action_text'] = f"🏆 Checkmate! {p_name} wins!"
        elif board.is_stalemate():
            state['phase'] = 'GAME_OVER'
            state['winner'] = 'draw'
            state['result_reason'] = 'stalemate'
            state['last_action_text'] = "🤝 Game drawn by stalemate."
        elif board.is_insufficient_material():
            state['phase'] = 'GAME_OVER'
            state['winner'] = 'draw'
            state['result_reason'] = 'insufficient_material'
            state['last_action_text'] = "🤝 Game drawn by insufficient material."
        else:
            if board.is_check():
                state['last_action_text'] = f"⚡ {p_name} played {san_str}. Check!"
            else:
                state['last_action_text'] = f"{p_name} played {san_str}."

        state['move_history'].append({
            'uci': move.uci(),
            'san': san_str,
            'player': player_index
        })


        return state, True, "Move applied."

    def check_win_condition(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if state['phase'] == 'GAME_OVER':
            return {
                'winner': state['winner'],
                'reason': state['result_reason']
            }
        return None

    def serialize_state(self, state: Dict[str, Any], player_index: Optional[int] = None) -> Dict[str, Any]:
        valid_moves = {}
        if player_index is not None:
            valid_moves = self.get_valid_moves(state, player_index)

        serialized = dict(state)
        serialized['valid_moves_for_client'] = valid_moves
        return serialized
