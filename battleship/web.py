"""Browser front-end: a stdlib HTTP server around `session.Session`.

`python3 -m battleship --web` serves the Wii-style board at http://127.0.0.1:8000
with a microphone button, so shots can be spoken ("fire at D five") instead of
typed. The rules live in `board.py` exactly as they do for the terminal game;
this module only moves JSON.
"""

from __future__ import annotations

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .board import parse_coord
from .session import Session

#: The page is the repository's root index.html — the same file a static host
#: serves — and it addresses its script and artwork under battleship/static/.
ROOT = Path(__file__).parent.parent
CONTENT_TYPES = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".png": "image/png",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "BattleshipChannel/1.0"
    session: Session
    seed: int | None = None

    def log_message(self, fmt: str, *args) -> None:  # quieter console
        pass

    # -- plumbing ----------------------------------------------------------
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: dict, status: int = 200) -> None:
        self._send(status, json.dumps(payload).encode(), "application/json")

    def _static(self, name: str) -> None:
        path = (ROOT / name).resolve()
        if not path.is_file() or ROOT.resolve() not in path.parents:
            self._send(404, b"not found", "text/plain")
            return
        self._send(200, path.read_bytes(), CONTENT_TYPES.get(path.suffix, "text/plain"))

    # -- routes ------------------------------------------------------------
    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._static("index.html")
        elif self.path == "/api/state":
            self._json(type(self).session.state())
        else:
            self._static(self.path.lstrip("/"))

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json({"error": "bad request"}, 400)
            return
        cls = type(self)

        if self.path == "/api/new":
            cls.session = Session(cls.seed)
            self._json(cls.session.state())
        elif self.path == "/api/reroll":
            try:
                cls.session.reroll_home_fleet()
            except ValueError as exc:
                self._json({"error": str(exc)}, 409)
                return
            self._json(cls.session.state())
        elif self.path == "/api/fire":
            self._fire(payload)
        elif self.path == "/api/fusion":
            self._fire(payload, fusion=True)
        elif self.path == "/api/swe2":
            self._salvo(cls.session.swe2)
        elif self.path == "/api/outsource":
            self._salvo(cls.session.outsource)
        else:
            self._json({"error": "no such endpoint"}, 404)

    def _salvo(self, action) -> None:
        """Run a Devin-only special that needs no coordinate."""
        try:
            events = action()
        except ValueError as exc:
            self._json({"error": str(exc)}, 409)
            return
        self._json({"events": events, "state": type(self).session.state()})

    def _fire(self, payload: dict, fusion: bool = False) -> None:
        try:
            if "coord" in payload:
                row, col = parse_coord(str(payload["coord"]))
            else:
                row, col = int(payload["row"]), int(payload["col"])
        except (KeyError, TypeError, ValueError) as exc:
            self._json({"error": str(exc) or "Use a coordinate like B7."}, 400)
            return
        session = type(self).session
        try:
            events = session.fusion(row, col) if fusion else session.fire(row, col)
        except ValueError as exc:
            self._json({"error": str(exc)}, 409)
            return
        self._json({"events": events, "state": type(self).session.state()})


def serve(port: int = 8000, open_browser: bool = True, seed: int | None = None) -> None:
    Handler.seed = seed
    Handler.session = Session(seed)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"  🦦  Battleship Channel is live at {url}  (Ctrl-C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Ceasefire. Bye.")
    finally:
        server.server_close()
