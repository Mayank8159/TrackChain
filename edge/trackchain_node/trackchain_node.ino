// node/trackchain_node.ino  — ESP32-CAM + MPU6050 → TrackChain Space
#include "esp_camera.h"
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include "base64.h"

#define NODE_ID   "TC-NODE-01"
#define NODE_TOKEN "SECRET_TOKEN"            // provisioned, HMAC-issued by backend
#define WS_HOST   "trackchain-backend-7sensitive.hf.space"
#define WS_PORT   443
#define WS_PATH   "/ws/node?token=" NODE_TOKEN
#define WIFI_SSID "YOUR_SSID"
#define WIFI_PASS "YOUR_PASS"

#define FRAME_PERIOD_MS 200   // 5 fps (backend may override via cfg)
#define IMU_PERIOD_MS    50   // 20 Hz
#define HB_PERIOD_MS   5000

WebSocketsClient ws;
Adafruit_MPU6050 mpu;
volatile bool online = false;
uint32_t frameSeq = 0, imuSeq = 0;
unsigned long tFrame = 0, tImu = 0, tHb = 0;

// ---- camera (AI-Thinker OV2640 pinmap) ----
void setupCamera() {
  camera_config_t c;
  c.ledc_channel = LEDC_CHANNEL_0; c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0=5; c.pin_d1=18; c.pin_d2=19; c.pin_d3=21;
  c.pin_d4=36; c.pin_d5=39; c.pin_d6=34; c.pin_d7=35;
  c.pin_xclk=0; c.pin_pclk=22; c.pin_vsync=25; c.pin_href=23;
  c.pin_sscb_sda=26; c.pin_sscb_scl=27; c.pin_pwdn=32; c.pin_reset=-1;
  c.xclk_freq_hz = 20000000; c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = FRAMESIZE_SVGA; c.jpeg_quality = 12; c.fb_count = 2;
  esp_camera_init(&c);
}

void wsEvent(WStype_t type, uint8_t* payload, size_t len) {
  if (type == WStype_CONNECTED) {
    online = true;
    ws.sendTXT("{\"type\":\"hello\",\"node_id\":\"" NODE_ID "\",\"fw\":\"1.0\"}");
  } else if (type == WStype_DISCONNECTED || type == WStype_ERROR) {
    online = false;                      // → store-and-forward mode
  } else if (type == WStype_TEXT) {
    StaticJsonDocument<128> d; deserializeJson(d, payload, len);
    if (strcmp(d["type"], "cfg") == 0) { /* apply adaptive fps/quality */ }
  }
}

void sendIMU() {
  sensors_event_t a, g, t; mpu.getEvent(&a, &g, &t);
  StaticJsonDocument<256> d;
  d["type"]="imu"; d["t"]=millis(); d["seq"]=imuSeq++;
  d["ax"]=a.acceleration.x; d["ay"]=a.acceleration.y; d["az"]=a.acceleration.z;
  d["gx"]=g.gyro.x; d["gy"]=g.gyro.y; d["gz"]=g.gyro.z;
  String s; serializeJson(d, s);
  if (online) ws.sendTXT(s); /* else buffer to PSRAM ring for batch flush */
}

void sendFrame() {
  camera_fb_t* fb = esp_camera_fb_get(); if (!fb) return;
  String b64 = base64::encode(fb->buf, fb->len);
  String msg = "{\"type\":\"frame\",\"t\":" + String(millis()) +
               ",\"seq\":" + String(frameSeq++) +
               ",\"w\":" + String(fb->width) + ",\"h\":" + String(fb->height) +
               ",\"b64\":\"" + b64 + "\"}";
  if (online) ws.sendTXT(msg); /* else enqueue for HTTP batch flush */
  esp_camera_fb_return(fb);
}

void loop() {
  ws.loop();
  unsigned long now = millis();
  if (!online && now - tHb > 10000) {          // reconnect with backoff
    tHb = now; ws.beginSSL(WS_HOST, WS_PORT, WS_PATH);
  }
  if (now - tImu  > IMU_PERIOD_MS)   { tImu  = now; sendIMU();   }
  if (now - tFrame > FRAME_PERIOD_MS){ tFrame = now; sendFrame();}
  if (online && now - tHb > HB_PERIOD_MS){ tHb = now; ws.sendTXT("{\"type\":\"hb\"}"); }
}

void setup() {
  Serial.begin(115200); Wire.begin(); mpu.begin();
  setupCamera();
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) delay(250);
  ws.beginSSL(WS_HOST, WS_PORT, WS_PATH);
  ws.onEvent(wsEvent);
}
