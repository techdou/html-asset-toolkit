#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serve a single-file HTML (or a directory of assets) over local HTTP.

Designed as a lightweight browser-verification helper after packaging. Uses
only the Python standard library — no extra dependencies.

Features:
- Auto-detects the first available port starting from --port.
- Optionally opens the system browser (--open).
- Serves a single HTML file or a directory.
- Prints a clear URL and a Ctrl+C hint.
"""

from __future__ import annotations

import argparse
import http.server
import socket
import socketserver
import sys
import webbrowser
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Suppress default noisy logging, print only errors."""

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        pass

    def log_error(self, fmt: str, *args) -> None:  # noqa: A003
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def find_available_port(host: str, start: int, attempts: int = 50) -> int:
    """Return the first bindable port starting from *start*."""
    for port in range(start, start + attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                return port
        except OSError:
            continue
    raise SystemExit(
        f"ERROR: no available port found in range {start}-{start + attempts - 1} on {host}. "
        "Specify a different --port."
    )


def serve(directory: Path, port: int, host: str, open_browser: bool, url_path: str) -> None:
    handler = lambda *args, **kw: QuietHandler(*args, directory=str(directory), **kw)  # noqa: E731

    # Use a Reusable address so re-running the script doesn't hit TIME_WAIT.
    class ReusableServer(socketserver.TCPServer):
        allow_reuse_address = True

    httpd = ReusableServer((host, port), handler)
    display_host = "localhost" if host in ("127.0.0.1", "0.0.0.0") else host
    lan_host = None
    if host == "0.0.0.0":
        try:
            lan_host = socket.gethostbyname(socket.gethostname())
        except Exception:
            lan_host = None

    url = f"http://{display_host}:{port}/{url_path.lstrip('/')}"
    print(f"Serving:   {directory}")
    print(f"Local URL: {url}")
    if lan_host:
        print(f"Network:   http://{lan_host}:{port}/{url_path.lstrip('/')}")
    print("Press Ctrl+C to stop.\n")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        httpd.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Serve a single-file HTML or a directory over local HTTP for preview."
    )
    parser.add_argument("target", type=Path, help="An HTML file to serve, or a directory to serve from.")
    parser.add_argument("--port", type=int, default=8000, help="Starting port. Auto-increments if occupied.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Use 0.0.0.0 for LAN access.")
    parser.add_argument("--open", action="store_true", help="Open the system browser automatically.")
    parser.add_argument("--no-browser", action="store_true", help="Never open a browser (overrides --open).")
    args = parser.parse_args()

    if not args.target.exists():
        print(f"ERROR: target not found: {args.target}", file=sys.stderr)
        return 1

    open_browser = args.open and not args.no_browser

    if args.target.is_file():
        directory = args.target.parent.resolve()
        url_path = args.target.name
    else:
        directory = args.target.resolve()
        url_path = ""

    port = find_available_port(args.host, args.port)
    if port != args.port:
        print(f"Port {args.port} in use, using {port} instead.")

    serve(directory, port, args.host, open_browser, url_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
