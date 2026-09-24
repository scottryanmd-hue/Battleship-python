"""Everything that gets drawn to the terminal, styled like a Wii channel."""

from __future__ import annotations

import re
import sys
import time
import unicodedata
from datetime import datetime

from . import art
from .board import SIZE, LETTERS, Board

CELL = 3
BOARD_W = SIZE * CELL + 3
ARENA_W = 78


def clear() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


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


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def visible_len(text: str) -> int:
    return display_width(ANSI_RE.sub("", text))


def pad(text: str, width: int, align: str = "^") -> str:
    slack = max(0, width - display_width(text))
    if align == "<":
        return text + " " * slack
    if align == ">":
        return " " * slack + text
    left = slack // 2
    return " " * left + text + " " * (slack - left)


def tint(text: str, bg: str) -> str:
    """Keep `bg` behind a line whose inner colours reset as they finish."""
    return bg + text.replace(art.RESET, art.RESET + bg) + art.RESET


def fill(text: str, width: int, bg: str, align: str = "<") -> str:
    slack = max(0, width - visible_len(text))
    if align == "^":
        left = slack // 2
        text = " " * left + text + " " * (slack - left)
    elif align == ">":
        text = " " * slack + text
    else:
        text = text + " " * slack
    return tint(text, bg)


def panel(
    lines: list[str],
    *,
    title: str = "",
    accent: str = art.WII_BLUE,
    bg: str = art.BG_WHITE,
    width: int | None = None,
) -> list[str]:
    """A glossy rounded Wii tile wrapped around some content."""
    inner = max([width or 0] + [visible_len(l) for l in lines] + [visible_len(title) + 6])
    inner += 2
    edge = accent + bg

    if title:
        head = f"─ {title} "
        top = "╭" + head + "─" * max(0, inner - visible_len(head)) + "╮"
    else:
        top = "╭" + "─" * inner + "╮"
    out = [tint(art.color(top, edge), bg)]
    for line in lines:
        body = fill(" " + line, inner, bg)
        out.append(tint(art.color("│", edge) + body + art.color("│", edge), bg))
    out.append(tint(art.color("╰" + "─" * inner + "╯", edge), bg))
    return out


def header() -> list[str]:
    """The blue channel bar that tops every Wii screen."""
    clock = datetime.now().strftime("%a  %H:%M")
    left = " 🦦  B A T T L E S H I P   C H A N N E L    ◉ vs ◆"
    gap = max(1, ARENA_W - display_width(left) - display_width(clock) - 1)
    line = fill(
        art.color(left, art.BOLD) + " " * gap + art.color(clock + " ", art.SILVER),
        ARENA_W,
        art.BG_BLUE,
    )
    rule = fill("", ARENA_W, art.BG_BLUE)
    return [rule, line, rule]


def footer(hint: str = "") -> list[str]:
    """The Wii Menu tray: rounded buttons and a pointer hint."""
    buttons = "  ".join(art.color(f"( {b} )", art.INK) for b in ("Wii", "Mii"))
    text = (
        " "
        + buttons
        + "  "
        + art.color("( A )", art.WII_BLUE + art.BOLD)
        + art.color(f" {art.POINTER} {hint}" if hint else "", art.INK)
    )
    return [fill(text, ARENA_W, art.BG_PANEL)]


def channel_tile(lines: list[str], *, accent: str, selected: bool) -> list[str]:
    body = [pad(l, 22) for l in lines]
    if selected:
        body = [art.color(l, accent + art.BOLD) for l in body]
    else:
        body = [art.color(l, art.SOFT) for l in body]
    return panel(body, accent=accent if selected else art.SILVER, width=22)


def menu_screen(step: int) -> list[str]:
    """The Wii Menu: two channels and a hand pointer drifting between them."""
    devin = channel_tile(art.CHANNEL_DEVIN, accent=art.ORANGE, selected=step % 2 == 0)
    cursor = channel_tile(art.CHANNEL_CURSOR, accent=art.INK, selected=step % 2 == 1)
    pointer_col = 6 if step % 2 == 0 else 36
    out = header()
    out.append(fill("", ARENA_W, art.BG_WHITE))
    out += [
        fill(l, ARENA_W, art.BG_WHITE)
        for l in side_by_side(devin, cursor, gap=4)
    ]
    out.append(fill(" " * pointer_col + art.color("👆", art.ORANGE), ARENA_W, art.BG_WHITE))
    out.append(fill("", ARENA_W, art.BG_WHITE))
    for line in art.WIIMOTE:
        out.append(fill("   " + art.color(line, art.INK), ARENA_W, art.BG_WHITE))
    out.append(fill("", ARENA_W, art.BG_WHITE))
    return out


def hull_cell(ship, row: int, col: int, state: str, team_glyph: str, accent: str) -> str:
    """One three-column slice of a grey hull, so cells join into a whole ship."""
    idx = ship.cells.index((row, col))
    last = len(ship.cells) - 1
    horizontal = ship.cells[0][0] == ship.cells[-1][0]
    parts = art.HULL_H if horizontal else art.HULL_V
    segment = parts["bow" if idx == 0 else "stern" if idx == last else "mid"]
    steel = art.STEEL_DEAD if state == "sunk" else art.STEEL

    left, middle, right = segment
    if state == "hit":
        middle = art.color("✸", art.RED + art.BOLD)
    elif state == "sunk":
        middle = art.color("#", art.STEEL_DEAD)
    elif idx == last // 2 and 0 < idx < last:
        middle = art.color(team_glyph, accent)  # team logo painted amidships
    else:
        middle = art.color(middle, steel)
    return art.color(left, steel) + middle + art.color(right, steel)


