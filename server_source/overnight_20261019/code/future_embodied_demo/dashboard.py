from __future__ import annotations

import io
import json
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

from PIL import Image

from .engine import DemoEngine
from .language import UnsupportedInstruction


STATIC_ROOT = Path(__file__).with_name("static")


class DashboardServer:
    def __init__(
        self,
        engine: DemoEngine,
        host: str = "127.0.0.1",
        port: int = 8765,
    ) -> None:
        self.engine = engine
        self.host = host
        self.port = port
        self._frame_lock = threading.RLock()
        self._jpeg_frame: Optional[bytes] = None
        self._render_event = threading.Event()
        self._render_stop = threading.Event()
        self.engine.simulator.frame_callback = self.request_frame
        self._render_thread = threading.Thread(
            target=self._render_loop, name="mujoco-render", daemon=True
        )
        self._render_thread.start()
        self.request_frame()
        deadline = time.monotonic() + 4.0
        while self._jpeg_frame is None and time.monotonic() < deadline:
            time.sleep(0.02)
        handler = self._handler_class()
        self.httpd = ThreadingHTTPServer((host, port), handler)

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def update_frame(self, rgb_frame) -> None:
        output = io.BytesIO()
        Image.fromarray(rgb_frame).save(output, format="JPEG", quality=86, optimize=True)
        with self._frame_lock:
            self._jpeg_frame = output.getvalue()

    def request_frame(self, _frame=None) -> None:
        self._render_event.set()

    def _render_loop(self) -> None:
        try:
            while not self._render_stop.is_set():
                self._render_event.wait(timeout=0.15)
                self._render_event.clear()
                try:
                    self.update_frame(self.engine.simulator.render())
                except Exception:
                    if self._render_stop.is_set():
                        return
        finally:
            self.engine.simulator.close_renderer()

    def serve_forever(self) -> None:
        self.httpd.serve_forever(poll_interval=0.2)

    def shutdown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self._render_stop.set()
        self._render_event.set()
        self._render_thread.join(timeout=3.0)

    def _handler_class(self):
        dashboard = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "FutureEmbodiedDemo/1.0"

            def do_GET(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                if path == "/":
                    return self._file(STATIC_ROOT / "index.html", "text/html; charset=utf-8")
                if path == "/api/state":
                    return self._json(HTTPStatus.OK, dashboard.engine.state())
                if path == "/api/health":
                    return self._json(
                        HTTPStatus.OK,
                        {"ok": True, "backend": "offline_deterministic", "external_api": False},
                    )
                if path == "/api/frame.jpg":
                    with dashboard._frame_lock:
                        payload = dashboard._jpeg_frame
                    if payload is None:
                        dashboard.update_frame(dashboard.engine.simulator.render())
                        with dashboard._frame_lock:
                            payload = dashboard._jpeg_frame
                    return self._bytes(HTTPStatus.OK, payload or b"", "image/jpeg")
                return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

            def do_POST(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                try:
                    body = self._request_json()
                    if path == "/api/task":
                        instruction = str(body.get("instruction", ""))
                        goal = dashboard.engine.start(instruction, background=True)
                        return self._json(HTTPStatus.ACCEPTED, {"ok": True, "goal": goal})
                    if path == "/api/event":
                        result = dashboard.engine.inject_event(
                            str(body.get("event", "")),
                            target=body.get("target"),
                        )
                        return self._json(HTTPStatus.OK, {"ok": True, "result": result})
                    if path == "/api/reset":
                        state = dashboard.engine.reset()
                        dashboard.request_frame()
                        return self._json(HTTPStatus.OK, {"ok": True, "world": state})
                    if path == "/api/stop":
                        dashboard.engine.stop()
                        return self._json(HTTPStatus.OK, {"ok": True})
                    return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                except UnsupportedInstruction as exc:
                    return self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                except (ValueError, RuntimeError) as exc:
                    return self._json(HTTPStatus.CONFLICT, {"error": str(exc)})
                except Exception as exc:
                    return self._json(
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        {"error": f"{type(exc).__name__}: {exc}"},
                    )

            def log_message(self, fmt: str, *args) -> None:
                # Keep the terminal focused on task-level events.
                return

            def _request_json(self) -> Dict[str, object]:
                length = int(self.headers.get("Content-Length", "0"))
                payload = self.rfile.read(length) if length else b"{}"
                value = json.loads(payload.decode("utf-8"))
                if not isinstance(value, dict):
                    raise ValueError("JSON body must be an object")
                return value

            def _json(self, status: HTTPStatus, value: object) -> None:
                payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
                self._bytes(status, payload, "application/json; charset=utf-8")

            def _file(self, path: Path, content_type: str) -> None:
                if not path.is_file():
                    return self._json(HTTPStatus.NOT_FOUND, {"error": "static file missing"})
                self._bytes(HTTPStatus.OK, path.read_bytes(), content_type)

            def _bytes(self, status: HTTPStatus, payload: bytes, content_type: str) -> None:
                self.send_response(int(status))
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload)

        return Handler
