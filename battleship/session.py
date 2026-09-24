"""Headless game session: the same rules as the terminal game, as plain data.

The terminal front-end drives `game.Game`, which owns its own rendering and
`input()` loop. The browser front-end needs the same rules with no I/O at all,
so this module runs a game as a state machine: you fire at a square and get back
the list of events that happened (both sides' shots), and the whole board state
serialises to JSON.
"""

from __future__ import annotations

import random

from .board import EXPLOSION_THRESHOLD, FLEET, SIZE, Board, Ship, format_coord


def _ship_state(ship: Ship, reveal: bool) -> dict | None:
    """What the client is allowed to know about a ship."""
    if not reveal and not ship.sunk:
        return None
    horizontal = ship.cells[0][0] == ship.cells[-1][0]
    return {
        "name": ship.name,
        "size": ship.size,
        "row": ship.cells[0][0],
        "col": ship.cells[0][1],
        "horizontal": horizontal,
        "sunk": ship.sunk,
        "hits": sorted(list(cell) for cell in ship.hits),
    }


class Session:
    """One game of Devin (home) versus Cursor (away)."""

    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.player = Board()
        self.ai = Board()
        self.player.place_fleet_randomly(self.rng)
        self.ai.place_fleet_randomly(self.rng)
        self.ai_targets = [(r, c) for r in range(SIZE) for c in range(SIZE)]
        self.rng.shuffle(self.ai_targets)
        self.turn = 1
        self.winner: str | None = None
        self.log: list[str] = ["Wii Sports Resort weather: clear. Devin fires first."]
        self.stats = {
            "devin_hits": 0,
            "devin_misses": 0,
            "devin_sunk": 0,
            "cursor_hits": 0,
            "cursor_misses": 0,
            "cursor_sunk": 0,
        }

    def reroll_home_fleet(self) -> None:
        """Re-place Devin's fleet; only legal before the first shot."""
        if self.turn != 1 or any(self.stats.values()):
            raise ValueError("The battle has started — no rearranging now.")
        self.player = Board()
        self.player.place_fleet_randomly(self.rng)

    # -- shots -------------------------------------------------------------
    def _shoot(self, team: str, row: int, col: int) -> dict:
        target = self.ai if team == "devin" else self.player
        result, ship, exploded = target.fire(row, col)
        event = {
            "team": team,
            "row": row,
            "col": col,
            "coord": format_coord(row, col),
            "result": result,
            "ship": ship.name if ship else None,
            "exploded": exploded,
            "hits": len(ship.hits) if ship else 0,
        }
        who = "Devin" if team == "devin" else "Cursor"
        if result == "miss":
            self.stats[f"{team}_misses"] += 1
            self.log.append(f"{who} missiles splash down at {event['coord']}.")
        else:
            self.stats[f"{team}_hits"] += 1
            if result == "sunk":
                self.stats[f"{team}_sunk"] += 1
                blow = (
                    f"{min(EXPLOSION_THRESHOLD, ship.size)} missiles detonate"
                    if exploded
                    else "The last cell goes under"
                )
                finisher = "the otter flies in" if team == "devin" else "Cursor closes in"
                self.log.append(f"{blow} the {ship.name} at {event['coord']} — {finisher}.")
            else:
                self.log.append(f"{who} hits the hull at {event['coord']}.")
        self.log = self.log[-6:]
        return event

    def fire(self, row: int, col: int) -> list[dict]:
        """Devin's shot, then Cursor's reply. Returns the events, in order."""
        if self.winner is not None:
            raise ValueError("The game is already over.")
        if not (0 <= row < SIZE and 0 <= col < SIZE):
            raise ValueError("That square is off the board.")
        if self.ai.already_shot(row, col):
            raise ValueError("You already shelled that square.")

        events = [self._shoot("devin", row, col)]
        if self.ai.defeated:
            self.winner = "devin"
            return events

        ai_row, ai_col = self.ai_targets.pop()
        while self.player.already_shot(ai_row, ai_col):
            ai_row, ai_col = self.ai_targets.pop()
        events.append(self._shoot("cursor", ai_row, ai_col))
        if self.player.defeated:
            self.winner = "cursor"
            return events

        self.turn += 1
        return events

    # -- state -------------------------------------------------------------
    def board_state(self, board: Board, reveal: bool) -> dict:
        return {
            "grid": ["".join(row) for row in board.grid],
            "ships": [s for s in (_ship_state(sh, reveal) for sh in board.ships) if s],
            "fleet": [
                {"name": sh.name, "size": sh.size, "hits": len(sh.hits), "sunk": sh.sunk}
                for sh in board.ships
            ],
        }

    def state(self) -> dict:
        return {
            "size": SIZE,
            "turn": self.turn,
            "winner": self.winner,
            "log": self.log,
            "stats": {
                **self.stats,
                "devin_alive": len(FLEET) - self.stats["cursor_sunk"],
                "cursor_alive": len(FLEET) - self.stats["devin_sunk"],
            },
            "home": self.board_state(self.player, reveal=True),
            "away": self.board_state(self.ai, reveal=self.winner is not None),
        }
