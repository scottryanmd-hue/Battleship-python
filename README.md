# ⬢ Battleship: Devin vs Cursor 🦦

A terminal Battleship game where **HOME = Devin** (cognition-logo missiles, otter finishers) plays
**AWAY = Cursor** (a random-firing AI). Ships, shots and sinkings are animated right on the 10×10
grid, and a high-school-gym scoreboard tracks hits, misses and ships sunk.

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

## How to play

1. Choose `r` to have your five ships (Carrier 5, Battleship 4, Cruiser 3, Submarine 3,
   Destroyer 2) placed randomly, or `m` to place each one yourself by bow coordinate plus
   `h`/`v` orientation.
2. On your turn, enter a target on Cursor's grid like `F5` (row `A`–`J`, column `1`–`10`).
   Type `q` to resign.
3. Cursor fires back at a random square you haven't already been shelled on.
4. First fleet fully sunk loses.

## The flair

- Every Devin shot launches a `⬢` **cognition missile** off the deck of your ship; it flies across
  the target grid leaving a fading smoke trail (`˙ ° ∘ ·`) before it lands.
- Cursor fires `◆` missiles the same way, from the opposite edge, at your Devin ships.
- A miss buries itself in the water at that square (`o`); a hit burns as `✸`.
- **Three cognition missiles detonate a hull.** The ship explodes, and then the Devin otter 🦦
  flies in to deliver the final blow and sink the Cursor ship. (Two-cell Destroyers go down on
  their second hit.)
- The scoreboard shows the otter, HOME `DEVIN` vs AWAY `CURSOR`, the sunk-ship score, per-side
  hits/misses and remaining fleet size.

```
╔═══════════════════════════════════════════════════════════════════════╗
║  🦦  D E V I N   F I E L D H O U S E   ·   S C O R E B O A R D  🦦    ║
╠═══════════════════╦═══════════════════════════╦═══════════════════════╣
║       HOME        ║          ⬢ ⬡ ⬢            ║         AWAY          ║
║    🦦 DEVIN 🦦    ║         3  ―  1           ║      ◆ CURSOR ◆       ║
╠═══════════════════╬═══════════════════════════╬═══════════════════════╣
║  HITS       11    ║     INNING (TURN)   9     ║  HITS        4        ║
║  MISSES      7    ║  ⬢ COGNITION MISSILES ⬢   ║  MISSES      5        ║
║  SHIPS SUNK  3    ║     FLEET 4 ⬢  vs  ◆ 2    ║  SHIPS SUNK  1        ║
╚═══════════════════╩═══════════════════════════╩═══════════════════════╝
```

## Board legend

| Symbol | Meaning |
| --- | --- |
| `~` | unexplored water |
| `⬢` | your (Devin) ship |
| `◆` | a Cursor ship (only shown on your own grid legend; enemy ships stay hidden) |
| `o` | miss |
| `✸` | hit |
| `#` | sunk hull |

## Layout

```
battleship/
  board.py    grid, ship placement, firing rules, 3-missile detonation
  render.py   board drawing, scoreboard, side-by-side layout
  effects.py  missile flight + smoke, explosions, otter finisher
  game.py     placement UI, turn loop, AI, endgame
  __main__.py CLI entry point
```
