/*
 * bee.ino — Робот-пчела (ESP8266 Wemos Lolin D1 Light)
 *
 * Управление моторами:
 *   D5, D6 — движение прямо/назад (левый и правый мотор)
 *   D7, D8 — поворот (левый и правый мотор поворота)
 *
 * Команды от сервера (JSON, поле "command"):
 *   "forward"         → едет прямо      (D5 HIGH, D6 HIGH)
 *   "backward"        → едет назад      (D5 HIGH, D6 HIGH — реверс на драйвере)
 *   "turn_left"       → поворот влево   (D7 HIGH, D8 LOW)
 *   "turn_right"      → поворот вправо  (D7 LOW,  D8 HIGH)
 *   "stop"            → стоп            (все LOW)
 *   "go_to_flower"    → [ЗАГЛУШКА]
 *   "collect"         → [ЗАГЛУШКА]
 *   "return_to_hive"  → [ЗАГЛУШКА]
 *   "dance"           → [ЗАГЛУШКА]
 *   "sleep"           → [ЗАГЛУШКА]
 *
 * Библиотеки:
 *   - WebSockets  by Markus Sattler  (>= 2.4.0)
 *   - ArduinoJson by Benoît Blanchon (>= 6.x)
 */

#include <ESP8266WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

// ─── Настройки Wi-Fi ─────────────────────────────────────────────────────────
const char* WIFI_SSID     = "YOUR_SSID";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";

// ─── Настройки сервера ───────────────────────────────────────────────────────
const char* SERVER_IP      = "192.168.1.100";
const uint16_t SERVER_PORT = 8080;

// ─── Идентификатор этой пчелы ────────────────────────────────────────────────
const int BEE_ID = 1;

// ─── Пины моторов ────────────────────────────────────────────────────────────
//  Прямой/обратный ход:  D5 (GPIO14) — левый,  D6 (GPIO12) — правый
//  Поворот:              D7 (GPIO13) — влево,   D8 (GPIO15) — вправо
const uint8_t PIN_DRIVE_LEFT  = D5;
const uint8_t PIN_DRIVE_RIGHT = D6;
const uint8_t PIN_TURN_LEFT   = D7;
const uint8_t PIN_TURN_RIGHT  = D8;

// ─── Интервалы (мс) ──────────────────────────────────────────────────────────
const unsigned long STATUS_INTERVAL = 5000;

// ─── Глобальные переменные ───────────────────────────────────────────────────
WebSocketsClient webSocket;

float nectar       = 0.0;
int   targetFlower = 0;

unsigned long lastStatusMs = 0;

// ═════════════════════════════════════════════════════════════════════════════
//  РЕАЛЬНОЕ УПРАВЛЕНИЕ МОТОРАМИ
// ═════════════════════════════════════════════════════════════════════════════

void motorsStop() {
  digitalWrite(PIN_DRIVE_LEFT,  LOW);
  digitalWrite(PIN_DRIVE_RIGHT, LOW);
  digitalWrite(PIN_TURN_LEFT,   LOW);
  digitalWrite(PIN_TURN_RIGHT,  LOW);
  Serial.println("[MOT] STOP — все пины LOW");
}

void motorsForward() {
  // Сначала гасим поворот, потом включаем прямой ход
  digitalWrite(PIN_TURN_LEFT,   LOW);
  digitalWrite(PIN_TURN_RIGHT,  LOW);
  digitalWrite(PIN_DRIVE_LEFT,  HIGH);
  digitalWrite(PIN_DRIVE_RIGHT, HIGH);
  Serial.println("[MOT] FORWARD — D5=HIGH D6=HIGH");
}

void motorsBackward() {
  // Реверс: зависит от драйвера (L298N — отдельный пин DIR,
  // L9110 — инверсия на входах). Здесь упрощённо — те же пины.
  // При необходимости добавьте пины направления.
  digitalWrite(PIN_TURN_LEFT,   LOW);
  digitalWrite(PIN_TURN_RIGHT,  LOW);
  digitalWrite(PIN_DRIVE_LEFT,  HIGH);
  digitalWrite(PIN_DRIVE_RIGHT, HIGH);
  Serial.println("[MOT] BACKWARD — D5=HIGH D6=HIGH (реверс на драйвере)");
}

void motorsTurnLeft() {
  // Останавливаем прямой ход, включаем поворот влево
  digitalWrite(PIN_DRIVE_LEFT,  LOW);
  digitalWrite(PIN_DRIVE_RIGHT, LOW);
  digitalWrite(PIN_TURN_LEFT,   HIGH);
  digitalWrite(PIN_TURN_RIGHT,  LOW);
  Serial.println("[MOT] TURN LEFT — D7=HIGH D8=LOW");
}

void motorsTurnRight() {
  // Останавливаем прямой ход, включаем поворот вправо
  digitalWrite(PIN_DRIVE_LEFT,  LOW);
  digitalWrite(PIN_DRIVE_RIGHT, LOW);
  digitalWrite(PIN_TURN_LEFT,   LOW);
  digitalWrite(PIN_TURN_RIGHT,  HIGH);
  Serial.println("[MOT] TURN RIGHT — D7=LOW D8=HIGH");
}

