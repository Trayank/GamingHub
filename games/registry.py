from typing import Optional
from games.base import BaseGameEngine
from games.ludo.engine import LudoEngine
from games.chess.standard_engine import StandardChessEngine
from games.chess.four_way_engine import FourWayChessEngine
from games.chess.bughouse_engine import BughouseEngine

ENGINE_REGISTRY = {
    'LUDO': LudoEngine,
    'CHESS_STANDARD': StandardChessEngine,
    'CHESS_4WAY': FourWayChessEngine,
    'CHESS_BUGHOUSE': BughouseEngine
}

def get_game_engine(game_type: str) -> Optional[BaseGameEngine]:
    engine_cls = ENGINE_REGISTRY.get(game_type.upper())
    if engine_cls:
        return engine_cls()
    return None
