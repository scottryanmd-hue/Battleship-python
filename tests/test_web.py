import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from battleship.session import Session
from battleship.web import Handler


class SessionTests(unittest.TestCase):
    def test_a_shot_draws_a_reply(self):
        session = Session(seed=7)
        events = session.fire(0, 0)
        self.assertEqual([e["team"] for e in events], ["devin", "cursor"])
        self.assertEqual(session.turn, 2)

    def test_squares_cannot_be_shelled_twice(self):
        session = Session(seed=7)
        session.fire(3, 3)
        with self.assertRaises(ValueError):
            session.fire(3, 3)

    def test_cursor_never_repeats_a_square(self):
        session = Session(seed=1)
        fired = []
        for row in range(10):
            for col in range(10):
                if session.winner or session.ai.already_shot(row, col):
                    continue
                for event in session.fire(row, col):
                    if event["team"] == "cursor":
                        fired.append((event["row"], event["col"]))
        self.assertEqual(len(fired), len(set(fired)))

    def test_cursor_ships_stay_hidden_until_they_sink(self):
        session = Session(seed=7)
        self.assertEqual(session.state()["away"]["ships"], [])
        self.assertEqual(len(session.state()["home"]["ships"]), 5)
        # Seed 7 puts Cursor's Destroyer on C5-C6.
        session.fire(2, 4)
        session.fire(2, 5)
        away = session.state()["away"]["ships"]
        self.assertEqual([s["name"] for s in away], ["Destroyer"])
        self.assertTrue(away[0]["sunk"])

    def test_devin_wins_when_the_last_cursor_ship_goes_down(self):
        session = Session(seed=7)
        for ship in list(session.ai.ships):
            for row, col in ship.cells:
                if not session.ai.already_shot(row, col) and not session.winner:
                    session.fire(row, col)
        self.assertEqual(session.winner, "devin")
        self.assertEqual(session.state()["stats"]["devin_sunk"], 5)
        self.assertEqual(len(session.state()["away"]["ships"]), 5)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Handler.seed = 7
        Handler.session = Session(7)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def call(self, path, body=None):
        request = urllib.request.Request(
            self.url + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json"},
            method="POST" if body is not None else "GET",
        )
        with urllib.request.urlopen(request) as response:
            return json.load(response)

    def test_state_and_fire_round_trip(self):
        self.call("/api/new", {})
        state = self.call("/api/state")
        self.assertEqual(state["turn"], 1)
        self.assertEqual(state["away"]["ships"], [])

        payload = self.call("/api/fire", {"coord": "C5"})
        self.assertEqual(payload["events"][0]["result"], "hit")
        self.assertEqual(payload["state"]["stats"]["devin_hits"], 1)

    def test_bad_coordinates_and_repeats_are_rejected(self):
        self.call("/api/new", {})
        with self.assertRaises(urllib.error.HTTPError) as bad:
            self.call("/api/fire", {"coord": "Z9"})
        self.assertEqual(bad.exception.code, 400)

        self.call("/api/fire", {"row": 0, "col": 0})
        with self.assertRaises(urllib.error.HTTPError) as repeat:
            self.call("/api/fire", {"row": 0, "col": 0})
        self.assertEqual(repeat.exception.code, 409)

    def test_reroll_is_only_legal_before_the_first_shot(self):
        self.call("/api/new", {})
        self.assertEqual(self.call("/api/reroll", {})["turn"], 1)
        self.call("/api/fire", {"coord": "A1"})
        with self.assertRaises(urllib.error.HTTPError) as late:
            self.call("/api/reroll", {})
        self.assertEqual(late.exception.code, 409)

    def test_static_files_are_served(self):
        for path, marker in (("/", b"Battleship Channel"), ("/app.js", b"webkitSpeechRecognition")):
            with urllib.request.urlopen(self.url + path) as response:
                self.assertIn(marker, response.read())


if __name__ == "__main__":
    unittest.main()
