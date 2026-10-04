import random
from typing import Dict, Any, Tuple, Optional, List
from games.base import BaseGameEngine

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

class BlackjackEngine(BaseGameEngine):
    """
    Server-authoritative Blackjack Engine.
    """

    def initialize_state(self, player_count: int, variant: str = 'default', seats_info: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        player_count = max(1, min(7, player_count))

        deck = [{'suit': s, 'rank': r, 'id': f"{r}{s}"} for s in SUITS for r in RANKS] * 4
        random.shuffle(deck)

        players = []
        for i in range(player_count):
            name = seats_info[i]['name'] if seats_info and i < len(seats_info) else f"Player {i+1}"
            cards = [deck.pop(), deck.pop()]
            players.append({
                'id': i,
                'name': name,
                'cards': cards,
                'score': self._calculate_hand_value(cards),
                'is_busted': False,
                'is_stood': False
            })

        dealer_cards = [deck.pop(), deck.pop()]

        return {
            'player_count': player_count,
            'players': players,
            'dealer': {
                'cards': dealer_cards,
                'visible_score': self._calculate_hand_value([dealer_cards[0]])
            },
            'deck': deck,
            'current_player_index': 0,
            'phase': 'PLAYING',
            'winner': None,
            'last_action_text': 'Blackjack initialized. Dealt 2 cards to all players.'
        }

    def _calculate_hand_value(self, cards: List[Dict[str, str]]) -> int:
        val = 0
        aces = 0
        for c in cards:
            r = c['rank']
            if r in ['J', 'Q', 'K']:
                val += 10
            elif r == 'A':
                aces += 1
                val += 11
            else:
                val += int(r)

        while val > 21 and aces > 0:
            val -= 10
            aces -= 1
        return val

    def get_valid_moves(self, state: Dict[str, Any], player_index: int) -> Dict[str, Any]:
        if state['phase'] == 'GAME_OVER' or state['current_player_index'] != player_index:
            return {'can_hit': False, 'can_stand': False}

        player = state['players'][player_index]
        if player['is_busted'] or player['is_stood']:
            return {'can_hit': False, 'can_stand': False}

        return {'can_hit': True, 'can_stand': True}

    def apply_action(self, state: Dict[str, Any], player_index: int, action: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, str]:
        if state['phase'] == 'GAME_OVER':
            return state, False, "Game is over."

        if state['current_player_index'] != player_index:
            return state, False, "Not your turn."

        action_type = action.get('type')
        player = state['players'][player_index]

        if action_type == 'hit':
            card = state['deck'].pop()
            player['cards'].append(card)
            player['score'] = self._calculate_hand_value(player['cards'])

            if player['score'] > 21:
                player['is_busted'] = True
                state['last_action_text'] = f"💥 {player['name']} drew {card['rank']}{card['suit']} and BUSTED ({player['score']})!"
                self._advance_turn(state)
            else:
                state['last_action_text'] = f"{player['name']} hit and received {card['rank']}{card['suit']} (Total: {player['score']})."

            return state, True, "Hit action applied."

        elif action_type == 'stand':
            player['is_stood'] = True
            state['last_action_text'] = f"{player['name']} stood at {player['score']}."
            self._advance_turn(state)
            return state, True, "Stood."

        return state, False, f"Unknown action: {action_type}"

    def _advance_turn(self, state: Dict[str, Any]):
        curr = state['current_player_index']
        p_count = state['player_count']

        if curr < p_count - 1:
            state['current_player_index'] += 1
        else:
            # All players done -> Dealer plays
            dealer = state['dealer']
            while self._calculate_hand_value(dealer['cards']) < 17:
                dealer['cards'].append(state['deck'].pop())

            dealer_score = self._calculate_hand_value(dealer['cards'])
            state['phase'] = 'GAME_OVER'
            state['last_action_text'] = f"Dealer finished with score: {dealer_score}."

    def check_win_condition(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if state['phase'] == 'GAME_OVER':
            return {'dealer_score': self._calculate_hand_value(state['dealer']['cards'])}
        return None

    def serialize_state(self, state: Dict[str, Any], player_index: Optional[int] = None) -> Dict[str, Any]:
        valid_moves = {}
        if player_index is not None:
            valid_moves = self.get_valid_moves(state, player_index)

        serialized = dict(state)
        serialized['valid_moves_for_client'] = valid_moves
        return serialized
