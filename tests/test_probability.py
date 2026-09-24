import unittest

from battleship.board import SIZE, Board
from battleship.probability import best_square, density
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
        best = best_square(board)
        self.assertIn(best, [(0, 1), (0, 3)])

    def test_a_board_shot_to_pieces_has_no_target(self):
        board = _fleet_board()
        for row in range(SIZE):
            for col in range(SIZE):
                if not board.already_shot(row, col):
                    board.fire(row, col)
        self.assertIsNone(best_square(board))

    def test_the_session_publishes_swarm_intel_for_devin_only(self):
        state = Session(seed=7).state()
        self.assertEqual(len(state["swarm"]["heat"]), SIZE)
        self.assertRegex(state["swarm"]["best"], r"^[A-J](10|[1-9])$")
        self.assertEqual(state["away"]["ships"], [])  # still no peeking at Cursor's fleet


if __name__ == "__main__":
    unittest.main()
