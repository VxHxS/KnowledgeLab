"""Lightweight static HTTP server with SPA fallback for local project serving."""
from __future__ import annotations

import http.server
import os
import sys
import subprocess
import threading
from pathlib import Path


class SPAHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that falls back to index.html for unknown routes (SPA support)."""

    def do_GET(self) -> None:
        path = self.translate_path(self.path)
        if not os.path.exists(path) and not os.path.isfile(path):
            basename = os.path.basename(self.path)
            if "." not in basename:
                index = os.path.join(self.directory, "index.html")
                if os.path.isfile(index):
                    self.path = "/index.html"
        return super().do_GET()

    def log_message(self, format: str, *args: object) -> None:
        pass


def find_static_entry(directory: Path) -> Path | None:
    """Find the directory containing index.html, searching artifact then workspace."""
    for name in ("index.html", "index.htm"):
        if (directory / name).exists():
            return directory
    for subdir in ("dist", "build", "out", ".next"):
        candidate = directory / subdir
        if candidate.is_dir() and any((candidate / n).exists() for n in ("index.html", "index.htm")):
            return candidate
    return None


def serve_static_directory(directory: Path, port: int, bind: str = "127.0.0.1") -> subprocess.Popen | None:
    """Start a static file server with SPA fallback. Returns Popen or None on error."""
    entry = find_static_directory(directory)
    if entry is None:
        return None
    code = f"""
import http.server, os, sys

class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        p = self.translate_path(self.path)
        if not os.path.exists(p) and not os.path.isfile(p):
            b = os.path.basename(self.path)
            if '.' not in b:
                idx = os.path.join(self.directory, 'index.html')
                if os.path.isfile(idx):
                    self.path = '/index.html'
        return super().do_GET()
    def log_message(self, *a):
        pass

os.chdir(r'{entry.as_posix()}')
s = http.server.HTTPServer(('{bind}', {port}), H)
print(f'Serving on http://{bind}:{port}/')
s.serve_forever()
"""
    return subprocess.Popen(
        [sys.executable, "-c", code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def find_static_directory(directory: Path) -> Path | None:
    """Find the best directory to serve: artifact with index.html, or workspace root with index.html."""
    for name in ("index.html", "index.htm"):
        if (directory / name).exists():
            return directory
    for subdir in ("dist", "build", "out", ".next"):
        candidate = directory / subdir
        if candidate.is_dir() and any((candidate / n).exists() for n in ("index.html", "index.htm")):
            return candidate
    return None


def has_static_entry(path: Path) -> bool:
    """Check if a directory has an index.html entry."""
    return any((path / name).exists() for name in ("index.html", "index.htm"))
