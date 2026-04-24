# Lightweight HTTP server — serves frontend/index.html at GET / and live state at GET /api/state.
# Started automatically by main.py; not usually run standalone.
#
# Terminal 1 (deploy topology):
#   cd ~/Desktop/Network_Defender_FYP/containerlab-networks
#   sudo containerlab deploy -t cage4-topology.yaml
#
# Terminal 2 (run standalone):
#   cd ~/Desktop/Network_Defender_FYP/bridge
#   sudo ~/fyp-venv-linux/bin/python server.py
#
# Cleanup (when done):
#   sudo containerlab destroy -t cage4-topology.yaml

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

BRIDGE_DIR   = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BRIDGE_DIR, "..", "frontend"))
STATE_FILE   = os.path.join(BRIDGE_DIR, "state.json")


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._serve(os.path.join(FRONTEND_DIR, "index.html"), "text/html; charset=utf-8")
        elif self.path == "/api/state":
            self._serve(STATE_FILE, "application/json")
        else:
            self.send_response(404)
            self.end_headers()

    def _serve(self, path, content_type):
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *_):
        pass  # silence per-request access log noise


def start(port=8080):
    httpd = HTTPServer(("0.0.0.0", port), _Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    print(f"[server] Dashboard → http://localhost:{port}")
