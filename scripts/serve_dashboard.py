"""Serve the dashboard locally so the browser can load data/*.json."""
from __future__ import annotations

import http.server
import os
import webbrowser
from pathlib import Path

DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard"
PORT = int(os.getenv("DASHBOARD_PORT", "8080"))


def main() -> None:
    os.chdir(DASHBOARD_DIR)
    handler = http.server.SimpleHTTPRequestHandler
    with http.server.HTTPServer(("", PORT), handler) as httpd:
        url = f"http://localhost:{PORT}/"
        print(f"Serving dashboard at {url}")
        print("Press Ctrl+C to stop.")
        webbrowser.open(url)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
