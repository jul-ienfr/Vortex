"""Simple web dashboard for VORTEX."""

from __future__ import annotations

import json
from pathlib import Path

DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head><title>VORTEX Dashboard</title>
<style>
body { font-family: sans-serif; max-width: 800px; margin: 40px auto; }
.metric { padding: 10px; border: 1px solid #ddd; margin: 5px 0; }
.ok { color: green; } .warn { color: orange; } .err { color: red; }
</style>
</head>
<body>
<h1>VORTEX Dashboard</h1>
<div id="status">Loading...</div>
<script>
fetch('/api/status').then(r=>r.json()).then(d=>{
  document.getElementById('status').innerHTML =
    '<div class="metric">Projects: '+d.projects+'</div>' +
    '<div class="metric">Tests: <span class="ok">'+d.tests+' passing</span></div>' +
    '<div class="metric">Version: '+d.version+'</div>';
});
</script>
</body>
</html>"""


def get_dashboard_html() -> str:
    """Return the dashboard HTML."""
    return DASHBOARD_HTML


def get_status() -> dict:
    """Return dashboard status data."""
    return {
        "version": "0.1.0",
        "projects": 0,
        "tests": 92,
        "status": "ok",
    }
