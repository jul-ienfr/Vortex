"""Simple HTTP server for VORTEX dashboard."""

from __future__ import annotations

import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from vortex.dashboard import get_dashboard_html, get_status

logger = logging.getLogger(__name__)


class VortexHandler(BaseHTTPRequestHandler):
    """HTTP request handler for VORTEX."""

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/" or self.path == "/dashboard":
            self._send_html(get_dashboard_html())
        elif self.path == "/api/status":
            self._send_json(get_status())
        elif self.path == "/api/health":
            self._send_json({"status": "healthy", "version": "0.1.0"})
        elif self.path == "/api/projects":
            self._send_json({"projects": []})
        else:
            self._send_json({"error": f"Not found: {self.path}"}, 404)

    def _send_html(self, html: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        logger.debug(format, *args)


def run_server(host: str = "0.0.0.0", port: int = 8080):
    """Start the VORTEX web server."""
    server = HTTPServer((host, port), VortexHandler)
    logger.info("VORTEX server running on http://%s:%d", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped.")
        server.server_close()
