import asyncio
import json
import threading
import time
from pathlib import Path

from aiohttp import web, WSMsgType
import cv2


class CameraGrabber:
    def __init__(self, cam_index: int = 0):
        self.cam_index = cam_index
        self._cap = None
        self._lock = threading.Lock()
        self._latest_jpg: bytes | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_ok_ts = 0.0

    def start(self):
        if self._running:
            return

        # Windows: попробуем несколько backend'ов
        for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, 0]:
            cap = cv2.VideoCapture(self.cam_index, backend) if backend != 0 else cv2.VideoCapture(self.cam_index)
            if cap.isOpened():
                self._cap = cap
                break

        if self._cap is None or not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera index {self.cam_index}")

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._cap:
            self._cap.release()

    def _loop(self):
        while self._running:
            ok, frame = self._cap.read()
            if ok and frame is not None:
                ok2, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ok2:
                    with self._lock:
                        self._latest_jpg = buf.tobytes()
                        self._last_ok_ts = time.time()
            time.sleep(0.01)

    def get_latest_jpg(self) -> bytes | None:
        with self._lock:
            return self._latest_jpg

    def last_ok_age(self) -> float:
        with self._lock:
            if self._last_ok_ts == 0:
                return 1e9
            return time.time() - self._last_ok_ts


class AppState:
    def __init__(self):
        self.streaming = True
        self.clients: set[web.WebSocketResponse] = set()

    async def broadcast(self, payload: dict):
        msg = json.dumps(payload, ensure_ascii=False)
        dead = []
        for ws in self.clients:
            try:
                await ws.send_str(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)


# ---------- routes ----------
async def root(request: web.Request) -> web.StreamResponse:
    # Всегда открываем конкретный файл, без листинга папки
    static_dir: Path = request.app["static_dir"]
    return web.FileResponse(static_dir / "index.html")


async def health(request: web.Request) -> web.Response:
    cam: CameraGrabber = request.app["cam"]
    age = cam.last_ok_age()
    return web.json_response({"ok": True, "camera_last_frame_age_s": age})


async def frame_jpg(request: web.Request) -> web.Response:
    cam: CameraGrabber = request.app["cam"]
    jpg = cam.get_latest_jpg()

    if jpg is None:
        for _ in range(50):
            await asyncio.sleep(0.02)
            jpg = cam.get_latest_jpg()
            if jpg is not None:
                break

    if jpg is None:
        return web.Response(status=503, text="No frame yet")

    return web.Response(body=jpg, content_type="image/jpeg")


async def mjpeg(request: web.Request) -> web.StreamResponse:
    cam: CameraGrabber = request.app["cam"]
    state: AppState = request.app["state"]

    boundary = "frame"
    resp = web.StreamResponse(
        status=200,
        headers={
            "Content-Type": f"multipart/x-mixed-replace; boundary={boundary}",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
    await resp.prepare(request)

    try:
        while True:
            if not state.streaming:
                await asyncio.sleep(0.1)
                continue

            jpg = cam.get_latest_jpg()
            if jpg is None:
                await asyncio.sleep(0.02)
                continue

            part = (
                f"--{boundary}\r\n"
                "Content-Type: image/jpeg\r\n"
                f"Content-Length: {len(jpg)}\r\n\r\n"
            ).encode("utf-8") + jpg + b"\r\n"

            await resp.write(part)
            await asyncio.sleep(0.08)  # ~12 fps
    except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
        pass
    finally:
        try:
            await resp.write_eof()
        except Exception:
            pass

    return resp


async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    state: AppState = request.app["state"]

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    state.clients.add(ws)

    await ws.send_str(json.dumps({"type": "state", "streaming": state.streaming}, ensure_ascii=False))

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    await ws.send_str(json.dumps({"type": "error", "msg": "bad json"}))
                    continue

                t = data.get("type")
                if t=="robstate":
                    await state.broadcast({"type": "robstate", "id":"None"})
                if t == "start":
                    state.streaming = True
                    await state.broadcast({"type": "state", "streaming": state.streaming})
                elif t == "stop":
                    state.streaming = False
                    await state.broadcast({"type": "state", "streaming": state.streaming})
                elif t == "coordinates":
                    await state.broadcast({"type": "coordinates", "coordinates": data.get("coordinates")})
                else:
                    await ws.send_str(json.dumps({"type": "error", "msg": f"unknown command: {t}"}))
    finally:
        state.clients.discard(ws)

    return ws


async def on_startup(app: web.Application):
    app["cam"].start()


async def on_cleanup(app: web.Application):
    app["cam"].stop()


def main():
    base_dir = Path(__file__).resolve().parent
    static_dir = base_dir / "static"

    app = web.Application()
    app["cam"] = CameraGrabber(cam_index=0)
    app["state"] = AppState()
    app["static_dir"] = static_dir

    # API
    app.add_routes([
        web.get("/", root),
        web.get("/health", health),
        web.get("/frame.jpg", frame_jpg),
        web.get("/mjpeg", mjpeg),
        web.get("/ws", ws_handler),
    ])

    # Статика ТОЛЬКО в /static, без листинга
    app.router.add_static("/static/", path=static_dir, show_index=False)

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    web.run_app(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()