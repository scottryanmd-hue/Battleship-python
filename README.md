# ⬢ Battleship: Devin vs Cursor 🦦

A terminal Battleship game where **HOME = Devin** (cognition-logo missiles, otter finishers) plays
**AWAY = Cursor** (a random-firing AI). Ships, shots and sinkings are animated right on the 10×10
grid, and a Wii-style scoreboard tracks hits, misses and ships sunk.

The whole UI is dressed as a Nintendo Wii console: a blue channel bar with a clock, glossy white
rounded panels, a Wii Menu channel-select intro with a hand pointer and Wiimote, Mii-style team
portraits, Wii Sports meters and a Wii Menu button tray along the bottom. Ships are drawn as solid
grey hulls spanning their squares — Cursor's stay hidden until you hit them.

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
- The scoreboard shows the Devin and Cursor Miis, HOME vs AWAY, the sunk-ship score, the round
  number, and meters for hits, misses, ships sunk and remaining fleet.

```
 🦦  B A T T L E S H I P   C H A N N E L    ⬢ vs ◆                 Wed  21:23
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
| `◀███▶` / `▐▲▌` | a grey hull sitting across the squares it occupies, bow to stern |
| `⬢` / `◆` | the team logo painted amidships (Devin on your fleet, Cursor on theirs) |
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
  __main__.py CLI entry point
```
