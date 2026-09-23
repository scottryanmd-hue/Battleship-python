"""ASCII / emoji art for the Devin vs Cursor battleship arena."""

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

ORANGE = "\033[38;5;208m"
WHITE = "\033[97m"
GREY = "\033[38;5;245m"
DARK = "\033[38;5;240m"
RED = "\033[38;5;196m"
YELLOW = "\033[38;5;226m"
BLUE = "\033[38;5;39m"
NAVY = "\033[38;5;26m"
GREEN = "\033[38;5;46m"
BLACK_ON_AMBER = "\033[48;5;236m\033[38;5;208m"

COGNITION_GLYPH = "⬢"
CURSOR_GLYPH = "◆"
SMOKE = ["·", "∘", "°", "˙"]

COGNITION_LOGO = [
    "  ⬢⬡   ⬡⬢  ",
    "   ⬢⬡⬢⬡⬢   ",
    "  ⬢⬡   ⬡⬢  ",
]

CURSOR_LOGO = [
    "   ◢◣   ",
    "  ◢██◣  ",
    " ◢████◣ ",
    "◢██████◣",
]

OTTER_SMALL = "🦦"

OTTER_BIG = [
    "            .-\"\"\"-.            ",
    "          .'  _ _  '.          ",
    "         /   (o) (o)  \\        ",
    "        |      .-.     |       ",
    "     \\  |     (   )    |  /    ",
    "   ---  \\   '-.___.-'  /  ---  ",
    "     /   '._       _.'    \\    ",
    "          /`--...--`\\          ",
    "         /  .-----.  \\         ",
    "        |  | ⬢ ⬡ ⬢ |  |        ",
    "        |  | ⬡ ⬢ ⬡ |  |        ",
    "         \\ '-------' /         ",
    "          '._______.'          ",
    "            //   \\\\            ",
    "           (_)   (_)           ",
    "      D E V I N   O T T E R    ",
]

EXPLOSION_FRAMES = [
    [
        "      .  *  .      ",
        "   *   \\ | /   *   ",
        "  . --   ⬢   -- .  ",
        "   *   / | \\   *   ",
        "      .  *  .      ",
    ],
    [
        "    \\  .  |  .  /    ",
        "  *  \\ ,--´--, /  *  ",
        " -- ( B O O M ) --  ",
        "  *  / `--,--` \\  *  ",
        "    /  '  |  '  \\    ",
    ],
    [
        "   💥 💥 💥 💥 💥   ",
        " 💥  ✦   ✦   ✦  💥 ",
        "💥  ✦  B O O M ✦ 💥",
        " 💥  ✦   ✦   ✦  💥 ",
        "   💥 💥 💥 💥 💥   ",
    ],
]

WATER = "~"


def color(text: str, code: str) -> str:
    return f"{code}{text}{RESET}"


def banner() -> str:
    lines = [
        "╔══════════════════════════════════════════════════════════════╗",
        "║   ⬢  B A T T L E S H I P :  D E V I N   v s   C U R S O R  ◆  ║",
        "╚══════════════════════════════════════════════════════════════╝",
    ]
    return "\n".join(color(line, ORANGE + BOLD) for line in lines)


def ship_broadside(name: str, label: str, glyph: str, accent: str) -> list[str]:
    """A tiny side view of a ship with the team logo painted on its hull."""
    hull = f"[{glyph} {label} {glyph}]"
    return [
        color("        |        ", accent),
        color("     ___|___     ", accent),
        color(f"  __/{hull:^11}\\__  ", accent),
        color("  \\_______________/  ", accent),
        color(f"   {name:^17}", DIM),
    ]
