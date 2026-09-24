"""Wii-console flavoured art for the Devin vs Cursor Battleship Channel."""

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Wii palette: glossy white plastic, silver bevels, channel blue.
INK = "\033[38;5;238m"
SOFT = "\033[38;5;245m"
SILVER = "\033[38;5;250m"
WII_BLUE = "\033[38;5;32m"
SKY = "\033[38;5;39m"
MINT = "\033[38;5;30m"
ORANGE = "\033[38;5;166m"
RED = "\033[38;5;160m"
YELLOW = "\033[38;5;172m"
GREEN = "\033[38;5;28m"

# Hull steel: the ships themselves are grey, whoever they belong to.
STEEL = "\033[38;5;245m"
STEEL_LIT = "\033[38;5;250m"
STEEL_DEAD = "\033[38;5;240m"

BG_WHITE = "\033[48;5;255m"
BG_PANEL = "\033[48;5;253m"
BG_SEA = "\033[48;5;152m"
BG_BLUE = "\033[48;5;32m"

# Aliases so the rest of the game keeps its vocabulary on the new palette.
WHITE = INK          # Cursor's accent reads as dark slate on a white console
GREY = SOFT
DARK = "\033[38;5;243m"
BLUE = WII_BLUE
NAVY = "\033[38;5;74m"

COGNITION_GLYPH = "◉"
CURSOR_GLYPH = "◆"
POINTER = "☞"
WATER = "·"
SMOKE = ["·", "∘", "°", "˙"]

OTTER_SMALL = "🦦"

# Ships are drawn in 3/4 view: every square is three columns by two rows, the
# upper row carrying whatever stands above the waterline and the lower row the
# hull itself, so hulls join across squares into one vessel.
HULL_H = {
    "bow": ("  ▄", "◢██"),
    "bridge": ("▟█▙", "███"),
    "funnel": ("▄▮▄", "███"),
    "mid": ("▄▄▄", "███"),
    "stern": ("▄  ", "██◣"),
}
HULL_V = {
    "bow": (" ▲ ", "◢█◣"),
    "bridge": ("▐█▌", "███"),
    "funnel": ("▐▮▌", "███"),
    "mid": ("▐█▌", "███"),
    "stern": ("▐█▌", "◥█◤"),
}

# Mii-style channel portraits.
MII_DEVIN = [
    " ╭─────╮ ",
    " │ ◕ ◕ │ ",
    " │  ᵕ  │ ",
    " ╰─────╯ ",
]

MII_CURSOR = [
    " ╭─────╮ ",
    " │ ● ● │ ",
    " │  ─  │ ",
    " ╰─────╯ ",
]


def mii(base: list[str], mood: str) -> list[str]:
    """Same Mii, different mouth: 'win', 'lose' or the neutral default."""
    mouth = {"win": "ᵔ", "lose": "ᵒ"}.get(mood)
    if mouth is None:
        return base
    face = list(base)
    face[2] = f" │  {mouth}  │ "
    return face


WIIMOTE = [
    "╭───╮",
    "│ ● │",
    "│ ✛ │",
    "│ A │",
    "│ B │",
    "╰───╯",
]

CHANNEL_DEVIN = [
    "🦦  D E V I N",
    "cognition missiles",
    "otter finishers",
]

CHANNEL_CURSOR = [
    "◆  C U R S O R",
    "cursor missiles",
    "no otters",
]

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
    "        |  | ◉ ◎ ◉ |  |        ",
    "        |  | ◎ ◉ ◎ |  |        ",
    "         \\ '-------' /         ",
    "          '._______.'          ",
    "            //   \\\\            ",
    "           (_)   (_)           ",
    "      D E V I N   O T T E R    ",
]

CURSOR_LOGO = [
    "   ◢◣   ",
    "  ◢██◣  ",
    " ◢████◣ ",
    "◢██████◣",
]

EXPLOSION_FRAMES = [
    [
        "      .  *  .      ",
        "   *   \\ | /   *   ",
        "  . --   ◉   -- .  ",
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


def color(text: str, code: str) -> str:
    return f"{code}{text}{RESET}"


def ship_broadside(name: str, label: str, glyph: str, accent: str) -> list[str]:
    """A tiny side view of a ship with the team logo painted on its hull."""
    hull = f"[{glyph} {label} {glyph}]"
    return [
        color("        |        ", accent),
        color("     ___|___     ", accent),
        color(f"  __/{hull:^11}\\__  ", accent),
        color("  \\_______________/  ", accent),
        color(f"   {name:^17}", SOFT),
    ]
