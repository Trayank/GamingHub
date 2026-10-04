import random
from typing import Dict, Any, Tuple, Optional, List
from games.base import BaseGameEngine

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

class PokerEngine(BaseGameEngine):
    """
    Server-authoritative Texas Hold'em Poker Engine.
    """

    def initialize_state(self, player_count: int, variant: str = 'default', seats_info: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        player_count = max(2, min(8, player_count))

        deck = [{'suit': s, 'rank': r, 'id': f"{r}{s}"} for s in SUITS for r in RANKS]
        random.shuffle(deck)

        players = []
        for i in range(player_count):
            name = seats_info[i]['name'] if seats_info and i < len(seats_info) else f"Player {i+1}"
            hole = [deck.pop(), deck.pop()]
            players.append({
                'id': i,
                'name': name,
                'chips': 1000,
                'current_bet': 0,
                'hole_cards': hole,
                'is_folded': False,
                'is_all_in': False
            })

        return {
            'player_count': player_count,
            'players': players,
            'deck': deck,
            'community_cards': [],
            'pot': 0,
            'current_bet': 0,
            'current_player_index': 0,
            'betting_stage': 'PREFLOP',  # PREFLOP, FLOP, TURN, RIVER, SHOWDOWN
            'phase': 'PLAYING',
            'winner': None,
            'last_action_text': 'Texas Hold\'em initialized. Pre-flop betting round.'
        }

    def get_valid_moves(self, state: Dict[str, Any], player_index: int) -> Dict[str, Any]:
        if state['phase'] == 'GAME_OVER' or state['current_player_index'] != player_index:
            return {'can_fold': False, 'can_check': False, 'can_call': False, 'can_raise': False}

        player = state['players'][player_index]
        if player['is_folded']:
            return {'can_fold': False, 'can_check': False, 'can_call': False, 'can_raise': False}

        to_call = state['current_bet'] - player['current_bet']

        return {
            'can_fold': True,
            'can_check': (to_call == 0),
            'can_call': (to_call > 0 and player['chips'] >= to_call),
            'call_amount': to_call,
            'can_raise': (player['chips'] > to_call),
            'min_raise': max(20, to_call * 2)
        }

    def apply_action(self, state: Dict[str, Any], player_index: int, action: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, str]:
        if state['phase'] == 'GAME_OVER':
            return state, False, "Game is over."

        if state['current_player_index'] != player_index:
            return state, False, "Not your turn."

        player = state['players'][player_index]
        action_type = action.get('type')
        p_name = player['name']

        if action_type == 'fold':
            player['is_folded'] = True
            state['last_action_text'] = f"{p_name} folded."
            self._advance_turn(state)
            return state, True, "Folded."

        elif action_type == 'check':
            to_call = state['current_bet'] - player['current_bet']
            if to_call > 0:
                return state, False, "Cannot check when there is a bet to call."
            state['last_action_text'] = f"{p_name} checked."
            self._advance_turn(state)
            return state, True, "Checked."

        elif action_type == 'call':
            to_call = state['current_bet'] - player['current_bet']
            amount = min(to_call, player['chips'])
            player['chips'] -= amount
            player['current_bet'] += amount
            state['pot'] += amount
            state['last_action_text'] = f"{p_name} called {amount} chips."
            self._advance_turn(state)
            return state, True, "Called."

        elif action_type == 'raise':
            raise_amount = action.get('amount', 50)
            if player['chips'] < raise_amount:
                return state, False, "Not enough chips to raise."

            player['chips'] -= raise_amount
            player['current_bet'] += raise_amount
            state['pot'] += raise_amount
            state['current_bet'] = player['current_bet']
            state['last_action_text'] = f"💵 {p_name} raised to {player['current_bet']} chips!"
            self._advance_turn(state)
            return state, True, "Raised."

        return state, False, f"Unknown action: {action_type}"

    def _advance_turn(self, state: Dict[str, Any]):
        active_players = [p for p in state['players'] if not p['is_folded']]
        if len(active_players) == 1:
            state['phase'] = 'GAME_OVER'
            state['winner'] = active_players[0]['id']
            state['last_action_text'] = f"🏆 {active_players[0]['name']} won pot of {state['pot']} chips!"
            return

        curr = state['current_player_index']
        p_count = state['player_count']
        for _ in range(p_count):
            curr = (curr + 1) % p_count
            if not state['players'][curr]['is_folded']:
                state['current_player_index'] = curr
                break

    def check_win_condition(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if state['phase'] == 'GAME_OVER':
            return {'winner': state['winner']}
        return None

    def serialize_state(self, state: Dict[str, Any], player_index: Optional[int] = None) -> Dict[str, Any]:
        valid_moves = {}
        if player_index is not None:
            valid_moves = self.get_valid_moves(state, player_index)

        serialized = dict(state)
        if player_index is not None:
            players_summary = []
            for p in state['players']:
                p_copy = dict(p)
                if p['id'] != player_index:
                    p_copy['hole_cards'] = [{'suit': '?', 'rank': '?'}, {'suit': '?', 'rank': '?'}]
                players_summary.append(p_copy)
            serialized['players'] = players_summary

        serialized['valid_moves_for_client'] = valid_moves
        return serialized
