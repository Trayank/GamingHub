import secrets
from typing import Any, Dict, List, Optional, Tuple
from .base import BaseGameEngine


# 10 Player Vibrant Color Palettes
PLAYER_COLORS = [
    {"name": "Red", "hex": "#ef4444", "bg": "bg-red-500", "border": "border-red-500", "text": "text-red-400"},
    {"name": "Blue", "hex": "#3b82f6", "bg": "bg-blue-500", "border": "border-blue-500", "text": "text-blue-400"},
    {"name": "Green", "hex": "#22c55e", "bg": "bg-green-500", "border": "border-green-500", "text": "text-green-400"},
    {"name": "Yellow", "hex": "#eab308", "bg": "bg-yellow-500", "border": "border-yellow-500", "text": "text-yellow-400"},
    {"name": "Orange", "hex": "#f97316", "bg": "bg-orange-500", "border": "border-orange-500", "text": "text-orange-400"},
    {"name": "Purple", "hex": "#a855f7", "bg": "bg-purple-500", "border": "border-purple-500", "text": "text-purple-400"},
    {"name": "Teal", "hex": "#14b8a6", "bg": "bg-teal-500", "border": "border-teal-500", "text": "text-teal-400"},
    {"name": "Pink", "hex": "#ec4899", "bg": "bg-pink-500", "border": "border-pink-500", "text": "text-pink-400"},
    {"name": "Amber", "hex": "#f59e0b", "bg": "bg-amber-500", "border": "border-amber-500", "text": "text-amber-400"},
    {"name": "Indigo", "hex": "#6366f1", "bg": "bg-indigo-500", "border": "border-indigo-500", "text": "text-indigo-400"},
]


