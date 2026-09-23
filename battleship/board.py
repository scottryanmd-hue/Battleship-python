"""Grid, ships and shot bookkeeping."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

SIZE = 10
LETTERS = "ABCDEFGHIJ"

FLEET = [
    ("Carrier", 5),
    ("Battleship", 4),
    ("Cruiser", 3),
    ("Submarine", 3),
    ("Destroyer", 2),
]

#: A ship detonates (and gets finished off by the otter) at this many hits.
EXPLOSION_THRESHOLD = 3


class PlacementError(ValueError):
    pass


@dataclass
class Ship:
    name: str
    size: int
    cells: list[tuple[int, int]]
    hits: set[tuple[int, int]] = field(default_factory=set)
    sunk: bool = False

    @property
    def hit_count(self) -> int:
        return len(self.hits)

    @property
    def explodes_next(self) -> bool:
        """True when one more hit detonates the hull."""
        return self.hit_count + 1 >= min(EXPLOSION_THRESHOLD, self.size)


class Board:
    """One fleet's ocean. `grid` holds shot results, ships hold their own damage."""

    EMPTY = " "
    MISS = "o"
    HIT = "x"
    SUNK = "#"

    def __init__(self) -> None:
        self.grid = [[self.EMPTY for _ in range(SIZE)] for _ in range(SIZE)]
        self.ships: list[Ship] = []

    # -- placement ---------------------------------------------------------
    def cells_for(self, row: int, col: int, size: int, horizontal: bool) -> list[tuple[int, int]]:
        if horizontal:
            cells = [(row, col + i) for i in range(size)]
        else:
            cells = [(row + i, col) for i in range(size)]
        if any(not (0 <= r < SIZE and 0 <= c < SIZE) for r, c in cells):
            raise PlacementError("Ship runs off the board.")
        return cells

    def can_place(self, cells: list[tuple[int, int]]) -> bool:
        occupied = {cell for ship in self.ships for cell in ship.cells}
        return not any(cell in occupied for cell in cells)

    def place(self, name: str, size: int, row: int, col: int, horizontal: bool) -> Ship:
        cells = self.cells_for(row, col, size, horizontal)
        if not self.can_place(cells):
            raise PlacementError("That spot overlaps another ship.")
        ship = Ship(name=name, size=size, cells=cells)
        self.ships.append(ship)
        return ship

    def place_fleet_randomly(self, rng: random.Random) -> None:
        for name, size in FLEET:
            while True:
                horizontal = rng.random() < 0.5
                row = rng.randrange(SIZE - (0 if horizontal else size - 1))
                col = rng.randrange(SIZE - (size - 1 if horizontal else 0))
                try:
                    self.place(name, size, row, col, horizontal)
                    break
                except PlacementError:
                    continue

    # -- firing ------------------------------------------------------------
    def ship_at(self, row: int, col: int) -> Ship | None:
        for ship in self.ships:
            if (row, col) in ship.cells:
                return ship
        return None

    def already_shot(self, row: int, col: int) -> bool:
        return self.grid[row][col] != self.EMPTY

    def fire(self, row: int, col: int) -> tuple[str, Ship | None, bool]:
        """Return (result, ship, exploded) where result is 'miss' | 'hit' | 'sunk'."""
        ship = self.ship_at(row, col)
        if ship is None:
            self.grid[row][col] = self.MISS
            return "miss", None, False

        ship.hits.add((row, col))
        self.grid[row][col] = self.HIT

        exploded = ship.hit_count >= min(EXPLOSION_THRESHOLD, ship.size)
        if exploded or ship.hit_count == ship.size:
            ship.sunk = True
            ship.hits.update(ship.cells)
            for r, c in ship.cells:
                self.grid[r][c] = self.SUNK
            return "sunk", ship, exploded
        return "hit", ship, False

    # -- state -------------------------------------------------------------
    @property
    def sunk_ships(self) -> list[Ship]:
        return [s for s in self.ships if s.sunk]

    @property
    def defeated(self) -> bool:
        return bool(self.ships) and all(s.sunk for s in self.ships)


def parse_coord(text: str) -> tuple[int, int]:
    """'B7' / 'b7' -> (1, 6)."""
    text = text.strip().upper().replace(" ", "")
    if len(text) < 2:
        raise ValueError("Use a coordinate like B7.")
    letter, number = text[0], text[1:]
    if letter not in LETTERS or not number.isdigit():
        raise ValueError("Use a coordinate like B7 (row A-J, column 1-10).")
    col = int(number) - 1
    if not 0 <= col < SIZE:
        raise ValueError("Column must be between 1 and 10.")
    return LETTERS.index(letter), col


def format_coord(row: int, col: int) -> str:
    return f"{LETTERS[row]}{col + 1}"
