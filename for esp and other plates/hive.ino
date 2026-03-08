/*
 * hive.ino — Симулятор улья (ESP8266 Wemos Lolin D1 Light)
 *
 * Поведение:
 *   1. Подключается к Wi-Fi и WebSocket-серверу.
 *   2. Отслеживает:
 *        - nectar  — общий запас нектара
 *        - honey   — произведённый мёд
 *        - beesInside — сколько пчёл сейчас в улье
 *   3. Периодически конвертирует нектар в мёд (симуляция).
 *   4. Отправляет статус:
 *        {"type":"hive","id":0,"nectar":...,"honey":...,"bees_inside":...}
 *   5. Может принимать от сервера обновления (приход/уход пчёл, доставка нектара).
 *
 * Библиотеки:
 *   - WebSockets  by Markus Sattler
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

// ─── Идентификатор улья ──────────────────────────────────────────────────────
const int HIVE_ID = 0;

// ─── Интервалы (мс) ──────────────────────────────────────────────────────────
const unsigned long STATUS_INTERVAL   = 5000;
const unsigned long CONVERT_INTERVAL  = 10000;  // конвертация нектара → мёд

// ─── Параметры симуляции ─────────────────────────────────────────────────────
const float CONVERT_RATIO  = 0.3;   // 30% нектара → мёд за тик
const int   INITIAL_BEES   = 3;     // начальное кол-во пчёл

// ─── Глобальные переменные ───────────────────────────────────────────────────
WebSocketsClient webSocket;

float nectar     = 0.0;
float honey      = 0.0;
int   beesInside = INITIAL_BEES;

unsigned long lastStatusMs   = 0;
unsigned long lastConvertMs  = 0;

// ─── Отправка статуса ────────────────────────────────────────────────────────
void sendStatus() {
  StaticJsonDocument<160> doc;
  doc["type"]        = "hive";
  doc["id"]          = HIVE_ID;
  doc["nectar"]      = nectar;
  doc["honey"]       = honey;
  doc["bees_inside"] = beesInside;

  char buf[160];
  serializeJson(doc, buf, sizeof(buf));
  webSocket.sendTXT(buf);
  Serial.printf("[TX] %s\n", buf);
}

// ─── Обработка входящих сообщений ────────────────────────────────────────────
void handleMessage(uint8_t* payload, size_t length) {
  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) {
    Serial.printf("[ERR] JSON parse: %s\n", err.c_str());
    return;
  }

  // Сервер может присылать обновления:
  //   {"action":"bee_arrived","nectar_delivered":1.5}
  //   {"action":"bee_departed"}
  const char* action = doc["action"] | "";
  Serial.printf("[RX] action=%s\n", action);

  if (strcmp(action, "bee_arrived") == 0) {
    float delivered = doc["nectar_delivered"] | 0.0f;
    nectar += delivered;
    beesInside++;
    Serial.printf("  → Пчела прибыла, доставлено %.1f нектара. В улье: %d\n",
                  delivered, beesInside);

  } else if (strcmp(action, "bee_departed") == 0) {
    if (beesInside > 0) beesInside--;
    Serial.printf("  → Пчела вылетела. В улье: %d\n", beesInside);
  }
}

// ─── Callback WebSocket ──────────────────────────────────────────────────────
void webSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED:
      Serial.println("[WS] Подключено к серверу");
      sendStatus();
      break;

    case WStype_DISCONNECTED:
      Serial.println("[WS] Отключено");
      break;

    case WStype_TEXT:
      handleMessage(payload, length);
      break;

    default:
      break;
  }
}

// ─── Конвертация нектара в мёд ───────────────────────────────────────────────
void convertNectarToHoney() {
  unsigned long now = millis();
  if (now - lastConvertMs < CONVERT_INTERVAL) return;
  lastConvertMs = now;

  if (nectar > 0.1) {
    float portion = nectar * CONVERT_RATIO;
    nectar -= portion;
    honey  += portion;
    Serial.printf("  🍯 Конвертация: -%.2f нектара → +%.2f мёда (всего мёда: %.2f)\n",
                  portion, portion, honey);
  }
}

// ─── setup / loop ────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.printf("\n=== HIVE #%d ===\n", HIVE_ID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf(" OK  IP=%s\n", WiFi.localIP().toString().c_str());

  webSocket.begin(SERVER_IP, SERVER_PORT, "/");
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(3000);
}

void loop() {
  webSocket.loop();
  convertNectarToHoney();

  unsigned long now = millis();
  if (now - lastStatusMs >= STATUS_INTERVAL) {
    lastStatusMs = now;
    sendStatus();
  }
}
