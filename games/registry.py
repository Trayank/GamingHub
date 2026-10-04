from typing import Optional
from games.base import BaseGameEngine
from games.ludo.ludo_engine import LudoEngine
from games.chess.standard_engine import StandardChessEngine
from games.chess.four_way_engine import FourWayChessEngine
from games.chess.bughouse_engine import BughouseEngine
from games.cards.uno_engine import UnoEngine
from games.cards.poker_engine import PokerEngine
from games.cards.blackjack_engine import BlackjackEngine
from games.cards.rummy_engine import RummyEngine

ENGINE_REGISTRY = {
    'LUDO': LudoEngine,
    'CHESS_STANDARD': StandardChessEngine,
    'CHESS_4WAY': FourWayChessEngine,
    'CHESS_BUGHOUSE': BughouseEngine,
    'CARD_UNO': UnoEngine,
    'CARD_POKER': PokerEngine,
    'CARD_BLACKJACK': BlackjackEngine,
    'CARD_RUMMY': RummyEngine
}

def get_game_engine(game_type: str) -> Optional[BaseGameEngine]:
    if not game_type:
        return None
    key = game_type.upper()
    engine_cls = ENGINE_REGISTRY.get(key)
    if engine_cls:
        return engine_cls()
    return None
