import random
import unittest

from battleship.board import SIZE, Board
from battleship.probability import best_square, density, heatmap, posterior
from battleship.session import Session


def _fleet_board() -> Board:
    board = Board()
    board.place("Carrier", 5, 0, 0, True)
    board.place("Battleship", 4, 2, 0, True)
    board.place("Cruiser", 3, 4, 0, True)
    board.place("Submarine", 3, 6, 0, True)
    board.place("Destroyer", 2, 8, 0, True)
    return board


class DensityTests(unittest.TestCase):
    def test_an_untouched_ocean_favours_the_middle(self):
        heat = density(_fleet_board())
        self.assertEqual(max(max(row) for row in heat), 1.0)
        self.assertGreater(heat[4][4], heat[0][0])

    def test_shot_squares_are_never_recommended(self):
        board = _fleet_board()
        board.fire(9, 9)  # a miss, far from every hull
        heat = density(board)
        self.assertEqual(heat[9][9], 0.0)
        self.assertNotEqual(best_square(board), (9, 9))

    def test_a_miss_cools_its_neighbourhood(self):
        board = _fleet_board()
        before = density(board)[5][5]
        board.fire(5, 4)
        board.fire(5, 6)
        self.assertLess(density(board)[5][5], before)

    def test_the_swarm_chases_a_wounded_hull(self):
        board = _fleet_board()
        board.fire(0, 2)  # one hit on the Carrier, not enough to sink it
        best = best_square(board, random.Random(3))
        self.assertIn(best, [(0, 1), (0, 3)])

    def test_a_board_shot_to_pieces_has_no_target(self):
        board = _fleet_board()
        for row in range(SIZE):
            for col in range(SIZE):
                if not board.already_shot(row, col):
                    board.fire(row, col)
        self.assertIsNone(best_square(board, random.Random(3)))


class PosteriorTests(unittest.TestCase):
    def test_probabilities_are_odds_not_scores(self):
        odds, ess = posterior(_fleet_board(), random.Random(11))
        self.assertGreater(ess, 0)
        flat = [value for row in odds for value in row]
        self.assertTrue(all(0.0 <= value <= 1.0 for value in flat))
        # Seventeen cells of hull over a hundred squares: the mean square is
        # occupied about a sixth of the time, and none is anywhere near certain.
        self.assertLess(max(flat), 0.6)
        self.assertAlmostEqual(sum(flat), 17, delta=1.5)

    def test_shelled_squares_carry_no_probability(self):
        board = _fleet_board()
        board.fire(9, 9)
        board.fire(0, 2)
        odds, _ = posterior(board, random.Random(5))
        self.assertEqual(odds[9][9], 0.0)  # known water
        self.assertEqual(odds[0][2], 0.0)  # known hull, nothing left to learn

    def test_a_wounded_hull_dominates_the_posterior(self):
        board = _fleet_board()
        board.fire(0, 2)
        odds, _ = posterior(board, random.Random(5))
        self.assertGreater(odds[0][1], 0.4)
        self.assertGreater(odds[0][1], odds[5][5] * 2)  # twice open-water odds

    def test_the_estimate_matches_exhaustive_enumeration(self):
        """Against a board with one ship left, the exact answer is countable."""
        board = Board()
        board.place("Destroyer", 2, 4, 4, True)
        board.fire(0, 0)
        board.fire(9, 9)

        spots = [
            cells
            for size in (2,)
            for cells in (
                [(r, c), (r, c + 1)] for r in range(SIZE) for c in range(SIZE - 1)
            )
        ] + [[(r, c), (r + 1, c)] for r in range(SIZE - 1) for c in range(SIZE)]
        spots = [
            cells for cells in spots if not any(board.grid[r][c] != " " for r, c in cells)
        ]
        exact = [[0.0] * SIZE for _ in range(SIZE)]
        for cells in spots:
            for r, c in cells:
                exact[r][c] += 1 / len(spots)

        odds, _ = posterior(board, random.Random(2), samples=8000, time_budget=5.0)
        worst = max(abs(odds[r][c] - exact[r][c]) for r in range(SIZE) for c in range(SIZE))
        self.assertLess(worst, 0.02)

    def test_the_heatmap_reports_which_estimator_answered(self):
        read = heatmap(_fleet_board(), random.Random(1))
        self.assertEqual(read["method"], "posterior")
        self.assertGreater(read["ess"], 0)
        self.assertEqual(max(max(row) for row in read["heat"]), 1.0)


class SessionIntelTests(unittest.TestCase):
    def test_the_session_publishes_swarm_intel_for_devin_only(self):
        state = Session(seed=7).state()
        self.assertEqual(len(state["swarm"]["heat"]), SIZE)
        self.assertRegex(state["swarm"]["best"], r"^[A-J](10|[1-9])$")
        self.assertIn(state["swarm"]["method"], {"posterior", "density"})
        self.assertEqual(state["away"]["ships"], [])  # still no peeking at Cursor's fleet

    def test_the_map_moves_after_every_shot(self):
        session = Session(seed=7)
        before = session.state()["swarm"]["heat"]
        row, col = 4, 4
        session.fire(row, col)
        after = session.state()["swarm"]["heat"]
        self.assertEqual(after[row][col], 0.0)
        self.assertNotEqual(before, after)


if __name__ == "__main__":
    unittest.main()
