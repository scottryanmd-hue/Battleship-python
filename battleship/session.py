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
from .probability import heatmap

#: Squares a Devin Fusion salvo puts in the water, the aimed one included.
FUSION_SHOTS = 2

#: Columns (1-based) SWE-2 walks end to end.
SWE2_COLUMNS = (1, 4, 6)


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

    def _check_target(self, row: int, col: int) -> None:
        if self.winner is not None:
            raise ValueError("The game is already over.")
        if not (0 <= row < SIZE and 0 <= col < SIZE):
            raise ValueError("That square is off the board.")
        if self.ai.already_shot(row, col):
            raise ValueError("You already shelled that square.")

    def _cursor_reply(self, events: list[dict]) -> bool:
        """Cursor fires back. True if the game carries on."""
        row, col = self.ai_targets.pop()
        while self.player.already_shot(row, col):
            row, col = self.ai_targets.pop()
        events.append(self._shoot("cursor", row, col))
        if self.player.defeated:
            self.winner = "cursor"
            return False
        self.turn += 1
        return True

    def fire(self, row: int, col: int) -> list[dict]:
        """Devin's shot, then Cursor's reply. Returns the events, in order."""
        self._check_target(row, col)
        events = [self._shoot("devin", row, col)]
        if self.ai.defeated:
            self.winner = "devin"
            return events
        self._cursor_reply(events)
        return events

    def fusion_targets(self, row: int, col: int, count: int = FUSION_SHOTS) -> list[list[int]]:
        """The aimed square and the nearest unshelled squares around it.

        The cross around the target comes first; where one of those squares has
        already been shelled the salvo spills outward — diagonals, then the next
        ring — so a Fusion always puts `count` live missiles in the water, as
        long as Cursor's waters still hold that many unshot squares.
        """
        ring = [
            (-1, 0), (0, -1), (0, 1), (1, 0),  # the cross, first
            (-1, -1), (-1, 1), (1, -1), (1, 1),  # then the corners
        ]
        ring += sorted(
            (
                (dr, dc)
                for dr in range(-3, 4)
                for dc in range(-3, 4)
                if (dr, dc) != (0, 0) and (dr, dc) not in ring
            ),
            key=lambda d: (max(abs(d[0]), abs(d[1])), abs(d[0]) + abs(d[1]), d),
        )

        targets = [[row, col]]
        for dr, dc in ring:
            if len(targets) >= count:
                break
            r, c = row + dr, col + dc
            if 0 <= r < SIZE and 0 <= c < SIZE and not self.ai.already_shot(r, c):
                targets.append([r, c])
        return targets

    def swe2(self) -> list[dict]:
        """SWE-2 sweep: every open square in columns 1, 4 and 6, then Cursor replies."""
        if self.winner is not None:
            raise ValueError("The game is already over.")
        events: list[dict] = []
        for column in SWE2_COLUMNS:
            col = column - 1
            for row in range(SIZE):
                if self.ai.already_shot(row, col):
                    continue
                events.append(self._shoot("devin", row, col))
                events[-1]["barrage"] = True
                if self.ai.defeated:
                    self.winner = "devin"
                    return events
        if not events:
            raise ValueError("Columns 1, 4 and 6 are already shelled out.")
        self._cursor_reply(events)
        return events

    def outsource(self) -> list[dict]:
        """Outsourced IT: Cursor's largest surviving hull surfaces and goes down."""
        if self.winner is not None:
            raise ValueError("The game is already over.")
        afloat = [ship for ship in self.ai.ships if not ship.sunk]
        if not afloat:
            raise ValueError("Cursor has nothing left afloat.")
        target = max(afloat, key=lambda ship: ship.size)
        reveal = _ship_state(target, reveal=True)
        events: list[dict] = []
        # One missile per square of the hull: a five-square Carrier takes five,
        # even though three cognition missiles are enough to detonate her and
        # squares Devin already hit need no second hole. Those extra missiles
        # are for show and are fired first, so the salvo still ends on the shot
        # that actually sinks her.
        needed = min(EXPLOSION_THRESHOLD, target.size) - len(target.hits)
        live = [cell for cell in target.cells if not self.ai.already_shot(*cell)][:needed]
        for row, col in target.cells:
            if (row, col) in live:
                continue
            events.append({
                "team": "devin",
                "row": row,
                "col": col,
                "coord": format_coord(row, col),
                "result": "hit",
                "ship": target.name,
                "exploded": False,
                "hits": len(target.hits),
                "restrike": True,
            })
        for row, col in live:
            events.append(self._shoot("devin", row, col))
        for event in events:
            event["outsourced"] = True
        if events:
            events[0]["reveal"] = reveal
        if self.ai.defeated:
            self.winner = "devin"
            return events
        self._cursor_reply(events)
        return events

    def fusion(self, row: int, col: int) -> list[dict]:
        """A Devin Fusion salvo: the called square plus one neighbour, then Cursor replies."""
        self._check_target(row, col)
        events = []
        for r, c in self.fusion_targets(row, col):
            events.append(self._shoot("devin", r, c))
            events[-1]["fusion"] = True
            if self.ai.defeated:
                self.winner = "devin"
                return events
        self._cursor_reply(events)
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
            "swarm": self.swarm(),
        }

    def swarm(self) -> dict:
        """Devin-only intel: the probability heat map over Cursor's waters.

        Recomputed from scratch after every shot, so the map always reflects
        every miss, hit and wreck currently on the board.
        """
        read = heatmap(self.ai, self.rng)
        best = read["best"]
        return {
            "heat": read["heat"],
            "probability": read["probability"],
            "best": format_coord(*best) if best else None,
            "method": read["method"],
            "ess": read["ess"],
        }
