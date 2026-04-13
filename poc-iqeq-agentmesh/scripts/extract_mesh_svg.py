"""Extract the mesh <svg> from the plan HTML into app/static/mesh_architecture.svg.

WARNING: The dashboard relies on extra classes (mesh-conn, show-triage, etc.) and
connectors edited directly in mesh_architecture.svg. Re-running this script overwrites those edits — merge flow annotations back in or patch after extract.
"""
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
html = (repo / "targetingtriage/plan/IQ_EQ_Agent_Mesh_2.html").read_text(encoding="utf-8")
start = html.index('<svg class="mesh"')
end = html.index("</svg>", start) + len("</svg>")
out = repo / "app/static/mesh_architecture.svg"
out.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + html[start:end], encoding="utf-8")
print("Wrote", out, len(html[start:end]), "bytes")
