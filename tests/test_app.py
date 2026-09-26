import unittest
from unittest.mock import patch

from src.app import active_sessions, app


class TestAppSessions(unittest.TestCase):
    def setUp(self):
        active_sessions.clear()
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self):
        active_sessions.clear()

    def create_session(self, name="Alice"):
        response = self.client.post("/api/sessions", json={"creator_name": name})
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def test_created_session_returns_private_credentials_and_can_be_listed(self):
        created = self.create_session()

        self.assertTrue(created["player_token"])
        self.assertTrue(created["host_token"])
        listed = self.client.get("/api/sessions").get_json()["sessions"]
        self.assertEqual(listed[0]["session_id"], created["session_id"])
        self.assertNotIn("player_token", listed[0])
        self.assertNotIn("host_token", listed[0])

    def test_only_host_can_open_betting(self):
        created = self.create_session()
        session_id = created["session_id"]

        denied = self.client.post(f"/api/sessions/{session_id}/start")
        allowed = self.client.post(
            f"/api/sessions/{session_id}/start",
            headers={"X-Host-Token": created["host_token"]},
        )

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.get_json()["game_state"]["status"], "betting")

    def test_bet_requires_identity_and_cannot_exceed_balance(self):
        created = self.create_session()
        session_id = created["session_id"]
        self.client.post(
            f"/api/sessions/{session_id}/start",
            headers={"X-Host-Token": created["host_token"]},
        )

        denied = self.client.post(f"/api/sessions/{session_id}/bet", json={"amount": 10})
        too_large = self.client.post(
            f"/api/sessions/{session_id}/bet",
            json={"amount": 101},
            headers={"X-Player-Token": created["player_token"]},
        )

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(too_large.status_code, 400)
        self.assertEqual(active_sessions[session_id].players[0].chips, 100)

    def test_live_state_hides_dealer_hole_card_and_total(self):
        created = self.create_session()
        session = active_sessions[created["session_id"]]
        session.status = "in_progress"
        session.dealer.cards = ["AH", "9S"]
        session.dealer.total = 20

        state = self.client.get(f"/api/sessions/{created['session_id']}/status").get_json()

        self.assertEqual(state["dealer"]["cards"], ["XX", "9S"])
        self.assertIsNone(state["dealer"]["total"])

    def test_hitting_to_twenty_one_is_not_blackjack(self):
        created = self.create_session()
        session_id = created["session_id"]
        session = active_sessions[session_id]
        player = session.players[0]
        session.status = "in_progress"
        session.current_player_index = 0
        player.cards = ["KH", "5D"]
        player.total = 15
        player.bet = 10
        player.chips = 90
        session.dealer.cards = ["10C", "7S"]
        session.dealer.total = 17
        session.deck = ["6S"]

        response = self.client.post(
            f"/api/sessions/{session_id}/hit",
            headers={"X-Player-Token": created["player_token"]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("has 21", response.get_json()["message"])
        self.assertFalse(player.blackjack)
        self.assertEqual(response.get_json()["game_state"]["status"], "finished")

    def test_invalid_session_payloads_return_client_errors(self):
        no_json = self.client.post("/api/sessions")
        bad_max = self.client.post(
            "/api/sessions",
            json={"creator_name": "Alice", "max_players": "many"},
        )
        zero_max = self.client.post(
            "/api/sessions",
            json={"creator_name": "Alice", "max_players": 0},
        )

        self.assertEqual(no_json.status_code, 400)
        self.assertEqual(bad_max.status_code, 400)
        self.assertEqual(zero_max.status_code, 400)

    def test_final_bet_automatically_deals_the_round(self):
        created = self.create_session()
        session_id = created["session_id"]
        self.client.post(
            f"/api/sessions/{session_id}/start",
            headers={"X-Host-Token": created["host_token"]},
        )

        with patch("src.gameSession.random.shuffle", lambda deck: None):
            response = self.client.post(
                f"/api/sessions/{session_id}/bet",
                json={"amount": 10},
                headers={"X-Player-Token": created["player_token"]},
            )

        state = response.get_json()["game_state"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(state["status"], "in_progress")
        self.assertEqual(len(state["players"][0]["cards"]), 2)
        self.assertEqual(state["dealer"]["cards"][0], "XX")

    def test_new_round_requires_host_and_preserves_player_identity(self):
        created = self.create_session()
        session_id = created["session_id"]
        session = active_sessions[session_id]
        session.status = "finished"

        denied = self.client.post(f"/api/sessions/{session_id}/reset")
        allowed = self.client.post(
            f"/api/sessions/{session_id}/reset",
            headers={"X-Host-Token": created["host_token"]},
        )

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.get_json()["game_state"]["status"], "betting")
        self.assertIsNotNone(session.get_player_by_token(created["player_token"]))


if __name__ == "__main__":
    unittest.main()
