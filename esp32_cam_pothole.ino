#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ─── WiFi Config ───────────────────────────────────────────────
const char* WIFI_SSID     = "WIFI that you will use to share data through website";
const char* WIFI_PASSWORD = "WIFI PSWRD";

// ─── Server Config ─────────────────────────────────────────────
const char* SERVER_URL = "URL OF SERVER(you can get through the ipconfig cmd)";

// ─── Capture Interval ──────────────────────────────────────────
const int CAPTURE_INTERVAL_MS = 3000;  // Capture every 3 seconds

// ─── LED ───────────────────────────────────────────────────────
#define LED_PIN 4

// ─── Camera Pin Config (AI Thinker ESP32-CAM) ──────────────────
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

int totalDetections = 0;
unsigned long lastCaptureTime = 0;

// ══════════════════════════════════════════════════════════════
void setup() {
  Serial.begin(115200);
  Serial.println("\n[BOOT] Pothole Detection System Starting...");

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  initCamera();
  connectWiFi();

  Serial.println("[READY] System ready. Starting detection loop...");
}

// ══════════════════════════════════════════════════════════════
void loop() {
  unsigned long now = millis();
  if (now - lastCaptureTime >= CAPTURE_INTERVAL_MS) {
    lastCaptureTime = now;
    captureAndSend();
  }
}

// ──────────────────────────────────────────────────────────────
void captureAndSend() {
  // Capture image
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[CAM] Capture failed!");
    return;
  }
  Serial.printf("[CAM] Captured: %d bytes (%dx%d)\n", fb->len, fb->width, fb->height);

  // Send to server
  if (WiFi.status() == WL_CONNECTED) {
    sendToServer(fb);
  } else {
    Serial.println("[WiFi] Disconnected, reconnecting...");
    connectWiFi();
  }

  esp_camera_fb_return(fb);
}

// ──────────────────────────────────────────────────────────────
void sendToServer(camera_fb_t* fb) {
  HTTPClient http;
  http.begin(SERVER_URL);
  http.setTimeout(10000);

  // Build multipart form data
  String boundary = "----ESP32Boundary";
  String bodyStart = "--" + boundary + "\r\n";
  bodyStart += "Content-Disposition: form-data; name=\"image\"; filename=\"frame.jpg\"\r\n";
  bodyStart += "Content-Type: image/jpeg\r\n\r\n";
  String bodyEnd = "\r\n--" + boundary + "--\r\n";

  int totalLen = bodyStart.length() + fb->len + bodyEnd.length();
  uint8_t* body = (uint8_t*)malloc(totalLen);

  if (!body) {
    Serial.println("[HTTP] Memory allocation failed!");
    http.end();
    return;
  }

  memcpy(body, bodyStart.c_str(), bodyStart.length());
  memcpy(body + bodyStart.length(), fb->buf, fb->len);
  memcpy(body + bodyStart.length() + fb->len, bodyEnd.c_str(), bodyEnd.length());

  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);

  Serial.println("[HTTP] Sending to server...");
  int httpCode = http.POST(body, totalLen);
  free(body);

  if (httpCode == 200) {
    String response = http.getString();
    parseResponse(response);
  } else {
    Serial.printf("[HTTP] Error: %d\n", httpCode);
  }

  http.end();
}

// ──────────────────────────────────────────────────────────────
void parseResponse(String& response) {
  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, response);

  if (err) {
    Serial.println("[JSON] Parse error");
    return;
  }

  bool detected    = doc["pothole_detected"] | false;
  float confidence = doc["confidence"]       | 0.0;
  int count        = doc["pothole_count"]    | 0;

  // Material info
  float area_m2       = doc["materials"]["area_m2"]      | 0.0;
  float cement_kg     = doc["materials"]["cement_kg"]    | 0.0;
  float sand_kg       = doc["materials"]["sand_kg"]      | 0.0;
  float aggregate_kg  = doc["materials"]["aggregate_kg"] | 0.0;

  if (detected) {
    totalDetections++;
    Serial.println("╔══════════════════════════════════╗");
    Serial.println("║      POTHOLE DETECTED!           ║");
    Serial.printf ("║  Confidence : %.1f%%              \n", confidence * 100);
    Serial.printf ("║  Count      : %d                 \n", count);
    Serial.printf ("║  Area       : %.4f m²            \n", area_m2);
    Serial.println("║  Materials Needed:               ║");
    Serial.printf ("║    Cement   : %.2f kg            \n", cement_kg);
    Serial.printf ("║    Sand     : %.2f kg            \n", sand_kg);
    Serial.printf ("║    Aggregate: %.2f kg            \n", aggregate_kg);
    Serial.printf ("║  Total so far: %d                \n", totalDetections);
    Serial.println("╚══════════════════════════════════╝");

    // Flash LED 3 times
    flashLED(3);

  } else {
    Serial.printf("[OK] Road clear. Confidence: %.1f%%\n", confidence * 100);
  }
}

// ──────────────────────────────────────────────────────────────
void initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size   = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count     = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[CAM] Init failed: 0x%x\n", err);
    while (true) { delay(1000); }
  }

  sensor_t* s = esp_camera_sensor_get();
  s->set_brightness(s, 0);
  s->set_contrast(s, 1);
  s->set_saturation(s, -1);
  s->set_whitebal(s, 1);
  s->set_awb_gain(s, 1);
  s->set_exposure_ctrl(s, 1);
  s->set_aec2(s, 1);

  Serial.println("[CAM] Camera initialized (VGA)");
}

// ──────────────────────────────────────────────────────────────
void connectWiFi() {
  Serial.printf("[WiFi] Connecting to %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[WiFi] Failed! Will retry...");
  }
}

// ──────────────────────────────────────────────────────────────
void flashLED(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(150);
    digitalWrite(LED_PIN, LOW);
    delay(150);
  }
}
