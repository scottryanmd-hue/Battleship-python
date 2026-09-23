import random
import unittest

from battleship.board import Board, PlacementError, format_coord, parse_coord


class BoardTests(unittest.TestCase):
    def test_parse_and_format_coord(self):
        self.assertEqual(parse_coord("b7"), (1, 6))
        self.assertEqual(format_coord(1, 6), "B7")
        self.assertEqual(parse_coord("J10"), (9, 9))
        with self.assertRaises(ValueError):
            parse_coord("K3")
        with self.assertRaises(ValueError):
            parse_coord("A11")

    def test_overlap_and_bounds_rejected(self):
        board = Board()
        board.place("Cruiser", 3, 0, 0, horizontal=True)
        with self.assertRaises(PlacementError):
            board.place("Destroyer", 2, 0, 2, horizontal=True)
        with self.assertRaises(PlacementError):
            board.place("Carrier", 5, 0, 8, horizontal=True)

    def test_three_missiles_detonate_a_long_ship(self):
        board = Board()
        board.place("Carrier", 5, 0, 0, horizontal=True)
        self.assertEqual(board.fire(0, 0)[0], "hit")
        self.assertEqual(board.fire(0, 1)[0], "hit")
        result, ship, exploded = board.fire(0, 2)
        self.assertEqual(result, "sunk")
        self.assertTrue(exploded)
        self.assertTrue(ship.sunk)
        self.assertTrue(all(board.grid[0][c] == Board.SUNK for c in range(5)))
        self.assertTrue(board.defeated)

    def test_destroyer_sinks_on_two_hits(self):
        board = Board()
        board.place("Destroyer", 2, 4, 4, horizontal=False)
        self.assertEqual(board.fire(4, 4)[0], "hit")
        self.assertEqual(board.fire(5, 4)[0], "sunk")

    def test_miss_is_recorded(self):
        board = Board()
        board.place("Destroyer", 2, 0, 0, horizontal=True)
        result, ship, exploded = board.fire(9, 9)
        self.assertEqual((result, ship, exploded), ("miss", None, False))
        self.assertTrue(board.already_shot(9, 9))

    def test_random_fleet_fits_without_overlap(self):
        board = Board()
        board.place_fleet_randomly(random.Random(0))
        cells = [cell for ship in board.ships for cell in ship.cells]
        self.assertEqual(len(cells), len(set(cells)))
        self.assertEqual(len(board.ships), 5)


if __name__ == "__main__":
    unittest.main()
