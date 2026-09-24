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


class FusionTests(unittest.TestCase):
    def test_a_salvo_is_the_square_plus_a_neighbour(self):
        session = Session(seed=7)
        self.assertEqual(session.fusion_targets(4, 4), [[4, 4], [3, 4]])

    def test_a_salvo_spills_past_squares_already_shelled(self):
        session = Session(seed=7)
        session.ai.fire(3, 4)
        session.ai.fire(4, 3)
        targets = session.fusion_targets(4, 4)
        self.assertNotIn([3, 4], targets)
        self.assertNotIn([4, 3], targets)
        self.assertEqual(len(targets), 2)
        self.assertEqual(len(set(map(tuple, targets))), 2)

    def test_a_salvo_stays_on_the_board_in_a_corner(self):
        session = Session(seed=7)
        targets = session.fusion_targets(0, 0)
        self.assertEqual(targets[0], [0, 0])
        self.assertEqual(len(targets), 2)
        self.assertTrue(all(0 <= r < 10 and 0 <= c < 10 for r, c in targets))

    def test_two_missiles_fly_and_cursor_answers_once(self):
        session = Session(seed=7)
        events = session.fusion(4, 4)
        devin = [e for e in events if e["team"] == "devin"]
        self.assertEqual(len(devin), 2)
        self.assertTrue(all(e["fusion"] for e in devin))
        self.assertEqual(len([e for e in events if e["team"] == "cursor"]), 1)
        self.assertEqual(session.stats["devin_hits"] + session.stats["devin_misses"], 2)

    def test_a_salvo_never_re_shells_and_stops_at_the_win(self):
        session = Session(seed=7)
        while not session.winner:
            row, col = next(
                (r, c)
                for r in range(10)
                for c in range(10)
                if not session.ai.already_shot(r, c)
            )
            session.fusion(row, col)
        self.assertEqual(session.winner, "devin")
        with self.assertRaises(ValueError):
            session.fusion(0, 0)


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

    def test_fusion_endpoint_fires_a_two_shot_salvo(self):
        self.call("/api/new", {})
        payload = self.call("/api/fusion", {"coord": "E5"})
        devin = [e for e in payload["events"] if e["team"] == "devin"]
        self.assertEqual([e["coord"] for e in devin][0], "E5")
        self.assertEqual(len(devin), 2)
        stats = payload["state"]["stats"]
        self.assertEqual(stats["devin_hits"] + stats["devin_misses"], 2)

    def test_swe2_endpoint_sweeps_three_columns(self):
        self.call("/api/new", {})
        payload = self.call("/api/swe2", {})
        devin = [e for e in payload["events"] if e["team"] == "devin"]
        self.assertEqual(sorted({e["coord"][1:] for e in devin}), ["1", "4", "6"])
        self.assertEqual(len(devin), 30)

    def test_outsourced_it_sinks_the_biggest_hull_afloat(self):
        self.call("/api/new", {})
        payload = self.call("/api/outsource", {})
        devin = [e for e in payload["events"] if e["team"] == "devin"]
        self.assertEqual(devin[0]["reveal"]["name"], "Carrier")
        self.assertEqual(devin[-1]["result"], "sunk")
        fleet = {s["name"]: s for s in payload["state"]["away"]["fleet"]}
        self.assertTrue(fleet["Carrier"]["sunk"])

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

    def test_missing_victory_track_is_a_clean_404(self):
        """The page probes for an optional custom anthem on load."""
        with self.assertRaises(urllib.error.HTTPError) as missing:
            urllib.request.urlopen(self.url + "/sounds/victory.mp3")
        self.assertEqual(missing.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
