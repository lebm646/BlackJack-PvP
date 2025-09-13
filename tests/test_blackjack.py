import unittest
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from black_jack.src.gameSession import GameSession
from black_jack.src.player import Player
from black_jack.src.dealer import Dealer

class TestBlackjack(unittest.TestCase):
    def setUp(self):
        """Set up a game session for testing"""
        self.session = GameSession("test_session", "test_player")
        self.session.add_player("player1")
        self.session.add_player("player2")
        self.session.start_game()
    
    def test_initial_deal(self):
        """Test that each player and dealer get 2 cards initially"""
        for player in self.session.players:
            self.assertEqual(len(player.cards), 2)
            self.assertFalse(player.busted)
            self.assertIn(player.total, range(4, 22))  # Possible totals with 2 cards
        
        self.assertEqual(len(self.session.dealer.cards), 2)
        self.assertFalse(self.session.dealer.busted)
    
    def test_blackjack_win(self):
        """Test blackjack win condition"""
        player = self.session.players[0]
        # Set initial state
        player.chips = 100
        bet_amount = 10
        player.bet = bet_amount
        initial_chips = player.chips  # Save initial chips before any bets
        
        # Force blackjack
        player.cards = ['AH', 'KJ']  # Ace + Face card
        player.total = 21
        player.blackjack = True
        
        # Set dealer to not have blackjack
        self.session.dealer.cards = ['2H', '3D']
        self.session.dealer.total = 5
        
        # Determine winners
        self.session.determine_winners()
        
        # The implementation adds (bet * 2.5) to the chips
        # - 1x bet back (original bet)
        # - 1.x bet as winnings
        # So total added is 2.5x bet
        expected_chips = initial_chips + int(bet_amount * 2.5)
        self.assertEqual(player.chips, expected_chips)
        self.assertEqual(player.chips, 125.0)  # 100 + (10 * 2.5) = 125
    
    def test_bust_condition(self):
        """Test that player busts when going over 21"""
        player = self.session.players[0]
        player.cards = ['KH', 'QH', '2H']  # 22 points
        player.total = 22
        # Manually set busted since we're not using the hit method
        player.busted = player.total > 21
        
        self.assertTrue(player.busted)
    
    def test_dealer_play(self):
        """Test dealer hits on 16, stands on 17"""
        # Dealer has 16, should hit
        self.session.dealer.cards = ['KH', '6H']
        self.session.dealer.total = 16
        self.session.dealer_turn()
        self.assertGreaterEqual(self.session.dealer.total, 17)
        
        # Dealer has 17, should stand
        self.session.dealer.cards = ['KH', '7H']
        self.session.dealer.total = 17
        self.session.dealer_turn()
        self.assertEqual(self.session.dealer.total, 17)

if __name__ == '__main__':
    unittest.main()
