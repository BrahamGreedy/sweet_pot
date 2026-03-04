#include <ESP8266WiFi.h>

const char* WIFI_SSID = "Kabinet1";
const char* WIFI_PASS = "kabinet101";

// IP/порт сервера, куда ESP будет подключаться
IPAddress serverIP(192, 168, 100, 2);   // <-- поменяй на IP твоего ПК/сервера в локалке
const uint16_t serverPort = 9000;

WiFiClient client;

unsigned long lastSendMs = 0;

bool connectToServer() {
  if (client.connected()) return true;

  Serial.println("Connecting to server...");
  client.stop(); // на всякий случай сброс старого состояния
  if (!client.connect(serverIP, serverPort)) {
    Serial.println("Server connect failed");
    return false;
  }

  Serial.println("Server connected");
  client.setNoDelay(true); // чтобы меньше буферизовало (полезно для интерактива)
  client.println("HELLO_FROM_ESP");
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(200);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("WiFi connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("WiFi connected, IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // 1) Поддерживаем соединение
  if (!connectToServer()) {
    delay(1000);
    return;
  }

  // 2) Принимаем данные от сервера (построчно)
  while (client.available()) {
    String line = client.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) continue;

    Serial.print("RX: ");
    Serial.println(line);

    // простая логика: отвечаем ACK
    client.print("ACK ");
    client.println(line);
  }

  // 3) Периодически отправляем что-то на сервер
  if (millis() - lastSendMs > 1000) {
    lastSendMs = millis();
    client.print("PING ms=");
    client.println(millis());
  }

  // 4) Если сервер закрыл соединение
  if (!client.connected()) {
    Serial.println("Server disconnected");
    client.stop();
    delay(500);
  }
}