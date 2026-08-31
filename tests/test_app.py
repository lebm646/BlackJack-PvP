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


if __name__ == "__main__":
    unittest.main()
