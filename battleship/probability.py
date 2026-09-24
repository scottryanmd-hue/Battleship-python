"""Devin Security Swarm: where is the enemy fleet probably hiding?

Two estimators, both fed only by public information — the shot grid and which
ships have gone down. Neither ever looks at the defender's ship list.

`density` is the classic occurrence matrix used by most Battleship bots (the
"probability density" strategy): count, for every square, how many legal
placements of every surviving ship cover it, weighting placements that would
explain an open hit. It is instant and never fails, but it counts each ship
independently, so it ignores the fact that the ships have to fit on the board
*together*.

`posterior` answers the sharper question — "given everything I have shelled so
far, in what fraction of the fleet layouts that are still possible does a hull
sit on this square?" — by Monte Carlo over whole layouts. The prior is the
game's own placement process (ships laid down in fleet order, each uniformly at
random among the spots left free by the ones before it), and the evidence is
every miss, every open hit and every sunk hull.

Plain rejection sampling from that prior collapses once a couple of hits are on
the board — almost no random layout happens to cover them — so draws are made
from a proposal that deliberately steers ships onto uncovered hits and are then
reweighted by the likelihood ratio between prior and proposal (sequential
importance sampling). The weighted average is unbiased for the true posterior,
and the effective sample size, ESS = (Σw)² / Σw², says how much of the draw is
really informative. Below a floor on ESS the swarm stops pretending and falls
back to the density map, reporting which estimator it used.
"""

from __future__ import annotations

import random
import time

from .board import EXPLOSION_THRESHOLD, SIZE, Board

#: A placement that explains an existing hit is this much more interesting than
#: one covering only open water (density estimator only).
HIT_WEIGHT = 25

#: Layouts to draw, and how long to spend drawing them, before answering.
SAMPLES = 1200
TIME_BUDGET = 0.35
#: Less effective sample size than this and the estimate is too thin to publish.
MIN_ESS = 40.0
#: How often the proposal steers a ship onto a run of hits nothing covers yet.
#: Tuned: harder steering finds the hits more often but at wilder weights, and
#: 0.5 maximised effective sample size across quiet and wounded boards alike.
STEER = 0.5


def surviving_sizes(board: Board) -> list[int]:
    return [ship.size for ship in board.ships if not ship.sunk]


def _sink_limit(size: int) -> int:
    """Hits a ship of this size can be carrying and still be afloat."""
    return min(EXPLOSION_THRESHOLD, size) - 1


def _placements(size: int) -> list[list[tuple[int, int]]]:
    spots = []
    for horizontal in (True, False):
        rows = SIZE if horizontal else SIZE - size + 1
        cols = SIZE - size + 1 if horizontal else SIZE
        for row in range(rows):
            for col in range(cols):
                spots.append(
                    [(row, col + i) if horizontal else (row + i, col) for i in range(size)]
                )
    return spots


def _evidence(board: Board) -> tuple[list[list[bool]], list[list[bool]]]:
    """(blocked, wounded): squares no hull can occupy, and open hits."""
    blocked = [
        [board.grid[r][c] in (Board.MISS, Board.SUNK) for c in range(SIZE)] for r in range(SIZE)
    ]
    wounded = [[board.grid[r][c] == Board.HIT for c in range(SIZE)] for r in range(SIZE)]
    return blocked, wounded


def density(board: Board) -> list[list[float]]:
    """Occurrence matrix, normalised to 0..1 over the squares still shootable."""
    blocked, wounded = _evidence(board)
    scores = [[0.0] * SIZE for _ in range(SIZE)]

    for size in surviving_sizes(board):
        for cells in _placements(size):
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


def _clusters(mask: int) -> list[int]:
    """The separate runs of adjacent hits in this mask, one bitmask each."""
    seen = 0
    found = []
    for bit in range(SIZE * SIZE):
        cell = 1 << bit
        if not mask & cell or seen & cell:
            continue
        group = cell
        seen |= cell
        stack = [bit]
        while stack:
            row, col = divmod(stack.pop(), SIZE)
            for nr, nc in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
                if not (0 <= nr < SIZE and 0 <= nc < SIZE):
                    continue
                nbit = 1 << (nr * SIZE + nc)
                if mask & nbit and not seen & nbit:
                    seen |= nbit
                    group |= nbit
                    stack.append(nr * SIZE + nc)
        found.append(group)
    return found


def _cell_mask(cells: list[tuple[int, int]]) -> int:
    mask = 0
    for r, c in cells:
        mask |= 1 << (r * SIZE + c)
    return mask


