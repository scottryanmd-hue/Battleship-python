"""Entry point: python3 -m battleship"""

from __future__ import annotations

import argparse

from .game import Game


def main() -> None:
    parser = argparse.ArgumentParser(description="Battleship: Devin (home) vs Cursor (away).")
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Animation speed multiplier for pauses (0 disables all animation delays).",
    )
    parser.add_argument("--seed", type=int, default=None, help="Seed the RNG for reproducible games.")
    args = parser.parse_args()

    try:
        Game(speed=args.speed, seed=args.seed).run()
    except KeyboardInterrupt:
        print("\n  Ceasefire. Bye.")


if __name__ == "__main__":
    main()
