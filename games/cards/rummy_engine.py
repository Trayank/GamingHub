import random
from typing import Dict, Any, Tuple, Optional, List
from games.base import BaseGameEngine

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

class RummyEngine(BaseGameEngine):
    """
    Server-authoritative Indian / Gin Rummy Engine.
    """

    def initialize_state(self, player_count: int, variant: str = 'default', seats_info: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        player_count = max(2, min(6, player_count))

        deck = [{'suit': s, 'rank': r, 'id': f"{r}{s}"} for s in SUITS for r in RANKS] * 2
        random.shuffle(deck)

        players = []
        for i in range(player_count):
            name = seats_info[i]['name'] if seats_info and i < len(seats_info) else f"Player {i+1}"
            hand = [deck.pop() for _ in range(13)]
            players.append({
                'id': i,
                'name': name,
                'hand': hand,
                'has_drawn': False
            })

        discard_pile = [deck.pop()]

        return {
            'player_count': player_count,
            'players': players,
            'deck': deck,
            'discard_pile': discard_pile,
            'current_player_index': 0,
            'phase': 'PLAYING',
            'winner': None,
            'last_action_text': 'Rummy initialized. 13 cards dealt to each player.'
        }

    def get_valid_moves(self, state: Dict[str, Any], player_index: int) -> Dict[str, Any]:
        if state['phase'] == 'GAME_OVER' or state['current_player_index'] != player_index:
            return {'can_draw': False, 'can_discard': False}

        player = state['players'][player_index]
        return {
            'can_draw': not player['has_drawn'],
            'can_discard': player['has_drawn']
        }

    def apply_action(self, state: Dict[str, Any], player_index: int, action: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, str]:
        if state['phase'] == 'GAME_OVER':
            return state, False, "Game is over."

        if state['current_player_index'] != player_index:
            return state, False, "Not your turn."

        action_type = action.get('type')
        player = state['players'][player_index]

        if action_type == 'draw_card':
            if player['has_drawn']:
                return state, False, "Already drawn a card this turn."

            from_discard = action.get('from_discard', False)
            if from_discard and len(state['discard_pile']) > 0:
                card = state['discard_pile'].pop()
            else:
                card = state['deck'].pop()

            player['hand'].append(card)
            player['has_drawn'] = True
            state['last_action_text'] = f"{player['name']} drew a card."
            return state, True, "Card drawn."

        elif action_type == 'discard_card':
            if not player['has_drawn']:
                return state, False, "Must draw a card before discarding."

            card_id = action.get('card_id')
            card_idx = next((i for i, c in enumerate(player['hand']) if c['id'] == card_id), None)
            if card_idx is None:
                return state, False, "Card not in hand."

            card = player['hand'].pop(card_idx)
            state['discard_pile'].append(card)
            player['has_drawn'] = False

            state['last_action_text'] = f"{player['name']} discarded {card['rank']}{card['suit']}."
            self._advance_turn(state)
            return state, True, "Card discarded."

        return state, False, f"Unknown action: {action_type}"

    def _advance_turn(self, state: Dict[str, Any]):
        state['current_player_index'] = (state['current_player_index'] + 1) % state['player_count']

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
                    p_copy['hand_count'] = len(p['hand'])
                    p_copy['hand'] = []
                players_summary.append(p_copy)
            serialized['players'] = players_summary

        serialized['valid_moves_for_client'] = valid_moves
        return serialized
