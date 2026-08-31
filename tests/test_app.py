import unittest

from src.app import active_sessions, app


class TestAppSessions(unittest.TestCase):
    def setUp(self):
        active_sessions.clear()
        self.client = app.test_client()

    def tearDown(self):
        active_sessions.clear()

    def test_created_session_can_be_listed(self):
        create_response = self.client.post(
            "/api/sessions",
            json={"creator_name": "Alice"},
        )

        self.assertEqual(create_response.status_code, 201)
        session_id = create_response.get_json()["session_id"]

        list_response = self.client.get("/api/sessions")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(
            list_response.get_json()["sessions"][0]["session_id"],
            session_id,
        )

    def test_hitting_blackjack_finishes_single_player_round(self):
        create_response = self.client.post(
            "/api/sessions",
            json={"creator_name": "Alice"},
        )
        session_id = create_response.get_json()["session_id"]
        session = active_sessions[session_id]
        session.start_game()

        player = session.players[0]
        player.cards = ["KH", "5D"]
        player.total = 15
        player.blackjack = False
        session.deck.append("6S")

        hit_response = self.client.post(
            f"/api/sessions/{session_id}/hit",
            json={"player_name": "Alice"},
        )

        self.assertEqual(hit_response.status_code, 200)
        game_state = hit_response.get_json()["game_state"]
        self.assertEqual(game_state["status"], "finished")
        self.assertIsNone(game_state["current_player"])
        self.assertTrue(game_state["winner"])


if __name__ == "__main__":
    unittest.main()
