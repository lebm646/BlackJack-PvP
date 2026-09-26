import unittest
from unittest.mock import patch

from src.gameSession import GameSession
from src.player import Player


class TestBlackjack(unittest.TestCase):
    def setUp(self):
        self.session = GameSession("test_session", "player1")
        self.player1 = self.session.add_player("player1")
        self.player2 = self.session.add_player("player2")
        self.session.begin_betting()

    def start_deterministic_round(self):
        self.session.place_bet(self.player1.token, 10)
        with patch("src.gameSession.random.shuffle", lambda deck: None):
            self.session.place_bet(self.player2.token, 10)

    def test_initial_deal_uses_one_deck(self):
        self.start_deterministic_round()

        self.assertEqual(len(self.player1.cards), 2)
        self.assertEqual(len(self.player2.cards), 2)
        self.assertEqual(len(self.session.dealer.cards), 2)
        self.assertEqual(len(self.session.deck), 46)

    def test_only_two_card_twenty_one_is_blackjack(self):
        natural = Player("Natural")
        natural.hit("AH")
        natural.hit("KD")

        ordinary_twenty_one = Player("Twenty One")
        ordinary_twenty_one.hit("5H")
        ordinary_twenty_one.hit("6D")
        ordinary_twenty_one.hit("10S")

        self.assertTrue(natural.blackjack)
        self.assertEqual(ordinary_twenty_one.total, 21)
        self.assertFalse(ordinary_twenty_one.blackjack)

    def test_blackjack_pays_three_to_two(self):
        self.player1.chips = 90
        self.player1.bet = 10
        self.player1.cards = ["AH", "KS"]
        self.player1.total = 21
        self.player1.blackjack = True
        self.player2.bet = 0
        self.session.dealer.cards = ["10H", "QD"]
        self.session.dealer.total = 20

        self.session.determine_winners()

        self.assertEqual(self.player1.chips, 115)

    def test_blackjack_still_pays_three_to_two_when_dealer_busts(self):
        self.player1.chips = 90
        self.player1.bet = 10
        self.player1.cards = ["AH", "KS"]
        self.player1.total = 21
        self.player1.blackjack = True
        self.player2.bet = 0
        self.session.dealer.cards = ["10H", "6D", "8C"]
        self.session.dealer.total = 24
        self.session.dealer.busted = True

        self.session.determine_winners()

        self.assertEqual(self.player1.chips, 115)

    def test_invalid_and_unaffordable_bets_are_rejected(self):
        self.assertFalse(self.player1.place_bet(0))
        self.assertFalse(self.player1.place_bet(-5))
        self.assertFalse(self.player1.place_bet(101))
        self.assertFalse(self.player1.place_bet(1.5))
        self.assertEqual(self.player1.chips, 100)

    def test_completed_player_is_skipped(self):
        self.player1.bet = 10
        self.player1.blackjack = True
        self.player1.total = 21
        self.player2.bet = 10
        self.session.status = "in_progress"
        self.session.current_player_index = 0

        should_continue = self.session._skip_completed_players()

        self.assertTrue(should_continue)
        self.assertIs(self.session.get_current_player(), self.player2)

    def test_dealer_hits_on_sixteen_and_stands_on_seventeen(self):
        self.session.dealer.cards = ["KH", "6H"]
        self.session.dealer.total = 16
        self.session.deck = ["2S"]
        self.session.dealer_turn()
        self.assertEqual(self.session.dealer.total, 18)

        self.session.dealer.cards = ["KH", "7H"]
        self.session.dealer.total = 17
        self.session.dealer_turn()
        self.assertEqual(self.session.dealer.total, 17)


if __name__ == "__main__":
    unittest.main()
