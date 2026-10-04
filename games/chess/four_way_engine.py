import copy
from typing import Dict, Any, Tuple, Optional, List
from games.base import BaseGameEngine

PLAYER_COLORS = ['red', 'blue', 'yellow', 'green']
COLOR_CODES = ['r', 'b', 'y', 'g']

class FourWayChessEngine(BaseGameEngine):
    """
    4-Player Chess Engine on a 14x14 cross-shaped board (160 active squares).
    Armies: Red (South), Blue (West), Yellow (North), Green (East).
    Turn Order: Red -> Blue -> Yellow -> Green.
    """

    BOARD_SIZE = 14

    def initialize_state(self, player_count: int = 4, variant: str = 'default', seats_info: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        board = [['.' for _ in range(14)] for _ in range(14)]

        # Mark 3x3 corners as invalid (None)
        for r in range(14):
            for c in range(14):
                if (r < 3 and c < 3) or (r < 3 and c > 10) or (r > 10 and c < 3) or (r > 10 and c > 10):
                    board[r][c] = None

        # Red (South / Player 0: rows 12 & 13, cols 3..10)
        board[13][3:11] = ['R_r', 'N_r', 'B_r', 'K_r', 'Q_r', 'B_r', 'N_r', 'R_r']
        board[12][3:11] = ['P_r'] * 8

        # Yellow (North / Player 2: rows 0 & 1, cols 3..10)
        board[0][3:11] = ['R_y', 'N_y', 'B_y', 'Q_y', 'K_y', 'B_y', 'N_y', 'R_y']
        board[1][3:11] = ['P_y'] * 8

        # Blue (West / Player 1: cols 0 & 1, rows 3..10)
        blue_back = ['R_b', 'N_b', 'B_b', 'Q_b', 'K_b', 'B_b', 'N_b', 'R_b']
        for idx, r in enumerate(range(3, 11)):
            board[r][0] = blue_back[idx]
            board[r][1] = 'P_b'

        # Green (East / Player 3: cols 12 & 13, rows 3..10)
        green_back = ['R_g', 'N_g', 'B_g', 'K_g', 'Q_g', 'B_g', 'N_g', 'R_g']
        for idx, r in enumerate(range(3, 11)):
            board[r][13] = green_back[idx]
            board[r][12] = 'P_g'

        players = []
        for i in range(4):
            name = seats_info[i]['name'] if seats_info and i < len(seats_info) else f"Player {i+1} ({PLAYER_COLORS[i].capitalize()})"
            players.append({
                'index': i,
                'color': PLAYER_COLORS[i],
                'code': COLOR_CODES[i],
                'name': name,
                'is_eliminated': False,
                'score': 0
            })

        elimination_mode = 'remove_pieces' if 'remove' in variant.lower() else 'gray_obstacles'

        return {
            'board': board,
            'current_player_index': 0,
            'elimination_mode': elimination_mode,
            'players': players,
            'phase': 'PLAYING',
            'winner': None,
            'last_action_text': '4-Way Chess initialized (160 active squares). Red to move.'
        }

    def _is_valid_square(self, r: int, c: int, board: List[List[Any]]) -> bool:
        if 0 <= r < 14 and 0 <= c < 14:
            return board[r][c] is not None
        return False

    def get_valid_moves(self, state: Dict[str, Any], player_index: int) -> Dict[str, Any]:
        if state['phase'] == 'GAME_OVER' or state['current_player_index'] != player_index:
            return {'moves': []}

        player = state['players'][player_index]
        if player['is_eliminated']:
            return {'moves': []}

        code = player['code']
        board = state['board']
        moves = []

        pawn_dir = {
            'r': (-1, 0),
            'b': (0, 1),
            'y': (1, 0),
            'g': (0, -1)
        }[code]

        pawn_captures = {
            'r': [(-1, -1), (-1, 1)],
            'b': [(-1, 1), (1, 1)],
            'y': [(1, -1), (1, 1)],
            'g': [(-1, -1), (1, -1)]
        }[code]

        for r in range(14):
            for c in range(14):
                piece = board[r][c]
                if not piece or not isinstance(piece, str) or piece == '.' or piece.startswith('X_'):
                    continue

                p_type, p_owner = piece.split('_')
                if p_owner != code:
                    continue

                if p_type == 'P':
                    # Forward 1
                    dr, dc = pawn_dir
                    fr, fc = r + dr, c + dc
                    if self._is_valid_square(fr, fc, board) and board[fr][fc] == '.':
                        moves.append({'from': [r, c], 'to': [fr, fc]})
                        # Double step from initial rank
                        is_start_rank = (code == 'r' and r == 12) or (code == 'y' and r == 1) or (code == 'b' and c == 1) or (code == 'g' and c == 12)
                        fr2, fc2 = r + 2 * dr, c + 2 * dc
                        if is_start_rank and self._is_valid_square(fr2, fc2, board) and board[fr2][fc2] == '.':
                            moves.append({'from': [r, c], 'to': [fr2, fc2]})

                    # Captures
                    for cr, cc in pawn_captures:
                        target_r, target_c = r + cr, c + cc
                        if self._is_valid_square(target_r, target_c, board):
                            target = board[target_r][target_c]
                            if target and target != '.' and not target.endswith(f'_{code}') and not target.startswith('X_'):
                                moves.append({'from': [r, c], 'to': [target_r, target_c]})

                elif p_type == 'N':
                    offsets = [(-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1)]
                    for dr, dc in offsets:
                        nr, nc = r + dr, c + dc
                        if self._is_valid_square(nr, nc, board):
                            target = board[nr][nc]
                            if target == '.' or (not target.endswith(f'_{code}') and not target.startswith('X_')):
                                moves.append({'from': [r, c], 'to': [nr, nc]})

                elif p_type in ['B', 'R', 'Q']:
                    dirs = []
                    if p_type in ['B', 'Q']:
                        dirs.extend([(-1,-1), (-1,1), (1,-1), (1,1)])
                    if p_type in ['R', 'Q']:
                        dirs.extend([(-1,0), (1,0), (0,-1), (0,1)])

                    for dr, dc in dirs:
                        nr, nc = r + dr, c + dc
                        while self._is_valid_square(nr, nc, board):
                            target = board[nr][nc]
                            if target == '.':
                                moves.append({'from': [r, c], 'to': [nr, nc]})
                            elif not target.endswith(f'_{code}') and not target.startswith('X_'):
                                moves.append({'from': [r, c], 'to': [nr, nc]})
                                break
                            else:
                                break
                            nr += dr
                            nc += dc

                elif p_type == 'K':
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            if dr == 0 and dc == 0: continue
                            nr, nc = r + dr, c + dc
                            if self._is_valid_square(nr, nc, board):
                                target = board[nr][nc]
                                if target == '.' or (not target.endswith(f'_{code}') and not target.startswith('X_')):
                                    moves.append({'from': [r, c], 'to': [nr, nc]})

        return {'moves': moves}

    def apply_action(self, state: Dict[str, Any], player_index: int, action: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, str]:
        if state['phase'] == 'GAME_OVER':
            return state, False, "Game is over."

        if player_index != state['current_player_index']:
            return state, False, "Not your turn."

        valid = self.get_valid_moves(state, player_index)
        from_sq = action.get('from')
        to_sq = action.get('to')

        if not from_sq or not to_sq:
            return state, False, "Invalid move payload."

        is_legal = any(m['from'] == from_sq and m['to'] == to_sq for m in valid['moves'])
        if not is_legal:
            return state, False, "Illegal move!"

        board = state['board']
        fr, fc = from_sq
        tr, tc = to_sq
        piece = board[fr][fc]
        target = board[tr][tc]

        board[fr][fc] = '.'

        # Promotion rule: Pawns entering central 8th rank or opposite territory promote to Queen
        p_type, p_owner = piece.split('_')
        if p_type == 'P':
            if (p_owner == 'r' and tr <= 5) or (p_owner == 'y' and tr >= 8) or (p_owner == 'b' and tc >= 8) or (p_owner == 'g' and tc <= 5):
                piece = f"Q_{p_owner}"

        board[tr][tc] = piece

        p_name = state['players'][player_index]['name']
        if target and target != '.' and target.startswith('K_'):
            elim_owner = target.split('_')[1]
            for p in state['players']:
                if p['code'] == elim_owner:
                    p['is_eliminated'] = True
                    state['last_action_text'] = f"⚔️ {p_name} captured {p['name']}'s King! {p['name']} is eliminated!"
                    # Apply elimination mode
                    for r in range(14):
                        for c in range(14):
                            if board[r][c] and board[r][c].endswith(f"_{elim_owner}"):
                                if state.get('elimination_mode') == 'remove_pieces':
                                    board[r][c] = '.'
                                else:
                                    board[r][c] = f"X_{elim_owner}"
        else:
            state['last_action_text'] = f"{p_name} moved piece."

        # Check surviving players
        active_players = [p for p in state['players'] if not p['is_eliminated']]
        if len(active_players) <= 1:
            state['phase'] = 'GAME_OVER'
            if len(active_players) == 1:
                state['winner'] = active_players[0]['index']
                state['last_action_text'] = f"🏆 Game Over! {active_players[0]['name']} wins 4-Way Chess!"
            return state, True, "Game Over!"

        # Clockwise turn rotation to next active player
        curr = state['current_player_index']
        for _ in range(4):
            curr = (curr + 1) % 4
            if not state['players'][curr]['is_eliminated']:
                state['current_player_index'] = curr
                break

        return state, True, "Move applied."

    def check_win_condition(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if state['phase'] == 'GAME_OVER':
            return {'winner': state['winner']}
        return None

    def serialize_state(self, state: Dict[str, Any], player_index: Optional[int] = None) -> Dict[str, Any]:
        valid_moves = {}
        if player_index is not None:
            valid_moves = self.get_valid_moves(state, player_index)

        serialized = dict(state)
        serialized['valid_moves_for_client'] = valid_moves
        return serialized