// ═════════════════════════════════════════════════════════════════════════════
//  ЗАГЛУШКИ (TODO: реализовать)
// ═════════════════════════════════════════════════════════════════════════════

void stubGoToFlower(int flowerId) {
  // TODO: навигация к цветку (компас, ИК-датчики, алгоритм пути)
  Serial.printf("[STUB] go_to_flower → flower_id=%d  (не реализовано)\n", flowerId);
}

void stubCollect() {
  // TODO: активация механизма сбора нектара (сервопривод, насос и т.д.)
  Serial.println("[STUB] collect → сбор нектара (не реализовано)");
}

void stubReturnToHive() {
  // TODO: навигация обратно к улью
  Serial.println("[STUB] return_to_hive → возврат в улей (не реализовано)");
}

void stubDance() {
  // TODO: «танец пчелы» — серия движений для коммуникации с другими роботами
  Serial.println("[STUB] dance → танец пчелы (не реализовано)");
}

void stubSleep() {
  // TODO: режим энергосбережения (WiFi.forceSleepBegin() и т.п.)
  Serial.println("[STUB] sleep → режим сна (не реализовано)");
}

// ─── Отправка статуса на сервер ──────────────────────────────────────────────
void sendStatus() {
  StaticJsonDocument<128> doc;
  doc["type"]   = "bee";
  doc["id"]     = BEE_ID;
  doc["nectar"] = nectar;

  char buf[128];
  serializeJson(doc, buf, sizeof(buf));
  webSocket.sendTXT(buf);
  Serial.printf("[TX] %s\n", buf);
}

// ─── Обработка входящей команды ──────────────────────────────────────────────
void handleCommand(uint8_t* payload, size_t length) {
  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) {
    Serial.printf("[ERR] JSON parse: %s\n", err.c_str());
    return;
  }

  const char* command = doc["command"] | "";
  Serial.printf("[RX] command=\"%s\"\n", command);

  // ── Реальное управление моторами ──
  if (strcmp(command, "forward") == 0) {
    motorsForward();

  } else if (strcmp(command, "backward") == 0) {
    motorsBackward();

  } else if (strcmp(command, "turn_left") == 0) {
    motorsTurnLeft();

  } else if (strcmp(command, "turn_right") == 0) {
    motorsTurnRight();

  } else if (strcmp(command, "stop") == 0) {
    motorsStop();

  // ── Заглушки ──
  } else if (strcmp(command, "go_to_flower") == 0) {
    targetFlower = doc["flower_id"] | 0;
    stubGoToFlower(targetFlower);

  } else if (strcmp(command, "collect") == 0) {
    stubCollect();

  } else if (strcmp(command, "return_to_hive") == 0) {
    stubReturnToHive();

  } else if (strcmp(command, "dance") == 0) {
    stubDance();

  } else if (strcmp(command, "sleep") == 0) {
    stubSleep();

  } else {
    Serial.printf("[WARN] Неизвестная команда: \"%s\"\n", command);
  }
}

// ─── Callback WebSocket-событий ──────────────────────────────────────────────
void webSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED:
      Serial.println("[WS] Подключено к серверу");
      sendStatus();
      break;

    case WStype_DISCONNECTED:
      Serial.println("[WS] Отключено от сервера");
      motorsStop();   // безопасность: стоп при потере связи
      break;

    case WStype_TEXT:
      handleCommand(payload, length);
      break;

    case WStype_PING:
    case WStype_PONG:
      break;

    default:
      break;
  }
}

// ─── setup ───────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.printf("\n=== BEE #%d ===\n", BEE_ID);

  // Инициализация пинов моторов
  pinMode(PIN_DRIVE_LEc:\Users\Asus\Documents\GitHub\sweet_pot\for esp and other plates\bee.ino c:\Users\Asus\Documents\GitHub\sweet_pot\for esp and other plates\flower.ino c:\Users\Asus\Documents\GitHub\sweet_pot\for esp and other plates\hive.inoFT,  OUTPUT);
  pinMode(PIN_DRIVE_RIGHT, OUTPUT);
  pinMode(PIN_TURN_LEFT,   OUTPUT);
  pinMode(PIN_TURN_RIGHT,  OUTPUT);
  motorsStop();  // гарантируем стоп при старте

  // Подключение к Wi-Fi
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf(" OK  IP=%s\n", WiFi.localIP().toString().c_str());

  // Подключение к WebSocket-серверу
  webSocket.begin(SERVER_IP, SERVER_PORT, "/");
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(3000);
}

// ─── loop ────────────────────────────────────────────────────────────────────
void loop() {
  webSocket.loop();

  // Периодическая отправка статуса
  unsigned long now = millis();
  if (now - lastStatusMs >= STATUS_INTERVAL) {
    lastStatusMs = now;
    sendStatus();
  }
}
