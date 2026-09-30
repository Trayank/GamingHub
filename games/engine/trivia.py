import time
import re
from typing import Dict, Any, List, Optional, Tuple
from .base import BaseGameEngine


# Built-in 5-Round Question Bank
TRIVIA_QUESTIONS = [
    {
        "id": 1,
        "question": "Which programming language was created by Guido van Rossum in 1991?",
        "options": ["Java", "Python", "C++", "JavaScript"],
        "correct_index": 1,
        "explanation": "Guido van Rossum created Python and released it in 1991."
    },
    {
        "id": 2,
        "question": "What protocol powers real-time full-duplex communication over WebSockets?",
        "options": ["HTTP/1.1", "WS / WSS", "FTP", "SMTP"],
        "correct_index": 1,
        "explanation": "WebSockets use the ws:// and wss:// protocols."
    },
    {
        "id": 3,
        "question": "Which in-memory data structure store is widely used as a Django Channels layer?",
        "options": ["PostgreSQL", "MongoDB", "Redis", "SQLite"],
        "correct_index": 2,
        "explanation": "Redis provides high-speed channel layer message passing."
    },
    {
        "id": 4,
        "question": "What is the capital city of France?",
        "options": ["Berlin", "Madrid", "Rome", "Paris"],
        "correct_index": 3,
        "explanation": "Paris is the capital and most populous city of France."
    },
    {
        "id": 5,
        "question": "Which planet in our solar system is known as the Red Planet?",
        "options": ["Venus", "Mars", "Jupiter", "Saturn"],
        "correct_index": 1,
        "explanation": "Mars appears red due to iron oxide (rust) on its surface."
    },
]

PROFANITY_LIST = [
    r'\bshit\b', r'\bfuck\b', r'\basshole\b', r'\bbitch\b', r'\bdamn\b', r'\bcrap\b'
]


def censor_profanity(text: str) -> str:
    """Filters profanity from chat messages by replacing matches with ***."""
    censored = text
    for pattern in PROFANITY_LIST:
        censored = re.sub(pattern, '***', censored, flags=re.IGNORECASE)
    return censored


class TriviaEngine(BaseGameEngine):
    """
    Real-Time Multiplayer Trivia Game Engine.
    Handles round transitions, 15-second per-question timers,
    speed-based bonus scoring, streak multipliers, and leaderboard sorting.
    """
    game_id = "trivia"
    slug = "trivia"
    name = "Trivia Challenge"
    description = "Real-time multiplayer trivia quiz with friends across timed rounds."
    category = "Party"
    icon = "fa-lightbulb"
    min_players = 2
    max_players = 8

    QUESTION_DURATION_SECONDS = 15
    INTERMISSION_DURATION_SECONDS = 5
    TOTAL_ROUNDS = 5

    def initialize_state(self, players: List[str]) -> Dict[str, Any]:
        player_scores = {p: 0 for p in players}
        player_streaks = {p: 0 for p in players}

        return {
            'game_id': self.game_id,
            'current_round': 0,
            'total_rounds': self.TOTAL_ROUNDS,
            'questions': TRIVIA_QUESTIONS,
            'player_scores': player_scores,
            'player_streaks': player_streaks,
            'current_question': None,
            'round_answers': {},  # player -> {option_index, timestamp, points_earned}
            'is_intermission': False,
            'is_over': False,
            'winner': None,
        }

    def start_next_round(self, state: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """Advances game state to the next round."""
        current_round = state.get('current_round', 0)
        questions = state.get('questions', TRIVIA_QUESTIONS)

        if current_round >= len(questions) or current_round >= self.TOTAL_ROUNDS:
            state['is_over'] = True
            state['winner'] = self.calculate_winner(state)
            return state, True

        question = questions[current_round]
        state['current_round'] = current_round + 1
        state['current_question'] = {
            'id': question['id'],
            'question': question['question'],
            'options': question['options'],
            'round_num': state['current_round'],
            'start_time': time.time(),
        }
        state['round_answers'] = {}
        state['is_intermission'] = False

        return state, False

    def validate_move(self, player: str, move_data: Dict[str, Any], state: Dict[str, Any]) -> bool:
        if state.get('is_over') or state.get('is_intermission'):
            return False

        if player in state.get('round_answers', {}):
            return False  # Already answered this round

        option_index = move_data.get('option_index')
        if option_index is None or not (0 <= option_index < 4):
            return False

        return True

    def apply_move(self, player: str, move_data: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        option_index = move_data['option_index']
        answer_time = time.time()
        
        current_q = state.get('current_question', {})
        start_time = current_q.get('start_time', answer_time)
        time_taken = max(0.0, answer_time - start_time)
        time_remaining = max(0.0, float(self.QUESTION_DURATION_SECONDS) - time_taken)

        round_num = state.get('current_round', 1) - 1
        correct_index = TRIVIA_QUESTIONS[round_num]['correct_index']
        is_correct = (option_index == correct_index)

        points = 0
        if is_correct:
            # Base 1000 pts + Speed Bonus (up to 500 pts) * Streak Multiplier
            speed_bonus = int((time_remaining / self.QUESTION_DURATION_SECONDS) * 500)
            base_points = 1000 + speed_bonus
            
            streak = state['player_streaks'].get(player, 0) + 1
            multiplier = 1.0 + min(streak * 0.2, 1.0)  # Max 2.0x multiplier
            points = int(base_points * multiplier)
            
            state['player_streaks'][player] = streak
            state['player_scores'][player] = state['player_scores'].get(player, 0) + points
        else:
            state['player_streaks'][player] = 0

        state['round_answers'][player] = {
            'option_index': option_index,
            'is_correct': is_correct,
            'points_earned': points,
            'time_taken': round(time_taken, 2),
        }

        return state

    def check_game_over(self, state: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if state.get('is_over'):
            return True, state.get('winner')
        return False, None

    def calculate_winner(self, state: Dict[str, Any]) -> str:
        scores = state.get('player_scores', {})
        if not scores:
            return "Nobody"
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_scores) > 1 and sorted_scores[0][1] == sorted_scores[1][1]:
            return "draw"
        return sorted_scores[0][0]

    def get_leaderboard(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        scores = state.get('player_scores', {})
        streaks = state.get('player_streaks', {})
        
        leaderboard = []
        for player, score in scores.items():
            leaderboard.append({
                'player': player,
                'score': score,
                'streak': streaks.get(player, 0),
            })
        
        leaderboard.sort(key=lambda x: x['score'], reverse=True)
        for rank, entry in enumerate(leaderboard, start=1):
            entry['rank'] = rank
            
        return leaderboard

    def get_public_state(self, state: Dict[str, Any], player: Optional[str] = None) -> Dict[str, Any]:
        current_q = state.get('current_question')
        clean_q = None
        if current_q:
            clean_q = {
                'id': current_q.get('id'),
                'question': current_q.get('question'),
                'options': current_q.get('options'),
                'round_num': current_q.get('round_num'),
            }

        user_answer = state.get('round_answers', {}).get(player) if player else None

        return {
            'game_id': self.game_id,
            'current_round': state.get('current_round', 0),
            'total_rounds': state.get('total_rounds', self.TOTAL_ROUNDS),
            'question': clean_q,
            'is_intermission': state.get('is_intermission', False),
            'is_over': state.get('is_over', False),
            'winner': state.get('winner'),
            'user_answer': user_answer,
            'leaderboard': self.get_leaderboard(state),
        }


# Singleton engine instance
trivia_engine = TriviaEngine()
