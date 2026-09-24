"""Devin Security Swarm: where is the enemy fleet probably hiding?

A classic Battleship density map. Every legal placement of every enemy ship that
still floats is enumerated against what the shooter can actually see — misses,
hits and sunk hulls — and each candidate square scores one point per placement
that covers it. Placements that also cover a known, unsunk hit are worth far
more, which turns the map into a targeting solution once a hull is wounded.

Only public information is used: the shot grid and which ships have gone down.
The swarm never peeks at the defender's ship list.
"""

from __future__ import annotations

from .board import SIZE, Board

#: A placement that explains an existing hit is this much more interesting than
#: one covering only open water.
HIT_WEIGHT = 25


def surviving_sizes(board: Board) -> list[int]:
    return [ship.size for ship in board.ships if not ship.sunk]


def density(board: Board) -> list[list[float]]:
    """Per-square scores in 0..1 for the squares still worth shelling.

    Already-shot squares score 0 — you cannot fire at them twice.
    """
    blocked = [
        [board.grid[r][c] in (Board.MISS, Board.SUNK) for c in range(SIZE)] for r in range(SIZE)
    ]
    wounded = [[board.grid[r][c] == Board.HIT for c in range(SIZE)] for r in range(SIZE)]
    scores = [[0.0] * SIZE for _ in range(SIZE)]

    for size in surviving_sizes(board):
        for horizontal in (True, False):
            rows = SIZE if horizontal else SIZE - size + 1
            cols = SIZE - size + 1 if horizontal else SIZE
            for row in range(rows):
                for col in range(cols):
                    cells = [
                        (row, col + i) if horizontal else (row + i, col) for i in range(size)
                    ]
                    if any(blocked[r][c] for r, c in cells):
                        continue
                    hits = sum(1 for r, c in cells if wounded[r][c])
                    weight = 1.0 + HIT_WEIGHT * hits
                    for r, c in cells:
                        if not wounded[r][c]:
                            scores[r][c] += weight

    peak = max((value for row in scores for value in row), default=0.0)
    if peak <= 0:
        return scores
    return [[round(value / peak, 4) for value in row] for row in scores]


def best_square(board: Board) -> tuple[int, int] | None:
    """The square the swarm would shell next, if any square is left."""
    scores = density(board)
    best = max(
        ((scores[r][c], r, c) for r in range(SIZE) for c in range(SIZE) if scores[r][c] > 0),
        default=None,
    )
    return (best[1], best[2]) if best else None
