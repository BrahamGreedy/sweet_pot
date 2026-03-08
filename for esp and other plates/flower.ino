/*
 * flower.ino — Симулятор цветка (ESP8266 Wemos Lolin D1 Light)
 *
 * Поведение:
 *   1. Подключается к Wi-Fi и WebSocket-серверу.
 *   2. Периодически отправляет статус:
 *        {"type":"flower","id":...,"nectar":...,"state":"..."}
 *   3. Принимает команды от сервера:
 *        {"state":"blooming"}   → цветок расцветает, нектар растёт
 *        {"state":"wilted"}     → цветок увял, нектар не копится
 *        {"state":"pollinated"} → опылён пчелой, нектар списывается
 *   4. Нектар медленно накапливается, пока цветок в состоянии blooming.
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

// ─── Идентификатор цветка ────────────────────────────────────────────────────
const int FLOWER_ID = 1;

// ─── Интервалы (мс) ──────────────────────────────────────────────────────────
const unsigned long STATUS_INTERVAL   = 5000;  // отправка статуса
const unsigned long NECTAR_GROW_INTERVAL = 6000;  // прирост нектара

// ─── Параметры симуляции ─────────────────────────────────────────────────────
const float NECTAR_MAX       = 10.0;
const float NECTAR_PER_TICK  = 0.5;   // прирост за один тик
const float NECTAR_COLLECTED = 1.5;   // сколько списывает пчела за визит

// ─── Глобальные переменные ───────────────────────────────────────────────────
WebSocketsClient webSocket;

String  flowerState   = "blooming";  // blooming | wilted | pollinated
float   nectar        = 5.0;         // начальный запас

unsigned long lastStatusMs  = 0;
unsigned long lastGrowMs    = 0;

// ─── Отправка статуса ────────────────────────────────────────────────────────
void sendStatus() {
  StaticJsonDocument<160> doc;
  doc["type"]   = "flower";
  doc["id"]     = FLOWER_ID;
  doc["nectar"] = nectar;
  doc["state"]  = flowerState;

  char buf[160];
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

  const char* newState = doc["state"] | "";
  Serial.printf("[RX] state=%s\n", newState);

  if (strlen(newState) > 0) {
    flowerState = String(newState);
    Serial.printf("  → Новое состояние: %s\n", flowerState.c_str());

    // Если цветок «опылён» — списываем нектар
    if (flowerState == "pollinated") {
      nectar = max(0.0f, nectar - NECTAR_COLLECTED);
      Serial.printf("  → Нектар после опыления: %.1f\n", nectar);
      // Возвращаемся в blooming через некоторое время (упрощённо — сразу)
      flowerState = "blooming";
    }
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
      handleCommand(payload, length);
      break;

    default:
      break;
  }
}

// ─── Рост нектара ────────────────────────────────────────────────────────────
void updateNectar() {
  unsigned long now = millis();
  if (now - lastGrowMs < NECTAR_GROW_INTERVAL) return;
  lastGrowMs = now;

  if (flowerState == "blooming" && nectar < NECTAR_MAX) {
    nectar = min(NECTAR_MAX, nectar + NECTAR_PER_TICK);
    Serial.printf("  🌻 Нектар вырос до %.1f\n", nectar);
  }
}

// ─── setup / loop ────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.printf("\n=== FLOWER #%d ===\n", FLOWER_ID);

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
  updateNectar();

  unsigned long now = millis();
  if (now - lastStatusMs >= STATUS_INTERVAL) {
    lastStatusMs = now;
    sendStatus();
  }
}
