# ◉ Battleship: Devin vs Cursor 🦦

A terminal Battleship game where **HOME = Devin** (cognition-logo missiles, otter finishers) plays
**AWAY = Cursor** (a random-firing AI). Ships, shots and sinkings are animated right on the 10×10
grid, and a Wii-style scoreboard tracks hits, misses and ships sunk.

The whole UI is dressed as a Nintendo Wii console: a blue channel bar with a clock, glossy white
rounded panels, a Wii Menu channel-select intro with a hand pointer and Wiimote, Mii-style team
portraits, Wii Sports meters and a Wii Menu button tray along the bottom. Ships are drawn in a 3/4
view — two rows per square, a raked bow, deckhouse and funnel above the waterline and a grey steel
hull below — spanning the squares they occupy. Cursor's stay hidden until you hit them.

## Run it

Requires Python 3.10+ and a UTF-8 terminal. No dependencies.

```bash
python3 -m battleship
# or
python3 main.py
```

Options:

```bash
python3 -m battleship --speed 0.5   # animations at half the pause length (0 = instant)
python3 -m battleship --seed 42     # reproducible ship placement and AI shots
```

## Browser mode, with voice targeting

The same rules also run behind a tiny local web server, so you can call your shots out loud
instead of typing them:

```bash
python3 -m battleship --web            # serves http://127.0.0.1:8000 and opens a browser
python3 -m battleship --web --port 9000 --no-browser --seed 42
```

The page is the Wii look in HTML/CSS: both fleets in 3/4 perspective as grey steel hulls, missiles
with smoke trails, explosions and the otter finisher. Every square Devin shells is stamped with the
cognition logo — bold red on a hit, faded blue on a miss, charcoal once the hull goes down. Click a
square on Cursor's waters to fire,
or press **Speak your shot** and say the target:

- "Fire at D 5"
- "Launch sonar on G 8"
- "D5"

Voice uses the browser-native `webkitSpeechRecognition` API, so it needs Chrome (or another
WebKit/Blink browser) and microphone permission — the button explains itself and disables where the
API is missing, and clicking squares always works. Nothing fires unless you order it: a heard
phrase only launches a missile when it carries a firing verb ("fire", "launch", "target", "hit"…)
or is nothing but the coordinate, so overheard conversation never shells a square. The transcript
that triggered each shot is echoed under the mic. The server binds to `127.0.0.1` only and keeps
one game in memory; `( A ) New game` starts another.

### Victory music

Sinking a Cursor ship sets off fireworks, the otter and a short 80s-montage fanfare synthesised in
the browser with the Web Audio API. To celebrate with your own track instead — a training-montage
anthem, say — drop an audio file at `battleship/static/sounds/victory.mp3` (`.ogg`, `.wav` and
`.m4a` work too) and the page plays that instead. Nothing copyrighted ships with the repo; supply
your own licensed copy.

## How to play

1. Choose `r` to have your five ships (Carrier 5, Battleship 4, Cruiser 3, Submarine 3,
   Destroyer 2) placed randomly, or `m` to place each one yourself by bow coordinate plus
   `h`/`v` orientation.
2. On your turn, enter a target on Cursor's grid like `F5` (row `A`–`J`, column `1`–`10`).
   Type `q` to resign.
3. Cursor fires back at a random square you haven't already been shelled on.
4. First fleet fully sunk loses.

## The flair

- Every Devin shot launches a `◉` **cognition missile** off the deck of your ship; it flies across
  the target grid leaving a fading smoke trail (`˙ ° ∘ ·`) before it lands.
- Cursor fires `◆` missiles the same way, from the opposite edge, at your Devin ships.
- A miss buries itself in the water at that square (`o`); a hit burns as `✸`.
- **Three cognition missiles detonate a hull.** The ship explodes, and then the Devin otter 🦦
  flies in to deliver the final blow and sink the Cursor ship. (Two-cell Destroyers go down on
  their second hit.)
- The scoreboard shows the Devin and Cursor Miis, HOME vs AWAY, the sunk-ship score, the round
  number, and meters for hits, misses, ships sunk and remaining fleet.

```
 🦦  B A T T L E S H I P   C H A N N E L    ◉ vs ◆                 Wed  21:23
╭─ SCOREBOARD ───────────────────────────────────────────────────────────────╮
│  ╭─────╮              H O M E                A W A Y              ╭─────╮  │
│  │ ◕ ◕ │                         3  -  1                          │ ● ● │  │
│  │  ᵕ  │                         ROUND 9                          │  ─  │  │
│  ╰─────╯                                                          ╰─────╯  │
│ 🦦 DEVIN                                                         CURSOR ◆  │
│                                                                            │
│                11 ▰▰▰▰▰▰▱▱▱▱       HITS       ▰▰▱▱▱▱▱▱▱▱ 4                 │
│                 7 ▰▰▰▰▱▱▱▱▱▱      MISSES      ▰▰▰▱▱▱▱▱▱▱ 5                 │
│                 3 ▰▰▰▰▰▰▱▱▱▱    SHIPS SUNK    ▰▰▱▱▱▱▱▱▱▱ 1                 │
│                 4 ▰▰▰▰▰▰▰▰▱▱    FLEET LEFT    ▰▰▰▰▱▱▱▱▱▱ 2                 │
╰────────────────────────────────────────────────────────────────────────────╯
 ( Wii )  ( Mii )  ( A ) ☞ ▰ ship   ✸ hit   o miss   # sunk
```

## Board legend

| Symbol | Meaning |
| --- | --- |
| `·` | unexplored water |
| `◢██▄▟█▙███◣` | a grey vessel in 3/4 view, raked bow through superstructure to stern |
| `◉` / `◆` | the team logo painted amidships (Devin on your fleet, Cursor on theirs) |
| `o` | miss |
| `✸` | hit |
| `#` | sunk hull |

## Layout

```
battleship/
  board.py    grid, ship placement, firing rules, 3-missile detonation
  render.py   Wii panels/channel bar, board drawing, scoreboard, side-by-side layout
  effects.py  missile flight + smoke, explosions, otter finisher
  game.py     placement UI, turn loop, AI, endgame
  session.py  headless game state machine (same rules, no I/O) for the browser
  web.py      stdlib HTTP server: static files + /api/state, /api/fire, /api/new, /api/reroll
  static/     browser front-end: Wii board in CSS 3D, missiles, mic button
  __main__.py CLI entry point
```
