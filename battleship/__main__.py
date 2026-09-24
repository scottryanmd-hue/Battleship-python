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
    parser.add_argument(
        "--web",
        action="store_true",
        help="Play in the browser instead, with a microphone button for spoken targets.",
    )
    parser.add_argument("--port", type=int, default=8000, help="Port for --web (default 8000).")
    parser.add_argument("--no-browser", action="store_true", help="With --web, don't open a browser.")
    args = parser.parse_args()

    if args.web:
        from .web import serve

        serve(port=args.port, open_browser=not args.no_browser, seed=args.seed)
        return

    try:
        Game(speed=args.speed, seed=args.seed).run()
    except KeyboardInterrupt:
        print("\n  Ceasefire. Bye.")


if __name__ == "__main__":
    main()
