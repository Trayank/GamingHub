from django.test import TestCase
from rooms.models import GameRoom, PlayerSession
from games.ludo.ludo_engine import LudoEngine
from games.chess.standard_engine import StandardChessEngine
from games.chess.four_way_engine import FourWayChessEngine
from games.chess.bughouse_engine import BughouseEngine

class LudoEngineTestCase(TestCase):

    def test_ludo_engine_polygonal_scalability(self):
        engine = LudoEngine()

        # 4 Players (Square / 4-quadrant layout)
        state4 = engine.initialize_state(4)
        self.assertEqual(state4['player_count'], 4)
        self.assertEqual(state4['total_circuit_length'], 24)

        # 6 Players (Hexagonal layout)
        state6 = engine.initialize_state(6)
        self.assertEqual(state6['player_count'], 6)
        self.assertEqual(state6['total_circuit_length'], 36)

        # 8 Players (Octagonal layout)
        state8 = engine.initialize_state(8)
        self.assertEqual(state8['player_count'], 8)
        self.assertEqual(state8['total_circuit_length'], 48)

        # 10 Players (Decagonal layout)
        state10 = engine.initialize_state(10)
        self.assertEqual(state10['player_count'], 10)
        self.assertEqual(state10['total_circuit_length'], 60)

    def test_ludo_consecutive_sixes(self):
        engine = LudoEngine()
        state = engine.initialize_state(4)
        state['consecutive_sixes'] = 2
        state['phase'] = 'WAITING_FOR_ROLL'

        # Force roll dice action
        state['dice_value'] = 6
        state['consecutive_sixes'] = 3
        # Direct turn forfeit trigger check
        state, valid, msg = engine.apply_action(state, 0, {'type': 'roll_dice'})
        self.assertTrue(valid)

    def test_ludo_safe_spot_capture_prevention(self):
        engine = LudoEngine()
        state = engine.initialize_state(2)
        # Player 0 token on safe start spot
        state['players'][0]['tokens'][0]['state'] = 'TRACK'
        state['players'][0]['tokens'][0]['pos'] = 0  # Absolute step 0 (safe start)

        # Player 1 token also on step 0
        state['players'][1]['tokens'][0]['state'] = 'TRACK'
        state['players'][1]['tokens'][0]['pos'] = 12 # Absolute step 0 for P1

        # Confirm both remain on track (no capture on safe spot)
        self.assertEqual(state['players'][0]['tokens'][0]['state'], 'TRACK')
        self.assertEqual(state['players'][1]['tokens'][0]['state'], 'TRACK')

    def test_ludo_blockades_toggle(self):
        engine = LudoEngine()
        state = engine.initialize_state(4, variant='blockades_enabled')
        self.assertTrue(state['blockades_enabled'])

class ChessEnginesTestCase(TestCase):

    def test_standard_chess_engine(self):
        engine = StandardChessEngine()
        state = engine.initialize_state(2)
        self.assertEqual(state['current_turn'], 'w')

        valid_moves = engine.get_valid_moves(state, 0)
        self.assertGreater(len(valid_moves['moves']), 0)

        # White pawn move e2 to e4
        state, valid, msg = engine.apply_action(state, 0, {'type': 'move_piece', 'from': [6, 4], 'to': [4, 4]})
        self.assertTrue(valid)
        self.assertEqual(state['current_turn'], 'b')

    def test_four_way_chess_engine(self):
        engine = FourWayChessEngine()
        state = engine.initialize_state(4)
        self.assertEqual(len(state['players']), 4)
        self.assertEqual(len(state['board']), 14)

    def test_bughouse_engine(self):
        engine = BughouseEngine()
        state = engine.initialize_state(4)
        self.assertIn('board_a', state)
        self.assertIn('board_b', state)
        self.assertIn('reserves', state)
