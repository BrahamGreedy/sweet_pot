# Быстрый старт: настройка и запуск

## Шаг 1. Узнать IP сервера

Сервер и все ESP8266 должны быть **в одной Wi-Fi сети**.

**Windows** — открыть терминал (cmd) и выполнить:
```
ipconfig
```
Найти строку `IPv4 Address` у вашего Wi-Fi адаптера, например `192.168.1.100`.

**macOS / Linux**:
```
ip a          # Linux
ifconfig      # macOS
```
Найти адрес вида `192.168.x.x` у интерфейса `wlan0` / `en0`.

---

## Шаг 2. Вписать настройки в скетчи

В **каждом** из трёх `.ino` файлов (`bee.ino`, `flower.ino`, `hive.ino`) отредактировать блок констант в начале файла:

```cpp
const char* WIFI_SSID     = "MoyaSetka";       // имя Wi-Fi
const char* WIFI_PASSWORD = "parol12345";       // пароль Wi-Fi
const char* SERVER_IP     = "192.168.1.100";    // IP из шага 1
const uint16_t SERVER_PORT = 8080;              // порт (по умолчанию 8080)
```

Для пчёл и цветков — задать уникальный номер каждой плате:
```cpp
const int BEE_ID    = 1;   // 1, 2, 3… у каждой пчелы свой
const int FLOWER_ID = 1;   // 1, 2, 3… у каждого цветка свой
```

---

## Шаг 3. Подготовить Arduino IDE

1. **Добавить ESP8266 в Board Manager:**
   `File → Preferences → Additional Board Manager URLs` → вставить:
   ```
   http://arduino.esp8266.com/stable/package_esp8266com_index.json
   ```
   Затем `Tools → Board → Boards Manager` → найти **esp8266** → Install.

2. **Установить библиотеки** через `Sketch → Include Library → Manage Libraries`:
   - **WebSockets** by Markus Sattler (≥ 2.4.0)
   - **ArduinoJson** by Benoît Blanchon (≥ 6.0)

3. **Выбрать плату:**
   `Tools → Board` → **LOLIN(WEMOS) D1 mini Lite**

---

## Шаг 4. Запустить сервер

```bash
pip install websockets
python server.py
```

В консоли появится:
```
🐝 Swarm-сервер запускается на ws://0.0.0.0:8080
```

Сервер запущен и ждёт подключений. Не закрывайте терминал.

---

## Шаг 5. Прошить платы

1. Подключить ESP8266 по USB.
2. Открыть нужный скетч (например `bee/bee.ino`).
3. `Tools → Port` → выбрать появившийся COM-порт.
4. Нажать **Upload** (→).
5. После прошивки открыть `Tools → Serial Monitor` (115200 baud).

Если всё верно, в мониторе появится:
```
=== BEE #1 ===
Wi-Fi... OK  IP=192.168.1.42
[WS] Подключено к серверу
[TX] {"type":"bee","id":1,"nectar":0}
```

Повторить для каждой платы со своим скетчем и ID.

---

## Частые проблемы

| Симптом | Решение |
|---------|---------|
| `Wi-Fi......` висит бесконечно | Проверить SSID и пароль, плата должна быть в зоне роутера |
| `[WS] Отключено от сервера` | Проверить SERVER_IP и порт, убедиться что `server.py` запущен |
| Порт не виден в Arduino IDE | Установить драйвер CH340 (Wemos использует этот чип) |
| Сервер не видит устройства | Компьютер и ESP8266 должны быть в **одной** Wi-Fi сети |
