#!/usr/bin/env python3
"""
server.py — Асинхронный WebSocket-сервер для симуляции пчелиного роя.

Протокол:
  Устройство → Сервер:  {"type": "bee"|"flower"|"hive", ...payload}
  Сервер → Устройству:  {"type": "bee"|"flower", ...payload}

Запуск:
  python server.py          # слушает 0.0.0.0:8080
  python server.py 9090     # слушает 0.0.0.0:9090
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Optional

import websockets
from websockets.server import WebSocketServerProtocol

# ─── Настройки ────────────────────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = 8080

# ─── Логирование ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("swarm-server")


# ─── Реестр устройств ─────────────────────────────────────────────────────────
class DeviceRegistry:
    """Хранит mapping  (device_type, device_id) → websocket."""

    def __init__(self):
        # ключ: ("bee", 1) / ("flower", 5) / ("hive", 0)
        # значение: WebSocketServerProtocol
        self._devices: dict[tuple[str, int], WebSocketServerProtocol] = {}

    def register(self, dtype: str, did: int, ws: WebSocketServerProtocol):
        key = (dtype, did)
        self._devices[key] = ws
        log.info("✚ Зарегистрировано: %s id=%d  addr=%s", dtype, did, ws.remote_address)

    def unregister(self, ws: WebSocketServerProtocol):
        to_del = [k for k, v in self._devices.items() if v is ws]
        for k in to_del:
            del self._devices[k]
            log.info("✖ Отключено: %s id=%d", k[0], k[1])

    def get(self, dtype: str, did: int) -> Optional[WebSocketServerProtocol]:
        return self._devices.get((dtype, did))

    def summary(self) -> str:
        bees    = [did for (dt, did) in self._devices if dt == "bee"]
        flowers = [did for (dt, did) in self._devices if dt == "flower"]
        hives   = [did for (dt, did) in self._devices if dt == "hive"]
        return f"bees={bees} flowers={flowers} hives={hives}"


registry = DeviceRegistry()


# ─── Вспомогательные функции ──────────────────────────────────────────────────
def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


async def send_to_device(dtype: str, did: int, payload: dict):
    """Отправить JSON-команду конкретному устройству по типу и ID."""
    ws = registry.get(dtype, did)
    if ws is None:
        log.warning("⚠ Устройство %s id=%d не найдено в реестре", dtype, did)
        return
    msg = json.dumps(payload, ensure_ascii=False)
    try:
        await ws.send(msg)
        log.info("→ [%s id=%d] %s", dtype, did, msg)
    except websockets.ConnectionClosed:
        log.warning("⚠ Соединение с %s id=%d закрыто при отправке", dtype, did)
        registry.unregister(ws)


# ─── Команды сервера (API для внешней логики) ─────────────────────────────────
async def command_bee(bee_id: int, command: str, flower_id: int = 0):
    """Отправить команду пчеле."""
    payload = {
        "type": "bee",
        "id": bee_id,
        "command": command,
        "time": now_iso(),
        "flower_id": flower_id,
    }
    await send_to_device("bee", bee_id, payload)


async def command_flower(flower_id: int, state: str):
    """Отправить команду цветку."""
    payload = {
        "type": "flower",
        "id": flower_id,
        "state": state,
        "time": now_iso(),
    }
    await send_to_device("flower", flower_id, payload)


# ─── Обработка входящих сообщений ─────────────────────────────────────────────
async def handle_message(ws: WebSocketServerProtocol, raw: str):
    """Разбирает входящий JSON и регистрирует устройство / логирует статус."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.error("✗ Невалидный JSON от %s: %s", ws.remote_address, raw[:120])
        return

    dtype = data.get("type")  # "bee" | "flower" | "hive"
    did   = data.get("id", 0)

    if dtype not in ("bee", "flower", "hive"):
        log.warning("✗ Неизвестный тип устройства: %s", dtype)
        return

    # Авторегистрация при первом сообщении
    if registry.get(dtype, did) is None:
        registry.register(dtype, did, ws)

    log.info("← [%s id=%d] %s", dtype, did, raw[:200])

    # ── Здесь можно добавить игровую логику ──
    # Пример: при получении статуса пчелы — отправить ей команду лететь к цветку
    # if dtype == "bee":
    #     await command_bee(did, "go_to_flower", flower_id=1)


# ─── Обработчик WebSocket-подключений ─────────────────────────────────────────
async def handler(ws: WebSocketServerProtocol):
    addr = ws.remote_address
    log.info("⇌ Новое подключение: %s", addr)
    try:
        async for message in ws:
            await handle_message(ws, message)
    except websockets.ConnectionClosed as e:
        log.info("⇌ Соединение закрыто: %s (code=%s)", addr, e.code)
    except Exception as e:
        log.error("✗ Ошибка в handler для %s: %s", addr, e)
    finally:
        registry.unregister(ws)
        log.info("Реестр: %s", registry.summary())


# ─── Демо-задача: периодическая отправка команд ──────────────────────────────
async def demo_commander():
    """Пример фоновой задачи — каждые 15 секунд командует пчеле id=1."""
    await asyncio.sleep(10)  # ждём, пока устройства подключатся
    while True:
        await command_bee(bee_id=1, command="go_to_flower", flower_id=1)
        await command_flower(flower_id=1, state="blooming")
        await asyncio.sleep(15)


# ─── Точка входа ──────────────────────────────────────────────────────────────
async def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    log.info("🐝 Swarm-сервер запускается на ws://%s:%d", HOST, port)

    async with websockets.serve(
        handler,
        HOST,
        port,
        ping_interval=20,
        ping_timeout=10,
    ):
        # Запускаем демо-задачу параллельно с сервером
        asyncio.create_task(demo_commander())
        await asyncio.Future()  # работаем бесконечно


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Сервер остановлен (Ctrl+C)")
