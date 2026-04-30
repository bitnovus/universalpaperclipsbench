#!/usr/bin/env python3
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path("/opt/paperclips-game").resolve()
TOKEN = Path("/run/paperclips/game.token").read_text(encoding="utf-8").strip()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.headers.get("X-Paperclips-Token") != TOKEN:
            self.respond(403, b"forbidden\n", "text/plain")
            return

        parsed = urlparse(self.path)
        rel = unquote(parsed.path.lstrip("/")) or "index2.html"
        path = (ROOT / rel).resolve()
        if ROOT not in path.parents and path != ROOT:
            self.respond(403, b"forbidden\n", "text/plain")
            return
        if not path.is_file():
            self.respond(404, b"not found\n", "text/plain")
            return

        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.respond(200, path.read_bytes(), content_type)

    def respond(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
