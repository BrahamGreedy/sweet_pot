# Пчелиный рой — система обмена сообщениями

Система из Python WebSocket-сервера и трёх Arduino-скетчей (ESP8266) для симуляции пчелиного роя.

## Архитектура

```
┌─────────────┐     WebSocket      ┌──────────────┐
│  bee.ino     │◄──────────────────►│              │
│  (ESP8266)   │                    │              │
├─────────────┤     WebSocket      │  server.py   │
│  flower.ino  │◄──────────────────►│  (Python)    │
│  (ESP8266)   │                    │              │
├─────────────┤     WebSocket      │              │
│  hive.ino    │◄──────────────────►│              │
│  (ESP8266)   │                    └──────────────┘
└─────────────┘
```

## 1. Запуск сервера

### Требования
- Python 3.9+
- Библиотека `websockets`

### Установка и запуск

```bash
pip install websockets
python server.py          # порт 8080 по умолчанию
python server.py 9090     # или указать свой порт
```

Сервер выведет в консоль:
```
🐝 Swarm-сервер запускается на ws://0.0.0.0:8080
```

Запомните **IP-адрес компьютера** в локальной сети (например, `192.168.1.100`) — он понадобится для скетчей.

## 2. Прошивка ESP8266

### Требования
- Arduino IDE 1.8+ или 2.x
- Плата **ESP8266** добавлена в Board Manager (URL: `http://arduino.esp8266.com/stable/package_esp8266com_index.json`)
- Установленные библиотеки через Library Manager:
  - **WebSockets** by Markus Sattler (версия ≥ 2.4.0)
  - **ArduinoJson** by Benoît Blanchon (версия ≥ 6.0)

### Настройка Board Manager
1. `File → Preferences → Additional Board Manager URLs` → вставить URL выше
2. `Tools → Board → Boards Manager` → найти **esp8266** → Install
3. `Tools → Board` → выбрать **LOLIN(WEMOS) D1 mini Lite**

### Прошивка каждого скетча

**Перед прошивкой** отредактируйте в каждом `.ino` файле:

```cpp
const char* WIFI_SSID     = "YOUR_SSID";       // ← имя вашей Wi-Fi сети
const char* WIFI_PASSWORD = "YOUR_PASSWORD";    // ← пароль
const char* SERVER_IP     = "192.168.1.100";    // ← IP сервера
const uint16_t SERVER_PORT = 8080;              // ← порт сервера
```

Для пчёл и цветков также задайте уникальный ID:
```cpp
const int BEE_ID    = 1;   // 1, 2, 3... для разных пчёл
const int FLOWER_ID = 1;   // 1, 2, 3... для разных цветков
```

**Порядок прошивки:**

1. Откройте `bee/bee.ino` в Arduino IDE
2. `Tools → Board` → LOLIN(WEMOS) D1 mini Lite
3. `Tools → Port` → выберите COM-порт платы
4. Нажмите **Upload** (→)
5. Откройте Serial Monitor (115200 baud) для отладки

Повторите для `flower/flower.ino` и `hive/hive.ino` на соответствующих платах.

## 3. Протокол сообщений

### Устройство → Сервер (статусы)

| Устройство | Формат |
|-----------|--------|
| Пчела | `{"type":"bee", "id":1, "nectar":1.5}` |
| Цветок | `{"type":"flower", "id":1, "nectar":5.0, "state":"blooming"}` |
| Улей | `{"type":"hive", "id":0, "nectar":3.0, "honey":1.2, "bees_inside":3}` |

### Сервер → Устройству (команды)

| Цель | Формат |
|------|--------|
| Пчела | `{"type":"bee", "id":1, "command":"go_to_flower", "time":"...", "flower_id":1}` |
| Цветок | `{"type":"flower", "id":1, "state":"blooming", "time":"..."}` |
| Улей | `{"action":"bee_arrived", "nectar_delivered":1.5}` |

### Команды для пчелы
- `go_to_flower` — лететь к цветку (указать `flower_id`)
- `collect` — начать сбор нектара
- `return_to_hive` — вернуться в улей

### Состояния цветка
- `blooming` — цветёт, нектар растёт
- `wilted` — увял, нектар не копится
- `pollinated` — опылён, нектар списывается

## 4. Отладка

- Serial Monitor (115200) на каждой плате показывает все события
- Сервер логирует все входящие (`←`) и исходящие (`→`) сообщения в консоль
- Устройства автоматически переподключаются при потере связи (каждые 3 сек)
