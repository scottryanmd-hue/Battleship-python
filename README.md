# ◉ Battleship: Devin vs Cursor 🦦

A terminal Battleship game where **HOME = Devin** (cognition-logo missiles, otter finishers) plays
**AWAY = Cursor** (a random-firing AI). Ships, shots and sinkings are animated right on the 10×10
grid, and a Wii-style scoreboard tracks hits, misses and ships sunk.

The whole UI is dressed as a Nintendo Wii console: a blue channel bar with a clock, glossy white
rounded panels, a Wii Menu channel-select intro with a hand pointer and Wiimote, Mii-style team
portraits, Wii Sports meters and a Wii Menu button tray along the bottom. Ships are drawn in a 3/4
view — two rows per square, a raked bow, deckhouse and funnel above the waterline and a grey steel
hull below — spanning the squares they occupy. Cursor's stay hidden until you hit them.

## Play it

No install at all: **[play it in your browser](https://scottryanmd-hue.github.io/Battleship-python/)**
(enable GitHub Pages on this repo once — Settings → Pages → Source: GitHub Actions).

Or clone it:

```bash
git clone https://github.com/scottryanmd-hue/Battleship-python.git
cd Battleship-python
open index.html                 # the web build: no server, no Python
python3 -m battleship --web     # the same board served locally
python3 -m battleship           # or the terminal version
```

Python 3.10+, no dependencies to install.

### The web build

`index.html` at the root is the whole game. Opened from a static host — GitHub Pages, or the file
itself — there is no Python behind it, so the rules run in the page: `battleship/static/engine.js`
is the port of `board.py` and `session.py`, placing both fleets, firing Cursor's shots, and
answering Fusion, SWE-2 and Outsourced IT. `python3 -m battleship --web` serves that same page and
answers those calls from Python instead, so both modes play the same game.

The one difference: the Security Swarm's heat map is the placement-density estimate offline, not
the Monte Carlo posterior the Python engine computes — the page labels which one it is showing.

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

### Devin Security Swarm

A toggle under the mic, and a Devin-team-only weapon: Cursor's AI fires blind, but you can light up
its waters with a probability heat map — green where a hull most likely hides, orange for
probable, red for unlikely — recomputed from scratch after every single shot, with the odds
printed on each square.

Those odds are a real posterior, not a score. `battleship/probability.py` asks: *given every miss,
every open hit and every wreck on the board, in what fraction of the fleet layouts still possible
does a hull sit on this square?* The prior is the game's own placement process — ships laid down in
fleet order, each uniformly at random among the spots the earlier ones left free — and layouts are
drawn by Monte Carlo. Plain rejection sampling collapses as soon as a couple of hits are on the
board (almost no random layout happens to cover them), so draws come from a proposal that
deliberately steers ships onto hits nothing has explained yet and are then reweighted by the
prior/proposal likelihood ratio — sequential importance sampling, unbiased for the true posterior.
The estimator reports its own effective sample size, ESS = (Σw)² / Σw²; below a floor of 40 it
stops pretending, says so in the banner, and falls back to the classic occurrence-matrix density
map (every legal placement of every surviving ship, hit-covering placements weighted 25×).

Against boards small enough to enumerate exactly, the sampler lands within ~1% of the true
probabilities — there is a test that checks it. It reads only public information, never the
defender's ship list, so it is an edge, not X-ray vision. Press the button again to stand the
swarm down.

### Devin Fusion

Under the swarm button, and also Devin-only: arm **Devin Fusion** and your next order — spoken or
clicked — goes up as a two-missile salvo instead of one shot. The named square is hit first, then
the nearest open square beside it; anything already shelled is skipped and the second shot spills
outward (corners, then the next ring) so both missiles always hit live water. Cursor still answers
once. Fusion disarms itself after the salvo, so the shot after it is an ordinary single one.

### SWE-2

One press and Devin walks a full salvo down columns 1, 4 and 6 — every square in them that has not
been shelled yet, top to bottom, thirty missiles on an empty board. Long salvos fly on a short fuse
so the sweep does not take a minute to watch. Cursor answers once at the end.

### Outsourced IT (AI Labor)

Cursor's largest hull still afloat surfaces on their side of the board and is struck square by
square until it goes down. Press it again and the next largest surfaces, and so on until Cursor has
nothing left.

### The fleets

Devin's ships are clean grey steel. Cursor's are on a maintenance budget that ran out: rust
streaking down the plating, a mismatched plate welded over the bow, a tarpaulin where a deckhouse
window should be, a funnel knocked out of true still coughing smoke, and a permanent list to port.
Every Cursor hull wears the Cursor cube amidships, and each square Devin lands a direct hit on is
stamped with that cube in red on the hull itself.

### Winning the match

When the last Cursor hull goes down, the otter surfaces with a clam shell branded with the Cursor
mark, taps it three times, cracks it open — the two halves and the logo spin away and fade — and
then dances under the fireworks to the fanfare.

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
index.html    the web build's page: the board, served or opened straight from disk
battleship/
  board.py    grid, ship placement, firing rules, 3-missile detonation
  render.py   Wii panels/channel bar, board drawing, scoreboard, side-by-side layout
  effects.py  missile flight + smoke, explosions, otter finisher
  game.py     placement UI, turn loop, AI, endgame
  session.py  headless game state machine (same rules, no I/O) for the browser
  probability.py  Devin Security Swarm: Bayesian posterior (+ density fallback) over the enemy grid
  web.py      stdlib HTTP server: static files + /api/state, /api/fire, /api/fusion, /api/swe2,
              /api/outsource, /api/new, /api/reroll
  static/     browser front-end: Wii board in CSS 3D, missiles, mic button, and
              engine.js — the rules in JavaScript, for when there is no server
  __main__.py CLI entry point
```
