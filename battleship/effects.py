"""Missile flight, smoke trails, explosions and the otter finisher."""

from __future__ import annotations

from . import art
from .board import EXPLOSION_THRESHOLD, SIZE, Ship, format_coord
from .render import Screen

TRAIL_CHARS = ["˙", "°", "∘", "·"]


def _launch_lines(team: str) -> list[str]:
    if team == "devin":
        ship = art.ship_broadside("U.S.S. DEVIN", "DEVIN", art.COGNITION_GLYPH, art.ORANGE)
        return ship + [art.color("   ⬢➤  launching cognition missile...", art.ORANGE + art.BOLD)]
    ship = art.ship_broadside("C.S.S. CURSOR", "CURSOR", art.CURSOR_GLYPH, art.WHITE)
    return ship + [art.color("   ◆➤  Cursor returns fire...", art.WHITE + art.BOLD)]


def _overlay_kwargs(team: str, overlay: dict) -> dict:
    return {"overlay_ai": overlay} if team == "devin" else {"overlay_player": overlay}


def fly_missile(screen: Screen, team: str, row: int, col: int) -> None:
    """Send a logo-shaped missile across the target grid, trailing smoke."""
    head = (
        art.color(art.COGNITION_GLYPH, art.ORANGE)
        if team == "devin"
        else art.color(art.CURSOR_GLYPH, art.WHITE)
    )
    launch = _launch_lines(team)
    if team == "devin":
        path = list(range(0, col + 1))
    else:
        path = list(range(SIZE - 1, col - 1, -1))
    if not path:
        path = [col]

    screen.frame(
        message=art.color(f"  FIRING AT {format_coord(row, col)}", art.YELLOW + art.BOLD),
        extra=launch,
        **_overlay_kwargs(team, {}),
    )
    screen.pause(0.35)

    for i, c in enumerate(path):
        overlay = {(row, c): head}
        for t, trail_char in enumerate(TRAIL_CHARS, start=1):
            if i - t >= 0:
                overlay[(row, path[i - t])] = art.color(trail_char, art.GREY if t < 3 else art.DARK)
        screen.frame(
            message=art.color(f"  ⇢ incoming: {format_coord(row, c)}", art.GREY),
            extra=launch,
            **_overlay_kwargs(team, overlay),
        )
        screen.pause(0.07)


def splash(screen: Screen, team: str, row: int, col: int) -> None:
    for glyph, code in ((" ", art.BLUE), ("◌", art.BLUE), ("o", art.BLUE)):
        screen.frame(
            message=art.color("  SPLASH! Missile buried itself in open water. MISS.", art.BLUE + art.BOLD),
            **_overlay_kwargs(team, {(row, col): art.color(glyph, code)}),
        )
        screen.pause(0.12)
    screen.pause(0.3)


def impact(screen: Screen, team: str, row: int, col: int, ship: Ship) -> None:
    hull = f"{ship.name} ({ship.hit_count}/{min(EXPLOSION_THRESHOLD, ship.size)} missiles to detonation)"
    for glyph, code in (("✷", art.YELLOW), ("✸", art.RED), ("✹", art.YELLOW), ("✸", art.RED)):
        screen.frame(
            message=art.color(f"  DIRECT HIT on the {hull}", art.RED + art.BOLD),
            **_overlay_kwargs(team, {(row, col): art.color(glyph, code + art.BOLD)}),
        )
        screen.pause(0.12)
    screen.pause(0.35)


def explode(screen: Screen, team: str, ship: Ship, exploded: bool) -> None:
    flash = {cell: art.color("✹", art.YELLOW + art.BOLD) for cell in ship.cells}
    missiles = min(EXPLOSION_THRESHOLD, ship.size)
    if exploded and team == "devin":
        headline = f"  💥 {missiles} COGNITION MISSILES — the {ship.name} DETONATES! 💥"
    else:
        headline = f"  💥 The {ship.name} is breaking apart! 💥"
    for frame in art.EXPLOSION_FRAMES:
        screen.frame(
            message=art.color(headline, art.RED + art.BOLD),
            extra=[art.color(line, art.YELLOW) for line in frame],
            **_overlay_kwargs(team, flash),
        )
        screen.pause(0.22)


def otter_finisher(screen: Screen, ship: Ship) -> None:
    """The Devin otter flies in and delivers the killing blow to a Cursor ship."""
    width = 40
    for step in range(0, width, 6):
        screen.frame(
            message=art.color("  🦦  INCOMING OTTER  🦦", art.ORANGE + art.BOLD),
            extra=[
                art.color(" " * step + "🦦💨", art.ORANGE),
                art.color(" " * max(0, step - 2) + "  ⬢ ⬢ ⬢", art.GREY),
            ],
            overlay_ai={cell: art.color("✹", art.YELLOW) for cell in ship.cells},
        )
        screen.pause(0.08)

    screen.frame(
        message=art.color(
            f"  🦦 FINAL BLOW! The Devin otter sinks the Cursor {ship.name}! 🦦",
            art.ORANGE + art.BOLD,
        ),
        extra=[art.color(line, art.ORANGE) for line in art.OTTER_BIG]
        + ["", art.color("        ⬢  C O G N I T I O N   S T R I K E  ⬢", art.ORANGE + art.BOLD)],
        overlay_ai={cell: art.color("#", art.DARK) for cell in ship.cells},
    )
    screen.pause(1.6)


def cursor_finisher(screen: Screen, ship: Ship) -> None:
    screen.frame(
        message=art.color(f"  ◆ Cursor sinks the Devin {ship.name}. ◆", art.WHITE + art.BOLD),
        extra=[art.color(line, art.WHITE) for line in art.CURSOR_LOGO],
        overlay_player={cell: art.color("#", art.DARK) for cell in ship.cells},
    )
    screen.pause(1.4)