def cell_block(board: Board, row: int, col: int, reveal: bool, team_glyph: str, accent: str) -> str:
    """The full CELL-wide contents of one square."""
    mark = board.grid[row][col]
    ship = board.ship_at(row, col)
    if ship is not None and (reveal or ship.sunk or mark == Board.HIT):
        state = "sunk" if mark == Board.SUNK else "hit" if mark == Board.HIT else "ok"
        return hull_cell(ship, row, col, state, team_glyph, accent)
    if mark == Board.MISS:
        return " " + art.color("o", art.WII_BLUE) + " "
    return " " + art.color(art.WATER, art.NAVY) + " "


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
    header_row = "   " + "".join(f"{n:^{CELL}}" for n in range(1, SIZE + 1))
    rows = [tint(art.color(header_row, art.INK), art.BG_SEA)]
    for r in range(SIZE):
        cells = []
        for c in range(SIZE):
            shot = overlay.get((r, c))
            if shot:
                lead = (CELL - 1) // 2
                cells.append(" " * lead + shot + " " * (CELL - 1 - lead))
            else:
                cells.append(cell_block(board, r, c, reveal, team_glyph, accent))
        rows.append(tint(art.color(f" {LETTERS[r]} ", art.INK) + "".join(cells), art.BG_SEA))
    return panel(rows, title=title, accent=accent, width=BOARD_W)


def side_by_side(left: list[str], right: list[str], gap: int = 4) -> list[str]:
    width = max((visible_len(l) for l in left), default=0)
    height = max(len(left), len(right))
    left = left + [""] * (height - len(left))
    right = right + [""] * (height - len(right))
    return [l + " " * (width - visible_len(l) + gap) + r for l, r in zip(left, right)]


def meter(value: int, total: int, code: str, width: int = 10) -> str:
    filled = 0 if total <= 0 else round(width * value / total)
    return art.color("▰" * filled, code) + art.color("▱" * (width - filled), art.SILVER)


def scoreboard(stats: dict) -> list[str]:
    """Wii Sports style: two Miis, one big score, soft meters underneath."""
    a = art
    lead = stats["devin_sunk"] - stats["cursor_sunk"]
    mood = "win" if lead > 0 else "lose" if lead < 0 else ""
    flip = {"win": "lose", "lose": "win", "": ""}[mood]
    devin = [a.color(l, a.ORANGE) for l in a.mii(a.MII_DEVIN, mood)]
    cursor = [a.color(l, a.INK) for l in a.mii(a.MII_CURSOR, flip)]
    score = f"{stats['devin_sunk']}  -  {stats['cursor_sunk']}"
    fleet = 5

    mid = ARENA_W - 4 - 2 * 9 - 4
    middle = [
        a.color(pad("H O M E                A W A Y", mid), a.SOFT),
        a.color(pad(score, mid), a.WII_BLUE + a.BOLD),
        a.color(pad(f"ROUND {stats['turn']}", mid), a.SOFT),
    ]
    top = [
        f"{devin[i]}  {middle[i] if i < len(middle) else pad('', mid)}  {cursor[i]}"
        for i in range(4)
    ]
    names = (
        a.color(pad("🦦 DEVIN", 9), a.ORANGE + a.BOLD)
        + "  "
        + pad("", mid)
        + "  "
        + a.color(pad("CURSOR ◆", 9), a.INK + a.BOLD)
    )

    def stat_row(label: str, dv: int, cv: int, code: str, total: int) -> str:
        row = (
            a.color(f"{dv:>3} ", code)
            + meter(dv, total, code)
            + a.color(pad(label, 18), a.SOFT)
            + meter(cv, total, code)
            + a.color(f" {cv:<3}", code)
        )
        return " " * max(0, (ARENA_W - 4 - visible_len(row)) // 2) + row

    shots = max(1, stats["devin_hits"] + stats["devin_misses"], stats["cursor_hits"] + stats["cursor_misses"])
    body = top + [names, ""] + [
        stat_row("HITS", stats["devin_hits"], stats["cursor_hits"], a.RED, shots),
        stat_row("MISSES", stats["devin_misses"], stats["cursor_misses"], a.WII_BLUE, shots),
        stat_row("SHIPS SUNK", stats["devin_sunk"], stats["cursor_sunk"], a.YELLOW, fleet),
        stat_row("FLEET LEFT", stats["devin_alive"], stats["cursor_alive"], a.GREEN, fleet),
    ]
    return panel(body, title="SCOREBOARD", accent=art.WII_BLUE, width=ARENA_W - 4)


def fleet_status(board: Board, label: str, accent: str) -> list[str]:
    lines = []
    for ship in board.ships:
        if ship.sunk:
            bar = art.color("▰" * ship.size, art.STEEL_DEAD) + art.color("  SUNK", art.DARK)
        else:
            bar = "".join(
                art.color("✸", art.RED) if cell in ship.hits else art.color("▰", art.STEEL)
                for cell in ship.cells
            )
        lines.append(art.color(f"{ship.name:<11}", art.INK) + " " + bar)
    return panel(lines, title=f"{label} FLEET", accent=accent, width=BOARD_W)


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
        body = scoreboard(self.stats)
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
            accent=art.INK,
            overlay=overlay_ai,
        )
        body += side_by_side(left, right)
        body += side_by_side(
            fleet_status(self.player_board, "DEVIN", art.ORANGE),
            fleet_status(self.ai_board, "CURSOR", art.INK),
        )
        if extra:
            body += extra
        out = header() + [fill(line, ARENA_W, art.BG_WHITE) for line in body]
        out += footer("▰ ship   ✸ hit   o miss   # sunk")
        if message:
            out.append("")
            out.append(message)
        sys.stdout.write("\n".join(out) + "\n")
        sys.stdout.flush()
