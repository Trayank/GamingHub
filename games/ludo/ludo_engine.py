import random
from typing import Dict, Any, Tuple, Optional, List
from games.base import BaseGameEngine

DEFAULT_COLORS = [
    'red', 'blue', 'green', 'yellow', 
    'purple', 'orange', 'cyan', 'pink', 'lime', 'brown'
]

class LudoEngine(BaseGameEngine):
    """
    Complete Server-Authoritative Ludo Game Engine supporting 2 to 10 players dynamically.
    
    Board Geometry Math:
    - 2 to 4 Players: 4-quadrant layout (2 players use opposite quadrants 0 and 2).
    - 5 to 6 Players: Hexagonal polygonal board (6 arms around center).
    - 7 to 8 Players: Octagonal polygonal board (8 arms around center).
    - 9 to 10 Players: Decagonal polygonal board (10 arms around center).
    
    Track Specs:
    - Each arm consists of 6 steps along the outer circuit before turning into private 6-step Home Stretch.
    - Total main circuit steps = player_count * 6.
    - Safe spots: Start square for each player (step = p * 6) + intermediate star safe spots (step = p * 6 + 3).
    """

    ARM_LENGTH = 6
    HOME_STRETCH_LENGTH = 6

    def initialize_state(self, player_count: int, variant: str = 'default', seats_info: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        player_count = max(2, min(10, player_count))

        # Handle 2-player opposite quadrant seating if requested or default
        active_seats = list(range(player_count))
        total_arms = player_count
        if player_count == 2 and variant.lower() in ['standard', '4quadrant', 'opposite']:
            total_arms = 4
            active_seats = [0, 2]

        total_circuit_length = total_arms * self.ARM_LENGTH

        players = []
        for idx, seat_idx in enumerate(active_seats):
            color = DEFAULT_COLORS[seat_idx % len(DEFAULT_COLORS)]
            if seats_info and idx < len(seats_info) and seats_info[idx].get('color'):
                color = seats_info[idx]['color']
            name = seats_info[idx]['name'] if seats_info and idx < len(seats_info) else f"Player {idx + 1}"

            players.append({
                'id': idx,
                'seat_index': seat_idx,
                'name': name,
                'color': color,
                'start_step': seat_idx * self.ARM_LENGTH,
                'tokens': [
                    {'id': 0, 'state': 'YARD', 'pos': 0},
                    {'id': 1, 'state': 'YARD', 'pos': 0},
                    {'id': 2, 'state': 'YARD', 'pos': 0},
                    {'id': 3, 'state': 'YARD', 'pos': 0},
                ],
                'completed_tokens': 0,
                'rank': None
            })

        safe_spots = []
        for seat_idx in range(total_arms):
            start = seat_idx * self.ARM_LENGTH
            safe_spots.append(start)
            safe_spots.append((start + 3) % total_circuit_length)

        blockades_enabled = ('blockade' in variant.lower() or 'stack' in variant.lower())

        state = {
            'player_count': player_count,
            'total_arms': total_arms,
            'total_circuit_length': total_circuit_length,
            'arm_length': self.ARM_LENGTH,
            'blockades_enabled': blockades_enabled,
            'players': players,
            'current_player_index': 0,
            'dice_rolled': False,
            'dice_value': None,
            'consecutive_sixes': 0,
            'phase': 'WAITING_FOR_ROLL',  # WAITING_FOR_ROLL, WAITING_FOR_MOVE, GAME_OVER
            'safe_spots': safe_spots,
            'winner': None,
            'rankings': [],
            'last_action_text': f"Ludo match started ({player_count} players). Player 1 to roll."
        }
        return state

    def _get_absolute_track_pos(self, seat_index: int, relative_pos: int, total_circuit: int) -> int:
        start_step = seat_index * self.ARM_LENGTH
        return (start_step + relative_pos) % total_circuit

    def _get_tokens_at_abs_step(self, state: Dict[str, Any], abs_step: int) -> List[Tuple[int, Dict[str, Any]]]:
        """Returns list of (player_idx, token_dict) at specified absolute circuit step."""
        result = []
        total_circuit = state['total_circuit_length']
        for p_idx, player in enumerate(state['players']):
            for token in player['tokens']:
                if token['state'] == 'TRACK':
                    t_abs = self._get_absolute_track_pos(player['seat_index'], token['pos'], total_circuit)
                    if t_abs == abs_step:
                        result.append((p_idx, token))
        return result

    def get_valid_moves(self, state: Dict[str, Any], player_index: int) -> Dict[str, Any]:
        if state['phase'] == 'GAME_OVER' or state['current_player_index'] != player_index:
            return {'can_roll': False, 'valid_token_ids': [], 'move_previews': {}}

        if state['phase'] == 'WAITING_FOR_ROLL':
            return {'can_roll': True, 'valid_token_ids': [], 'move_previews': {}}

        dice = state['dice_value']
        player = state['players'][player_index]
        valid_token_ids = []
        move_previews = {}
        total_circuit = state['total_circuit_length']
        max_track_steps = total_circuit - 1

        for token in player['tokens']:
            t_state = token['state']
            t_pos = token['pos']
            can_move = False
            dest_info = None

            if t_state == 'YARD':
                if dice == 6:
                    can_move = True
                    start_abs = self._get_absolute_track_pos(player['seat_index'], 0, total_circuit)
                    dest_info = {'type': 'TRACK', 'pos': 0, 'abs_pos': start_abs}
            elif t_state == 'TRACK':
                new_pos = t_pos + dice
                if new_pos <= max_track_steps:
                    # Check blockade along path if blockades enabled
                    path_blocked = False
                    if state['blockades_enabled']:
                        for step in range(t_pos + 1, new_pos + 1):
                            step_abs = self._get_absolute_track_pos(player['seat_index'], step, total_circuit)
                            occupants = self._get_tokens_at_abs_step(state, step_abs)
                            # Blockade = 2+ tokens of same non-player color
                            opp_tokens = [tok for p_i, tok in occupants if p_i != player_index]
                            if len(opp_tokens) >= 2:
                                path_blocked = True
                                break

                    if not path_blocked:
                        can_move = True
                        dest_abs = self._get_absolute_track_pos(player['seat_index'], new_pos, total_circuit)
                        dest_info = {'type': 'TRACK', 'pos': new_pos, 'abs_pos': dest_abs}
                else:
                    # Turns into private Home Stretch
                    stretch_pos = new_pos - max_track_steps - 1
                    if stretch_pos < self.HOME_STRETCH_LENGTH:
                        can_move = True
                        dest_info = {'type': 'STRETCH', 'pos': stretch_pos}

            elif t_state == 'STRETCH':
                new_stretch_pos = t_pos + dice
                if new_stretch_pos < self.HOME_STRETCH_LENGTH:
                    can_move = True
                    dest_info = {'type': 'STRETCH' if new_stretch_pos < self.HOME_STRETCH_LENGTH - 1 else 'HOME', 'pos': new_stretch_pos}

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

            dice = random.randint(1, 6)
            state['dice_value'] = dice
            state['dice_rolled'] = True

            if dice == 6:
                state['consecutive_sixes'] += 1
            else:
                state['consecutive_sixes'] = 0

            # 3 consecutive sixes forfeit turn
            if state['consecutive_sixes'] == 3:
                p_name = state['players'][player_index]['name']
                state['consecutive_sixes'] = 0
                state['dice_rolled'] = False
                state['dice_value'] = None
                state['phase'] = 'WAITING_FOR_ROLL'
                state['last_action_text'] = f"3 consecutive 6s rolled by {p_name}! Turn forfeited."
                self._advance_turn(state)
                return state, True, "3 consecutive sixes. Turn forfeited."

            valid_moves = self.get_valid_moves(state, player_index)
            if not valid_moves['valid_token_ids']:
                p_name = state['players'][player_index]['name']
                state['last_action_text'] = f"{p_name} rolled {dice}. No valid moves available."
                state['dice_rolled'] = False
                state['dice_value'] = None
                state['phase'] = 'WAITING_FOR_ROLL'
                self._advance_turn(state)
                return state, True, f"Rolled {dice}, but no valid moves available."

            state['phase'] = 'WAITING_FOR_MOVE'
            state['last_action_text'] = f"{state['players'][player_index]['name']} rolled {dice}."
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
            total_circuit = state['total_circuit_length']
            max_track_steps = total_circuit - 1

            if token['state'] == 'YARD':
                token['state'] = 'TRACK'
                token['pos'] = 0
                state['last_action_text'] = f"{player['name']} brought token out of yard onto start!"
            elif token['state'] == 'TRACK':
                new_pos = token['pos'] + dice
                if new_pos <= max_track_steps:
                    token['pos'] = new_pos
                else:
                    token['state'] = 'STRETCH'
                    token['pos'] = new_pos - max_track_steps - 1
                    if token['pos'] == self.HOME_STRETCH_LENGTH - 1:
                        token['state'] = 'HOME'
                        player['completed_tokens'] += 1
                        grant_extra_turn = True
                        state['last_action_text'] = f"🎯 {player['name']}'s token reached HOME!"
            elif token['state'] == 'STRETCH':
                token['pos'] += dice
                if token['pos'] == self.HOME_STRETCH_LENGTH - 1:
                    token['state'] = 'HOME'
                    player['completed_tokens'] += 1
                    grant_extra_turn = True
                    state['last_action_text'] = f"🎯 {player['name']}'s token reached HOME!"

            # Capture handling
            if token['state'] == 'TRACK':
                abs_pos = self._get_absolute_track_pos(player['seat_index'], token['pos'], total_circuit)
                if abs_pos not in state['safe_spots']:
                    occupants = self._get_tokens_at_abs_step(state, abs_pos)
                    for opp_idx, opp_tok in occupants:
                        if opp_idx != player_index:
                            opp_tok['state'] = 'YARD'
                            opp_tok['pos'] = 0
                            captured_opponent = True
                            grant_extra_turn = True
                            opp_name = state['players'][opp_idx]['name']
                            state['last_action_text'] = f"💥 {player['name']} captured {opp_name}'s token!"

            # Ranking calculation
            if player['completed_tokens'] == 4 and player['rank'] is None:
                rank = len(state['rankings']) + 1
                player['rank'] = rank
                state['rankings'].append({
                    'player_index': player_index,
                    'name': player['name'],
                    'rank': rank
                })
                if len(state['rankings']) == 1:
                    state['winner'] = player_index
                    state['last_action_text'] = f"🏆 {player['name']} finished 1st Place!"

            # Win condition check
            win_info = self.check_win_condition(state)
            if win_info:
                state['phase'] = 'GAME_OVER'
                state['last_action_text'] = f"🏁 Match Over! Winner is {state['players'][win_info['winner_index']]['name']}."
                return state, True, "Game Over!"

            # Turn transition
            if grant_extra_turn and player['completed_tokens'] < 4:
                state['phase'] = 'WAITING_FOR_ROLL'
                state['dice_rolled'] = False
                state['dice_value'] = None
                state['last_action_text'] += " Bonus turn granted!"
            else:
                state['phase'] = 'WAITING_FOR_ROLL'
                state['dice_rolled'] = False
                state['dice_value'] = None
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
