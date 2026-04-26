from __future__ import annotations

import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lab_mvp.orchestrator import ExperimentOrchestrator
from lab_mvp.storage import JsonStore


store = JsonStore(ROOT / "data")
orchestrator = ExperimentOrchestrator(store, ROOT / "sample_data")


class MVPHandler(BaseHTTPRequestHandler):
    server_version = "LabMVP/0.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/state":
                self._json(orchestrator.state())
                return
            if path.startswith("/reports/"):
                self._serve_report(path)
                return
            if path == "/":
                self._serve_file(ROOT / "static" / "index.html")
                return
            if path.startswith("/static/"):
                self._serve_file(ROOT / unquote(path.lstrip("/")))
                return
            self._not_found()
        except Exception as exc:
            self._error(exc)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._payload()
            if path == "/api/projects":
                self._json(orchestrator.create_project(payload.get("name", "Untitled"), payload.get("description", "")))
                return
            if path == "/api/datasets/import":
                self._json(orchestrator.import_dataset(payload["project_id"], payload["filename"], payload["content"]))
                return
            if path == "/api/runs":
                self._json(orchestrator.create_run(
                    payload["project_id"],
                    payload["dataset_id"],
                    payload.get("parameters", {}),
                    payload.get("label", ""),
                ))
                return
            if path == "/api/recommendations":
                self._json(orchestrator.recommend(payload["project_id"]))
                return
            if path == "/api/reports":
                self._json(orchestrator.generate_report(payload["project_id"]))
                return
            if path == "/api/demo/load":
                self._json(orchestrator.load_demo())
                return
            self._not_found()
        except Exception as exc:
            self._error(exc)

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def _payload(self) -> dict:
        length = int(self.headers.get("content-length", "0"))
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def _json(self, payload: dict | list, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path) -> None:
        resolved = path.resolve()
        if ROOT not in resolved.parents and resolved != ROOT:
            self._not_found()
            return
        if not resolved.exists() or not resolved.is_file():
            self._not_found()
            return
        body = resolved.read_bytes()
        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        if resolved.suffix in {".html", ".css", ".js"}:
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_report(self, path: str) -> None:
        report_name = Path(unquote(path)).name
        self._serve_file(store.report_dir / report_name)

    def _not_found(self) -> None:
        self._json({"error": "Not found"}, 404)

    def _error(self, exc: Exception) -> None:
        self._json({"error": str(exc), "type": exc.__class__.__name__}, 500)


def main() -> None:
    port = 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), MVPHandler)
    print(f"Lab MVP server running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

