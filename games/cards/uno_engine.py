import random
from typing import Dict, Any, Tuple, Optional, List
from games.base import BaseGameEngine

COLORS = ['red', 'blue', 'green', 'yellow']

class UnoEngine(BaseGameEngine):
    """
    Server-authoritative Uno / Color Match Card Game Engine.
    """

    def initialize_state(self, player_count: int, variant: str = 'default', seats_info: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        player_count = max(2, min(8, player_count))

        # Build deck of 108 Uno cards
        deck = []
        for color in COLORS:
            deck.append({'color': color, 'value': '0', 'id': f"{color}_0"})
            for v in ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'Skip', 'Reverse', '+2']:
                deck.append({'color': color, 'value': v, 'id': f"{color}_{v}_1"})
                deck.append({'color': color, 'value': v, 'id': f"{color}_{v}_2"})
        for _ in range(4):
            deck.append({'color': 'wild', 'value': 'Wild', 'id': f"wild_{_}"})
            deck.append({'color': 'wild', 'value': '+4', 'id': f"wild_4_{_}"})

        random.shuffle(deck)

        # Deal 7 cards to each player
        players = []
        for i in range(player_count):
            name = seats_info[i]['name'] if seats_info and i < len(seats_info) else f"Player {i+1}"
            hand = [deck.pop() for _ in range(7)]
            players.append({
                'id': i,
                'name': name,
                'hand': hand,
                'score': 0,
                'has_said_uno': False
            })

        # Draw top non-wild card to start discard pile
        discard_pile = []
        top_card = deck.pop()
        while top_card['color'] == 'wild':
            deck.append(top_card)
            random.shuffle(deck)
            top_card = deck.pop()
        discard_pile.append(top_card)

        return {
            'player_count': player_count,
            'players': players,
            'deck': deck,
            'discard_pile': discard_pile,
            'top_card': top_card,
            'active_color': top_card['color'],
            'current_player_index': 0,
            'direction': 1,  # 1 for clockwise, -1 for counter-clockwise
            'phase': 'PLAYING',
            'winner': None,
            'last_action_text': 'Uno game initialized. 7 cards dealt.'
        }

    def get_valid_moves(self, state: Dict[str, Any], player_index: int) -> Dict[str, Any]:
        if state['phase'] == 'GAME_OVER' or state['current_player_index'] != player_index:
            return {'playable_card_ids': [], 'can_draw': False}

        player = state['players'][player_index]
        top = state['top_card']
        active_color = state['active_color']

        playable = []
        for card in player['hand']:
            if card['color'] == 'wild' or card['color'] == active_color or card['value'] == top['value']:
                playable.append(card['id'])

        return {
            'playable_card_ids': playable,
            'can_draw': True
        }

    def apply_action(self, state: Dict[str, Any], player_index: int, action: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, str]:
        if state['phase'] == 'GAME_OVER':
            return state, False, "Game is over."

        if state['current_player_index'] != player_index:
            return state, False, "Not your turn."

        action_type = action.get('type')
        player = state['players'][player_index]

        if action_type == 'play_card':
            card_id = action.get('card_id')
            chosen_color = action.get('color', 'red')

            card_idx = next((i for i, c in enumerate(player['hand']) if c['id'] == card_id), None)
            if card_idx is None:
                return state, False, "Card not in hand."

            valid = self.get_valid_moves(state, player_index)
            if card_id not in valid['playable_card_ids']:
                return state, False, "Cannot play this card."

            card = player['hand'].pop(card_idx)
            state['discard_pile'].append(card)
            state['top_card'] = card

            if card['color'] == 'wild':
                state['active_color'] = chosen_color
            else:
                state['active_color'] = card['color']

            # Handle action cards
            val = card['value']
            p_name = player['name']
            state['last_action_text'] = f"{p_name} played {card['value']} ({state['active_color']})."

            if val == 'Reverse':
                state['direction'] *= -1
            elif val == 'Skip':
                self._advance_turn(state)
            elif val == '+2':
                next_p = self._get_next_player_index(state)
                self._draw_cards(state, next_p, 2)
                self._advance_turn(state)
            elif val == '+4':
                next_p = self._get_next_player_index(state)
                self._draw_cards(state, next_p, 4)
                self._advance_turn(state)

            # Win check
            if len(player['hand']) == 0:
                state['phase'] = 'GAME_OVER'
                state['winner'] = player_index
                state['last_action_text'] = f"🏆 {p_name} played their last card and won Uno!"
                return state, True, "Uno Victory!"

            self._advance_turn(state)
            return state, True, "Card played."

        elif action_type == 'draw_card':
            if len(state['deck']) == 0:
                # Reshuffle discard pile into deck
                top = state['discard_pile'].pop()
                state['deck'] = state['discard_pile']
                random.shuffle(state['deck'])
                state['discard_pile'] = [top]

            if len(state['deck']) > 0:
                drawn = state['deck'].pop()
                player['hand'].append(drawn)
                state['last_action_text'] = f"{player['name']} drew a card."

            self._advance_turn(state)
            return state, True, "Card drawn."

        return state, False, f"Unknown action: {action_type}"

    def _get_next_player_index(self, state: Dict[str, Any]) -> int:
        p_count = state['player_count']
        return (state['current_player_index'] + state['direction']) % p_count

    def _advance_turn(self, state: Dict[str, Any]):
        state['current_player_index'] = self._get_next_player_index(state)

    def _draw_cards(self, state: Dict[str, Any], player_idx: int, count: int):
        for _ in range(count):
            if len(state['deck']) == 0 and len(state['discard_pile']) > 1:
                top = state['discard_pile'].pop()
                state['deck'] = state['discard_pile']
                random.shuffle(state['deck'])
                state['discard_pile'] = [top]
            if len(state['deck']) > 0:
                state['players'][player_idx]['hand'].append(state['deck'].pop())

    def check_win_condition(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if state['phase'] == 'GAME_OVER':
            return {'winner': state['winner']}
        return None

    def serialize_state(self, state: Dict[str, Any], player_index: Optional[int] = None) -> Dict[str, Any]:
        valid_moves = {}
        if player_index is not None:
            valid_moves = self.get_valid_moves(state, player_index)

        serialized = dict(state)
        # Hide opponents' hands in serialized state
        if player_index is not None:
            players_summary = []
            for p in state['players']:
                p_copy = dict(p)
                if p['id'] != player_index:
                    p_copy['hand_count'] = len(p['hand'])
                    p_copy['hand'] = []  # Hide card values
                players_summary.append(p_copy)
            serialized['players'] = players_summary

        serialized['valid_moves_for_client'] = valid_moves
        return serialized