class LudoEngine(BaseGameEngine):
    """
    Server-Authoritative Real-Time Ludo Engine for 2 to 10 Players.
    Features dynamic radial N-arm board math, 4 tokens per player,
    safe tiles, extra rolls for 6s / captures / finishes, and consecutive 6 caps.
    """
    game_id: str = "ludo"
    slug: str = "ludo"
    name: str = "Ludo Party (2-10 Players)"
    description: str = "Roll dice, race your tokens, and capture opponents on a dynamic 2 to 10 player board."
    category: str = "Party"
    icon: str = "fa-dice"
    min_players: int = 2
    max_players: int = 10

    CELLS_PER_ARM: int = 6  # Each arm contributes 6 tiles to the outer track

    def initialize_state(self, players: List[str]) -> Dict[str, Any]:
        num_players = max(2, min(len(players), 10))
        active_players = players[:num_players]
        total_outer_cells = num_players * self.CELLS_PER_ARM

        players_state = {}
        for idx, player in enumerate(active_players):
            color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]
            entry_cell = idx * self.CELLS_PER_ARM
            home_entry_cell = (entry_cell + total_outer_cells - 1) % total_outer_cells

            players_state[player] = {
                'player_index': idx,
                'color': color,
                'entry_cell': entry_cell,
                'home_entry_cell': home_entry_cell,
                'tokens': [
                    {'id': 0, 'position': 'yard', 'steps': -1},
                    {'id': 1, 'position': 'yard', 'steps': -1},
                    {'id': 2, 'position': 'yard', 'steps': -1},
                    {'id': 3, 'position': 'yard', 'steps': -1},
                ],
                'finished_count': 0,
            }

        # Safe cells: entry tiles & midpoint star tiles
        safe_cells = []
        for idx in range(num_players):
            entry = idx * self.CELLS_PER_ARM
            star = (entry + 3) % total_outer_cells
            safe_cells.extend([entry, star])
        safe_cells = list(set(safe_cells))

        return {
            'game_id': self.game_id,
            'num_players': num_players,
            'total_outer_cells': total_outer_cells,
            'safe_cells': safe_cells,
            'player_order': active_players,
            'current_turn_index': 0,
            'current_player': active_players[0],
            'dice_value': None,
            'has_rolled': False,
            'consecutive_sixes': 0,
            'legal_moves': [],  # list of token indices (0..3)
            'players': players_state,
            'winner_podium': [],
            'is_over': False,
            'last_event': 'Game Started. Roll the dice!',
        }

    def roll_dice(self, player: str, state: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Rolls a server-authoritative 1-6 dice for current player."""
        if state.get('is_over') or state.get('current_player') != player or state.get('has_rolled'):
            return state, 0

        dice_val = secrets.randbelow(6) + 1
        state['dice_value'] = dice_val
        state['has_rolled'] = True

        if dice_val == 6:
            state['consecutive_sixes'] += 1
        else:
            state['consecutive_sixes'] = 0

        # Rule: 3 consecutive 6s invalidates turn
        if state['consecutive_sixes'] >= 3:
            state['last_event'] = f"{player} rolled three consecutive 6s! Turn forfeited."
            state = self._pass_turn(state)
            return state, dice_val

        # Compute legal moves for current player
        legal_moves = self._compute_legal_moves(player, dice_val, state)
        state['legal_moves'] = legal_moves

        if not legal_moves:
            state['last_event'] = f"{player} rolled a {dice_val}, but has no legal moves."
            if dice_val != 6:
                state = self._pass_turn(state)
            else:
                # Reset has_rolled to allow extra roll for 6
                state['has_rolled'] = False
        else:
            state['last_event'] = f"{player} rolled a {dice_val}! Select a token to move."

        return state, dice_val

    def validate_move(self, player: str, move_data: Dict[str, Any], state: Dict[str, Any]) -> bool:
        if state.get('is_over') or state.get('current_player') != player:
            return False

        if not state.get('has_rolled') or state.get('dice_value') is None:
            return False

        token_index = move_data.get('token_index')
        if token_index is None or not (isinstance(token_index, int) and 0 <= token_index < 4):
            return False

        return token_index in state.get('legal_moves', [])

    def apply_move(self, player: str, move_data: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        token_index = move_data['token_index']
        dice_val = state['dice_value']
        player_info = state['players'][player]
        token = player_info['tokens'][token_index]

        captured = False
        finished = False
        earned_extra_roll = (dice_val == 6)

        # 1. Moving out of yard
        if token['position'] == 'yard' and dice_val == 6:
            token['position'] = player_info['entry_cell']
            token['steps'] = 0
            state['last_event'] = f"{player} brought token #{token_index + 1} out of the yard!"
        else:
            # 2. Moving along main outer circuit or home straight
            old_steps = token['steps']
            new_steps = old_steps + dice_val
            total_outer = state['total_outer_cells']

            if old_steps < total_outer:
                if new_steps < total_outer:
                    # Stays on main outer ring
                    token['position'] = (player_info['entry_cell'] + new_steps) % total_outer
                    token['steps'] = new_steps
                elif new_steps == total_outer + 5:
                    # Reached final home goal exactly!
                    token['position'] = 'finished'
                    token['steps'] = new_steps
                    player_info['finished_count'] += 1
                    finished = True
                    earned_extra_roll = True
                    state['last_event'] = f"🎉 {player}'s token #{token_index + 1} reached the home goal!"
                elif new_steps < total_outer + 5:
                    # Enters home straight
                    home_idx = new_steps - total_outer + 1
                    token['position'] = f"home_{home_idx}"
                    token['steps'] = new_steps
                    state['last_event'] = f"{player} moved token #{token_index + 1} into the home straight."

        # 3. Check Captures on outer circuit
        if isinstance(token['position'], int) and token['position'] not in state['safe_cells']:
            landed_cell = token['position']
            for opp_name, opp_info in state['players'].items():
                if opp_name == player:
                    continue
                for opp_t in opp_info['tokens']:
                    if opp_t['position'] == landed_cell:
                        # Capture opponent token back to yard!
                        opp_t['position'] = 'yard'
                        opp_t['steps'] = -1
                        captured = True
                        earned_extra_roll = True
                        state['last_event'] = f"⚔️ {player} captured {opp_name}'s token!"

        # 4. Check Player Victory
        if player_info['finished_count'] == 4:
            if player not in state['winner_podium']:
                state['winner_podium'].append(player)
            
            state['is_over'] = True
            state['winner'] = state['winner_podium'][0]
            state['last_event'] = f"👑 {player} HAS WON THE LUDO MATCH!"
            return state

        # 5. Handle Turn Advancement or Extra Roll
        if earned_extra_roll:
            state['has_rolled'] = False
            state['legal_moves'] = []
            state['dice_value'] = None
        else:
            state = self._pass_turn(state)

        return state

    def check_game_over(self, state: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if state.get('is_over'):
            return True, state.get('winner')
        return False, None

    def _compute_legal_moves(self, player: str, dice_val: int, state: Dict[str, Any]) -> List[int]:
        player_info = state['players'][player]
        total_outer = state['total_outer_cells']
        legal = []

        for idx, t in enumerate(player_info['tokens']):
            pos = t['position']
            if pos == 'finished':
                continue
            if pos == 'yard':
                if dice_val == 6:
                    legal.append(idx)
            else:
                steps = t['steps']
                new_steps = steps + dice_val
                # Max steps to reach home goal is total_outer + 5
                if new_steps <= total_outer + 5:
                    legal.append(idx)

        return legal

    def _pass_turn(self, state: Dict[str, Any]) -> Dict[str, Any]:
        player_order = state['player_order']
        current_idx = state['current_turn_index']
        next_idx = (current_idx + 1) % len(player_order)

        state['current_turn_index'] = next_idx
        state['current_player'] = player_order[next_idx]
        state['has_rolled'] = False
        state['dice_value'] = None
        state['consecutive_sixes'] = 0
        state['legal_moves'] = []
        return state

    def get_public_state(self, state: Dict[str, Any], player: Optional[str] = None) -> Dict[str, Any]:
        return {
            'game_id': self.game_id,
            'num_players': state.get('num_players', 2),
            'total_outer_cells': state.get('total_outer_cells', 12),
            'safe_cells': state.get('safe_cells', []),
            'player_order': state.get('player_order', []),
            'current_player': state.get('current_player'),
            'current_turn_index': state.get('current_turn_index', 0),
            'dice_value': state.get('dice_value'),
            'has_rolled': state.get('has_rolled', False),
            'legal_moves': state.get('legal_moves', []),
            'players': state.get('players', {}),
            'winner_podium': state.get('winner_podium', []),
            'is_over': state.get('is_over', False),
            'winner': state.get('winner'),
            'last_event': state.get('last_event', ''),
            'your_name': player,
            'is_your_turn': (state.get('current_player') == player) and not state.get('is_over', False),
        }


# Singleton Engine Instance
ludo_engine = LudoEngine()