def posterior(
    board: Board,
    rng: random.Random | None = None,
    samples: int = SAMPLES,
    time_budget: float = TIME_BUDGET,
) -> tuple[list[list[float]], float]:
    """P(hull on this square | every shot so far), and the estimate's ESS.

    Sequential importance sampling: each surviving ship is placed in turn, the
    proposal favouring spots that cover a hit nothing has explained yet, and
    every layout carries the weight that undoes that steering.
    """
    rng = rng or random.Random()
    blocked, wounded = _evidence(board)
    sizes = surviving_sizes(board)
    hits_mask = _cell_mask(
        [(r, c) for r in range(SIZE) for c in range(SIZE) if wounded[r][c]]
    )

    # Placements as (bitmask, cells) so overlap tests are one integer AND.
    # `every` is what the game's own placer would consider; `legal` also obeys
    # the evidence — no hull sits on a miss or on a sunk wreck, and a ship still
    # afloat cannot be carrying enough hits to have gone down.
    every: dict[int, list[int]] = {}
    legal: dict[int, list[tuple[int, list[tuple[int, int]]]]] = {}
    for size in set(sizes):
        spots = []
        masks = []
        for cells in _placements(size):
            mask = _cell_mask(cells)
            masks.append(mask)
            if any(blocked[r][c] for r, c in cells):
                continue
            if sum(1 for r, c in cells if wounded[r][c]) > _sink_limit(size):
                continue
            spots.append((mask, cells))
        every[size] = masks
        legal[size] = spots

    totals = [[0.0] * SIZE for _ in range(SIZE)]
    weight_sum = 0.0
    weight_sq_sum = 0.0
    drawn = 0
    deadline = time.monotonic() + time_budget
    while drawn < samples and time.monotonic() < deadline:
        drawn += 1
        taken = 0
        uncovered = hits_mask
        layout: list[tuple[int, int]] = []
        weight = 1.0
        for index, size in enumerate(sizes):
            free = [spot for spot in legal[size] if not spot[0] & taken]
            if not free:
                weight = 0.0
                break
            # One wounded hull per ship: the proposal picks a run of open hits
            # and lands this ship on it, harder the closer the fleet is to
            # running out of ships that could still explain them.
            groups = _clusters(uncovered)
            # Pressure: the share of the ships still to be placed that have to
            # land on a wounded run. At 1 or more every remaining ship is
            # spoken for, so this one is steered outright.
            steer = 0.0
            if groups:
                steer = min(1.0, max(STEER, len(groups) / (len(sizes) - index)))
            fits = [[spot for spot in free if spot[0] & group] for group in groups]

            spot = None
            if groups and rng.random() < steer:
                choices = fits[rng.randrange(len(groups))]
                spot = rng.choice(choices) if choices else None
            if spot is None:
                spot = rng.choice(free)

            # Prior: uniform over everything the game's placer could have
            # chosen here. Proposal: the mixture just drawn from.
            prior = sum(1 for mask in every[size] if not mask & taken)
            proposal = (1.0 - steer) / len(free)
            for group, choices in zip(groups, fits):
                share = steer / len(groups)
                if not choices:
                    proposal += share / len(free)  # that run fell through to free
                elif spot[0] & group:
                    proposal += share / len(choices)
            weight *= 1.0 / prior / proposal
            taken |= spot[0]
            uncovered &= ~spot[0]
            layout.extend(spot[1])
        if weight <= 0.0 or uncovered:
            continue  # this layout cannot explain the hits: zero posterior mass
        weight_sum += weight
        weight_sq_sum += weight * weight
        for r, c in layout:
            totals[r][c] += weight

    if weight_sum <= 0.0:
        return [[0.0] * SIZE for _ in range(SIZE)], 0.0
    ess = weight_sum * weight_sum / weight_sq_sum
    grid = [
        [
            0.0 if blocked[r][c] or wounded[r][c] else round(totals[r][c] / weight_sum, 4)
            for c in range(SIZE)
        ]
        for r in range(SIZE)
    ]
    return grid, round(ess, 1)


def heatmap(board: Board, rng: random.Random | None = None) -> dict:
    """The swarm's read on the enemy grid, with its own provenance attached."""
    probability, ess = posterior(board, rng)
    if ess >= MIN_ESS:
        peak = max(max(row) for row in probability)
        heat = [[round(v / peak, 4) if peak > 0 else 0.0 for v in row] for row in probability]
        method = "posterior"
    else:
        heat = density(board)
        probability = [row[:] for row in heat]
        method = "density"
        ess = 0.0

    best = max(
        ((heat[r][c], r, c) for r in range(SIZE) for c in range(SIZE) if heat[r][c] > 0),
        default=None,
    )
    return {
        "heat": heat,
        "probability": probability,
        "best": (best[1], best[2]) if best else None,
        "method": method,
        "ess": ess,
    }


def best_square(board: Board, rng: random.Random | None = None) -> tuple[int, int] | None:
    """The square the swarm would shell next, if any square is left."""
    return heatmap(board, rng)["best"]
