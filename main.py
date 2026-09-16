"""Run the Linux distro guessing game with: python3 main.py"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from game import state

ROOT = Path(__file__).parent


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/app.css", "/app.js"):
            self.send_error(404)
            return
        file_name, content_type = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/app.css": ("app.css", "text/css; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
        }[self.path]
        body = (ROOT / file_name).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/api/state":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 100_000:
                raise ValueError("Request too large")
            payload = json.loads(self.rfile.read(size))
            result = state(payload.get("answers"))
            code = 200
        except (ValueError, TypeError, AttributeError, json.JSONDecodeError) as exc:
            result, code = {"error": str(exc)}, 400
        body = json.dumps(result).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    print("Distro Oracle is running at http://0.0.0.0:8000", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
