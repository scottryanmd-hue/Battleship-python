"""Everything that gets drawn to the terminal."""

from __future__ import annotations

import re
import sys
import time
import unicodedata

from . import art
from .board import SIZE, LETTERS, Board

CELL = 3


def clear() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def cell_text(board: Board, row: int, col: int, reveal: bool, team_glyph: str, accent: str) -> str:
    mark = board.grid[row][col]
    if mark == Board.SUNK:
        return art.color("#", art.DARK)
    if mark == Board.HIT:
        return art.color("✸", art.RED + art.BOLD)
    if mark == Board.MISS:
        return art.color("o", art.BLUE)
    if reveal and board.ship_at(row, col) is not None:
        return art.color(team_glyph, accent + art.BOLD)
    return art.color(art.WATER, art.NAVY)


def render_board(
    board: Board,
    *,
    title: str,
    reveal: bool,
    team_glyph: str,
    accent: str,
    overlay: dict[tuple[int, int], str] | None = None,
) -> list[str]:
    overlay = overlay or {}
    width = SIZE * CELL + 3
    lines = [art.color(f"{title:^{width}}", accent + art.BOLD)]
    header = "   " + "".join(f"{n:^{CELL}}" for n in range(1, SIZE + 1))
    lines.append(art.color(header, art.GREY))
    for r in range(SIZE):
        row_cells = []
        for c in range(SIZE):
            glyph = overlay.get((r, c)) or cell_text(board, r, c, reveal, team_glyph, accent)
            lead = (CELL - 1) // 2
            row_cells.append(" " * lead + glyph + " " * (CELL - 1 - lead))
        lines.append(art.color(f" {LETTERS[r]} ", art.GREY) + "".join(row_cells))
    return lines


def display_width(text: str) -> int:
    """Terminal column width, counting wide glyphs (emoji, CJK) as two."""
    total = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        if unicodedata.east_asian_width(ch) in ("W", "F") or 0x1F300 <= ord(ch) <= 0x1FAFF:
            total += 2
        else:
            total += 1
    return total


def pad(text: str, width: int, align: str = "^") -> str:
    slack = max(0, width - display_width(text))
    if align == "<":
        return text + " " * slack
    if align == ">":
        return " " * slack + text
    left = slack // 2
    return " " * left + text + " " * (slack - left)


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def visible_len(text: str) -> int:
    return display_width(ANSI_RE.sub("", text))


def side_by_side(left: list[str], right: list[str], gap: int = 6) -> list[str]:
    width = max((visible_len(l) for l in left), default=0)
    height = max(len(left), len(right))
    left = left + [""] * (height - len(left))
    right = right + [""] * (height - len(right))
    return [l + " " * (width - visible_len(l) + gap) + r for l, r in zip(left, right)]


def scoreboard(stats: dict) -> list[str]:
    """A high-school-gym style scoreboard with the Devin otter up top."""
    a = art
    o = a.ORANGE
    W1, W2, W3 = 19, 27, 23
    bar = a.color("║", o)

    def row(c1: str, c2: str, c3: str, k1: str, k2: str, k3: str) -> str:
        return (
            bar
            + a.color(pad(c1, W1), k1)
            + bar
            + a.color(pad(c2, W2), k2)
            + bar
            + a.color(pad(c3, W3), k3)
            + bar
        )

    return [
        a.color("╔" + "═" * (W1 + W2 + W3 + 2) + "╗", o),
        bar
        + a.color(pad("🦦  D E V I N   F I E L D H O U S E   ·   S C O R E B O A R D  🦦", W1 + W2 + W3 + 2), a.YELLOW + a.BOLD)
        + bar,
        a.color("╠" + "═" * W1 + "╦" + "═" * W2 + "╦" + "═" * W3 + "╣", o),
        row("HOME", "⬢ ⬡ ⬢", "AWAY", a.WHITE + a.BOLD, a.GREY, a.WHITE + a.BOLD),
        row(
            "🦦 DEVIN 🦦",
            f"{stats['devin_sunk']}  ―  {stats['cursor_sunk']}",
            "◆ CURSOR ◆",
            a.ORANGE + a.BOLD,
            a.RED + a.BOLD,
            a.WHITE + a.BOLD,
        ),
        a.color("╠" + "═" * W1 + "╬" + "═" * W2 + "╬" + "═" * W3 + "╣", o),
        row(
            f"HITS       {stats['devin_hits']:>3}",
            f"INNING (TURN) {stats['turn']:>3}",
            f"HITS       {stats['cursor_hits']:>3}",
            a.YELLOW,
            a.GREEN,
            a.YELLOW,
        ),
        row(
            f"MISSES     {stats['devin_misses']:>3}",
            "⬢ COGNITION MISSILES ⬢",
            f"MISSES     {stats['cursor_misses']:>3}",
            a.BLUE,
            a.ORANGE,
            a.BLUE,
        ),
        row(
            f"SHIPS SUNK {stats['devin_sunk']:>3}",
            f"FLEET {stats['devin_alive']} ⬢  vs  ◆ {stats['cursor_alive']}",
            f"SHIPS SUNK {stats['cursor_sunk']:>3}",
            a.RED,
            a.WHITE,
            a.RED,
        ),
        a.color("╚" + "═" * W1 + "╩" + "═" * W2 + "╩" + "═" * W3 + "╝", o),
    ]


def fleet_status(board: Board, label: str, accent: str) -> list[str]:
    lines = [art.color(f"{label} FLEET", accent + art.BOLD)]
    for ship in board.ships:
        if ship.sunk:
            bar = art.color("SUNK 💀", art.DARK)
        else:
            dots = "".join("✸" if cell in ship.hits else "▪" for cell in ship.cells)
            bar = art.color(dots, art.RED if ship.hits else accent)
        lines.append(f"  {ship.name:<11} {bar}")
    return lines


class Screen:
    """Draws the whole arena; `delay` scales every animation pause."""

    def __init__(self, player_board: Board, ai_board: Board, stats: dict, speed: float = 1.0):
        self.player_board = player_board
        self.ai_board = ai_board
        self.stats = stats
        self.speed = speed

    def pause(self, seconds: float) -> None:
        if self.speed > 0:
            time.sleep(seconds * self.speed)

    def frame(
        self,
        *,
        message: str = "",
        overlay_ai: dict | None = None,
        overlay_player: dict | None = None,
        extra: list[str] | None = None,
    ) -> None:
        clear()
        out = [art.banner(), ""]
        out += scoreboard(self.stats)
        out.append("")
        left = render_board(
            self.player_board,
            title="HOME · DEVIN WATERS",
            reveal=True,
            team_glyph=art.COGNITION_GLYPH,
            accent=art.ORANGE,
            overlay=overlay_player,
        )
        right = render_board(
            self.ai_board,
            title="AWAY · CURSOR WATERS",
            reveal=False,
            team_glyph=art.CURSOR_GLYPH,
            accent=art.WHITE,
            overlay=overlay_ai,
        )
        out += side_by_side(left, right)
        out.append("")
        out += side_by_side(
            fleet_status(self.player_board, "DEVIN", art.ORANGE),
            fleet_status(self.ai_board, "CURSOR", art.WHITE),
        )
        out.append("")
        out.append(art.color("  ⬢ = Devin ship   ◆ = Cursor ship   ✸ = hit   o = miss   # = sunk", art.DIM))
        if extra:
            out.append("")
            out += extra
        if message:
            out.append("")
            out.append(message)
        sys.stdout.write("\n".join(out) + "\n")
        sys.stdout.flush()
