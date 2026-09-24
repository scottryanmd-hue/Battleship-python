"""Game flow: placement, turns and the endgame."""

from __future__ import annotations

import random

from . import art, effects
from .board import (
    FLEET,
    SIZE,
    Board,
    PlacementError,
    format_coord,
    parse_coord,
)
from .render import ARENA_W, Screen, clear, fill, footer, menu_screen, panel


class Game:
    def __init__(self, speed: float = 1.0, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.player = Board()   # HOME · Devin
        self.ai = Board()       # AWAY · Cursor
        self.stats = {
            "devin_hits": 0,
            "devin_misses": 0,
            "devin_sunk": 0,
            "cursor_hits": 0,
            "cursor_misses": 0,
            "cursor_sunk": 0,
            "turn": 1,
            "devin_alive": len(FLEET),
            "cursor_alive": len(FLEET),
        }
        self.screen = Screen(self.player, self.ai, self.stats, speed=speed)
        self.ai_targets = [(r, c) for r in range(SIZE) for c in range(SIZE)]
        self.rng.shuffle(self.ai_targets)

    # -- setup -------------------------------------------------------------
    def ask(self, prompt: str) -> str:
        try:
            return input(prompt)
        except EOFError:
            raise SystemExit("\nNo input available — bye.")

    def intro(self) -> None:
        for step in range(4):
            clear()
            out = menu_screen(step)
            out += [
                fill(art.color("  Coordinates look like B7 (row A-J, column 1-10).", art.INK), ARENA_W, art.BG_WHITE),
                fill(art.color("  Three cognition missiles detonate a hull — then the otter finishes it.", art.INK), ARENA_W, art.BG_WHITE),
                fill("", ARENA_W, art.BG_WHITE),
            ]
            out += footer("point at a channel and press A")
            print("\n".join(out))
            self.screen.pause(0.35)

    def place_player_fleet(self) -> None:
        self.intro()
        choice = self.ask(art.color(f"  {art.POINTER} Place your fleet [r]andomly or [m]anually? (r/m): ", art.WII_BLUE)).strip().lower()
        if choice.startswith("m"):
            self.place_manually()
        else:
            self.player.place_fleet_randomly(self.rng)
        self.ai.place_fleet_randomly(self.rng)

    def place_manually(self) -> None:
        for name, size in FLEET:
            while True:
                self.screen.frame(
                    message=art.color(f"  {art.POINTER} Place your {name} ({size} cells).", art.WII_BLUE + art.BOLD)
                )
                raw = self.ask(art.color(f"  Bow coordinate for {name} (e.g. B3): ", art.WII_BLUE))
                orient = self.ask(art.color("  Orientation [h]orizontal / [v]ertical: ", art.WII_BLUE))
                try:
                    row, col = parse_coord(raw)
                    horizontal = not orient.strip().lower().startswith("v")
                    self.player.place(name, size, row, col, horizontal)
                    break
                except (ValueError, PlacementError) as exc:
                    print(art.color(f"  {exc}", art.RED))
                    self.ask(art.color("  Press Enter to retry.", art.GREY))

    # -- turns -------------------------------------------------------------
    def player_turn(self) -> None:
        while True:
            self.screen.frame(
                message=art.color(f"  {art.POINTER} YOUR SHOT, DEVIN. Aim at Cursor waters (e.g. F5), or 'q' to resign.", art.ORANGE + art.BOLD)
            )
            raw = self.ask(art.color("  Target: ", art.ORANGE))
            if raw.strip().lower() in {"q", "quit", "exit"}:
                raise SystemExit(
                    "\n"
                    + fill(art.color("  Devin resigns. Cursor takes the trophy.", art.INK), ARENA_W, art.BG_WHITE)
                    + "\n"
                )
            try:
                row, col = parse_coord(raw)
            except ValueError as exc:
                print(art.color(f"  {exc}", art.RED))
                self.ask(art.color("  Press Enter.", art.GREY))
                continue
            if self.ai.already_shot(row, col):
                print(art.color("  You already shelled that square.", art.RED))
                self.ask(art.color("  Press Enter.", art.GREY))
                continue
            break

        self.resolve_shot("devin", row, col)

    def ai_turn(self) -> None:
        row, col = self.ai_targets.pop()
        while self.player.already_shot(row, col):
            row, col = self.ai_targets.pop()
        self.screen.frame(message=art.color(f"  Cursor is targeting {format_coord(row, col)}...", art.INK + art.BOLD))
        self.screen.pause(0.5)
        self.resolve_shot("cursor", row, col)

    def resolve_shot(self, team: str, row: int, col: int) -> None:
        target = self.ai if team == "devin" else self.player
        effects.fly_missile(self.screen, team, row, col)
        result, ship, exploded = target.fire(row, col)

        if result == "miss":
            self.stats[f"{team}_misses"] += 1
            effects.splash(self.screen, team, row, col)
            return

        self.stats[f"{team}_hits"] += 1
        if result == "hit":
            effects.impact(self.screen, team, row, col, ship)
            return

        effects.explode(self.screen, team, ship, exploded)
        self.stats[f"{team}_sunk"] += 1
        if team == "devin":
            self.stats["cursor_alive"] -= 1
            effects.otter_finisher(self.screen, ship)
        else:
            self.stats["devin_alive"] -= 1
            effects.cursor_finisher(self.screen, ship)

    # -- main loop ---------------------------------------------------------
    def run(self) -> None:
        self.place_player_fleet()
        while True:
            self.player_turn()
            if self.ai.defeated:
                return self.finish(winner="devin")
            self.ai_turn()
            if self.player.defeated:
                return self.finish(winner="cursor")
            self.stats["turn"] += 1

    def finish(self, winner: str) -> None:
        if winner == "devin":
            extra = panel(
                [art.color(line, art.ORANGE) for line in art.OTTER_BIG]
                + ["", art.color("  🦦  F I N A L :  D E V I N   W I N S  🦦", art.ORANGE + art.BOLD)],
                title="RESULTS",
                accent=art.ORANGE,
            )
        else:
            extra = panel(
                [art.color(line, art.INK) for line in art.CURSOR_LOGO]
                + ["", art.color("  ◆  F I N A L :  C U R S O R   W I N S  ◆", art.INK + art.BOLD)],
                title="RESULTS",
                accent=art.INK,
            )
        self.screen.frame(
            message=art.color(
                f"  Game over in {self.stats['turn']} innings.  "
                f"Devin {self.stats['devin_hits']}H/{self.stats['devin_misses']}M · "
                f"Cursor {self.stats['cursor_hits']}H/{self.stats['cursor_misses']}M",
                art.WII_BLUE,
            ),
            extra=extra,
        )
        print()
