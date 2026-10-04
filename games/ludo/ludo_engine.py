import secrets
from typing import Dict, Any, Tuple, Optional, List
from games.base import BaseGameEngine

DEFAULT_COLORS = [
    'red', 'blue', 'yellow', 'green', 
    'purple', 'orange', 'cyan', 'pink', 'lime', 'brown'
]

# 52 main circuit track tiles for 4-quadrant / 15x15 Ludo board (0-indexed)
# Entry tiles: Red=0, Blue=13, Yellow=26, Green=39
# Safe stars: Red Star=7, Blue Star=20, Yellow Star=33, Green Star=46
SAFE_SPOTS_52 = [0, 7, 13, 20, 26, 33, 39, 46]

class LudoEngine(BaseGameEngine):
    """
    Server-Authoritative Ludo Game Engine matching exact Ludo King mechanics and board geometry.
    
    15x15 Board Circuit Specs:
    - 52 main circuit track tiles (0..51)
    - 5 private Home Stretch tiles per player leading to HOME (step 56)
    - 2-Player Mode: Opposite diagonal bases (Red vs Yellow / Seat 0 vs Seat 2)
    - Cryptographic fair dice rolling using `secrets.randbelow(6) + 1`
    - Turn rules: 3 consecutive 6s penalty, knockouts & bonus rolls, auto-pass / auto-move
    """

    TOTAL_CIRCUIT_LENGTH = 52
    HOME_STRETCH_LENGTH = 5

    def initialize_state(self, player_count: int, variant: str = 'default', seats_info: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        player_count = max(2, min(10, player_count))

        # Seating configuration:
        # In 2-Player (1v1) Mode, players ALWAYS use opposite diagonal bases on full 15x15 cross board:
        # Player 0: Red (Seat 0, Start offset 0) vs Player 1: Yellow (Seat 2, Start offset 26)
        if player_count == 2:
            total_arms = 4
            active_seats = [0, 2]
            if seats_info and len(seats_info) > 0:
                first_color = str(seats_info[0].get('color', 'red')).lower()
                if first_color == 'blue':
                    active_seats = [1, 3] # Blue vs Green
                elif first_color == 'green':
                    active_seats = [3, 1]
                elif first_color == 'yellow':
                    active_seats = [2, 0]
                else:
                    active_seats = [0, 2]
        else:
            total_arms = max(4, player_count)
            active_seats = list(range(player_count))

        players = []
        for idx, seat_idx in enumerate(active_seats):
            default_color = DEFAULT_COLORS[seat_idx % len(DEFAULT_COLORS)]
            color = seats_info[idx].get('color', default_color) if seats_info and idx < len(seats_info) else default_color
            name = seats_info[idx]['name'] if seats_info and idx < len(seats_info) else f"Player {idx + 1}"

            # Start step offset on 52-tile circuit for 4-quadrant layout:
            # Seat 0 (Red): 0
            # Seat 1 (Blue): 13
            # Seat 2 (Yellow): 26
            # Seat 3 (Green): 39
            start_step = (seat_idx % 4) * 13

            players.append({
                'id': idx,
                'seat_index': seat_idx,
                'name': name,
                'color': color,
                'start_step': start_step,
                'tokens': [
                    {'id': 0, 'state': 'YARD', 'pos': 0},
                    {'id': 1, 'state': 'YARD', 'pos': 0},
                    {'id': 2, 'state': 'YARD', 'pos': 0},
                    {'id': 3, 'state': 'YARD', 'pos': 0},
                ],
                'completed_tokens': 0,
                'rank': None
            })

        blockades_enabled = ('blockade' in variant.lower() or 'stack' in variant.lower())

        state = {
            'player_count': player_count,
            'total_arms': total_arms,
            'total_circuit_length': self.TOTAL_CIRCUIT_LENGTH,
            'home_stretch_length': self.HOME_STRETCH_LENGTH,
            'blockades_enabled': blockades_enabled,
            'players': players,
            'current_player_index': 0,
            'dice_rolled': False,
            'dice_value': None,
            'consecutive_sixes': 0,
            'phase': 'WAITING_FOR_ROLL',  # WAITING_FOR_ROLL, WAITING_FOR_MOVE, GAME_OVER
            'safe_spots': SAFE_SPOTS_52,
            'winner': None,
            'rankings': [],
            'last_action_text': f"Ludo match started ({player_count} players). {players[0]['name']}'s turn to roll."
        }
        return state

    def _get_absolute_track_pos(self, seat_index: int, relative_pos: int) -> int:
        start_offset = (seat_index % 4) * 13
        return (start_offset + relative_pos) % self.TOTAL_CIRCUIT_LENGTH

    def _get_tokens_at_abs_step(self, state: Dict[str, Any], abs_step: int) -> List[Tuple[int, Dict[str, Any]]]:
        """Returns list of (player_idx, token_dict) at specified absolute circuit step."""
        result = []
        for p_idx, player in enumerate(state['players']):
            for token in player['tokens']:
                if token['state'] == 'TRACK':
                    t_abs = self._get_absolute_track_pos(player['seat_index'], token['pos'])
                    if t_abs == abs_step:
                        result.append((p_idx, token))
        return result

    def get_valid_moves(self, state: Dict[str, Any], player_index: int) -> Dict[str, Any]:
        if state['phase'] == 'GAME_OVER' or state['current_player_index'] != player_index:
            return {'can_roll': False, 'valid_token_ids': [], 'move_previews': {}}

        if state['phase'] == 'WAITING_FOR_ROLL':
            return {'can_roll': True, 'valid_token_ids': [], 'move_previews': {}}

        dice = state['dice_value']
        if dice is None:
            return {'can_roll': False, 'valid_token_ids': [], 'move_previews': {}}

        player = state['players'][player_index]
        valid_token_ids = []
        move_previews = {}

        for token in player['tokens']:
            t_state = token['state']
            t_pos = token['pos']
            can_move = False
            dest_info = None

            if t_state == 'YARD':
                if dice == 6:
                    can_move = True
                    start_abs = self._get_absolute_track_pos(player['seat_index'], 0)
                    dest_info = {'type': 'TRACK', 'pos': 0, 'abs_pos': start_abs}
            elif t_state == 'TRACK':
                new_pos = t_pos + dice
                if new_pos <= 50:
                    can_move = True
                    dest_abs = self._get_absolute_track_pos(player['seat_index'], new_pos)
                    dest_info = {'type': 'TRACK', 'pos': new_pos, 'abs_pos': dest_abs}
                else:
                    # Enters private Home Stretch
                    stretch_pos = new_pos - 51
                    if stretch_pos < self.HOME_STRETCH_LENGTH:
                        can_move = True
                        dest_info = {'type': 'STRETCH', 'pos': stretch_pos}
                    elif stretch_pos == self.HOME_STRETCH_LENGTH:
                        can_move = True
                        dest_info = {'type': 'HOME', 'pos': 5}

            elif t_state == 'STRETCH':
                new_stretch_pos = t_pos + dice
                if new_stretch_pos < self.HOME_STRETCH_LENGTH:
                    can_move = True
                    dest_info = {'type': 'STRETCH', 'pos': new_stretch_pos}
                elif new_stretch_pos == self.HOME_STRETCH_LENGTH:
                    can_move = True
                    dest_info = {'type': 'HOME', 'pos': 5}

            if can_move:
                valid_token_ids.append(token['id'])
                move_previews[token['id']] = dest_info

        return {
            'can_roll': False,
            'valid_token_ids': valid_token_ids,
            'move_previews': move_previews
        }

    def apply_action(self, state: Dict[str, Any], player_index: int, action: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, str]:
        if state['phase'] == 'GAME_OVER':
            return state, False, "Game is already over."

        if state['current_player_index'] != player_index:
            return state, False, "Not your turn."

        action_type = action.get('type')

        if action_type == 'roll_dice':
            if state['phase'] != 'WAITING_FOR_ROLL':
                return state, False, "Dice already rolled."

            # Server-authoritative fair cryptographic roll
            dice = secrets.randbelow(6) + 1
            state['dice_value'] = dice
            state['dice_rolled'] = True

            p_name = state['players'][player_index]['name']

            if dice == 6:
                state['consecutive_sixes'] += 1
            else:
                state['consecutive_sixes'] = 0

            # 3 consecutive sixes forfeit turn
            if state['consecutive_sixes'] == 3:
                state['consecutive_sixes'] = 0
                state['dice_rolled'] = False
                state['dice_value'] = None
                state['phase'] = 'WAITING_FOR_ROLL'
                state['last_action_text'] = f"⚠️ 3 consecutive 6s rolled by {p_name}! Turn forfeited."
                self._advance_turn(state)
                return state, True, "3 consecutive sixes. Turn forfeited."

            valid_moves = self.get_valid_moves(state, player_index)
            if not valid_moves['valid_token_ids']:
                state['last_action_text'] = f"{p_name} rolled {dice}. No valid moves available."
                state['dice_rolled'] = False
                state['dice_value'] = None
                state['phase'] = 'WAITING_FOR_ROLL'
                self._advance_turn(state)
                return state, True, f"Rolled {dice}, but no valid moves available."

            state['phase'] = 'WAITING_FOR_MOVE'
            state['last_action_text'] = f"{p_name} rolled {dice}."
            return state, True, f"Rolled {dice}."

        elif action_type == 'move_piece':
            if state['phase'] != 'WAITING_FOR_MOVE':
                return state, False, "Must roll dice before moving."

            token_id = action.get('token_id')
            if token_id is None or not isinstance(token_id, int):
                return state, False, "Invalid token_id specified."

            valid_moves = self.get_valid_moves(state, player_index)
            if token_id not in valid_moves['valid_token_ids']:
                return state, False, "This token cannot be moved."

            dice = state['dice_value']
            player = state['players'][player_index]
            token = player['tokens'][token_id]

            grant_extra_turn = (dice == 6)
            captured_opponent = False
            p_name = player['name']

            if token['state'] == 'YARD':
                token['state'] = 'TRACK'
                token['pos'] = 0
                state['last_action_text'] = f"{p_name} brought token out of yard onto start tile!"
            elif token['state'] == 'TRACK':
                new_pos = token['pos'] + dice
                if new_pos <= 50:
                    token['pos'] = new_pos
                    state['last_action_text'] = f"{p_name} moved token {dice} steps."
                else:
                    stretch_pos = new_pos - 51
                    if stretch_pos < self.HOME_STRETCH_LENGTH:
                        token['state'] = 'STRETCH'
                        token['pos'] = stretch_pos
                        state['last_action_text'] = f"{p_name}'s token entered the Home Stretch!"
                    elif stretch_pos == self.HOME_STRETCH_LENGTH:
                        token['state'] = 'HOME'
                        token['pos'] = 5
                        player['completed_tokens'] += 1
                        grant_extra_turn = True
                        state['last_action_text'] = f"🎯 {p_name}'s token reached HOME!"
            elif token['state'] == 'STRETCH':
                new_stretch_pos = token['pos'] + dice
                if new_stretch_pos < self.HOME_STRETCH_LENGTH:
                    token['pos'] = new_stretch_pos
                    state['last_action_text'] = f"{p_name} moved token along Home Stretch."
                elif new_stretch_pos == self.HOME_STRETCH_LENGTH:
                    token['state'] = 'HOME'
                    token['pos'] = 5
                    player['completed_tokens'] += 1
                    grant_extra_turn = True
                    state['last_action_text'] = f"🎯 {p_name}'s token reached HOME!"

            # Knockout / Capture handling
            if token['state'] == 'TRACK':
                abs_pos = self._get_absolute_track_pos(player['seat_index'], token['pos'])
                if abs_pos not in SAFE_SPOTS_52:
                    occupants = self._get_tokens_at_abs_step(state, abs_pos)
                    for opp_idx, opp_tok in occupants:
                        if opp_idx != player_index:
                            opp_tok['state'] = 'YARD'
                            opp_tok['pos'] = 0
                            captured_opponent = True
                            grant_extra_turn = True
                            opp_name = state['players'][opp_idx]['name']
                            state['last_action_text'] = f"💥 {p_name} captured {opp_name}'s token!"

            # Check if player completed all 4 tokens
            if player['completed_tokens'] == 4 and player['rank'] is None:
                rank = len(state['rankings']) + 1
                player['rank'] = rank
                state['rankings'].append({
                    'player_index': player_index,
                    'name': p_name,
                    'rank': rank
                })
                if len(state['rankings']) == 1:
                    state['winner'] = player_index
                    state['last_action_text'] = f"🏆 {p_name} finished 1st Place!"

            # Check overall win condition
            win_info = self.check_win_condition(state)
            if win_info:
                state['phase'] = 'GAME_OVER'
                state['last_action_text'] = f"🏁 Match Over! Winner is {state['players'][win_info['winner_index']]['name']}."
                return state, True, "Game Over!"

            # Turn transition logic
            if grant_extra_turn and player['completed_tokens'] < 4:
                state['phase'] = 'WAITING_FOR_ROLL'
                state['dice_rolled'] = False
                state['dice_value'] = None
                state['last_action_text'] += " Bonus turn granted!"
            else:
                state['phase'] = 'WAITING_FOR_ROLL'
                state['dice_rolled'] = False
                state['dice_value'] = None
                state['consecutive_sixes'] = 0
                self._advance_turn(state)

            return state, True, "Piece moved."

        return state, False, f"Unknown action: {action_type}"

    def _advance_turn(self, state: Dict[str, Any]):
        p_count = len(state['players'])
        current = state['current_player_index']
        for _ in range(p_count):
            current = (current + 1) % p_count
            if state['players'][current]['completed_tokens'] < 4:
                state['current_player_index'] = current
                return

    def check_win_condition(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        active_players = [p for p in state['players'] if p['completed_tokens'] < 4]
        if len(active_players) <= 1 and len(state['rankings']) > 0:
            return {
                'winner_index': state['rankings'][0]['player_index'],
                'rankings': state['rankings']
            }
        return None

    def serialize_state(self, state: Dict[str, Any], player_index: Optional[int] = None) -> Dict[str, Any]:
        valid_moves = {}
        if player_index is not None:
            valid_moves = self.get_valid_moves(state, player_index)

        serialized = dict(state)
        serialized['valid_moves_for_client'] = valid_moves
        return serialized
