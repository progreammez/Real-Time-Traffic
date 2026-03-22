// ================= LIBRARIES =================
#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <WiFi.h>
#include <WebServer.h>

// ================= WIFI =================
const char* ssid = "Airtel_Pant_Ext"; 
const char* password = "A1rtelP@ntExt"; 

WebServer server(80);

// ================= LED =================
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ================= RFID =================
#define SS_PIN 5
#define RST_PIN 22
MFRC522 mfrc522(SS_PIN, RST_PIN);

// ================= CONFIG =================
#define NUM_DIR 4
#define LANES 3

int traffic[NUM_DIR][LANES];
int total[NUM_DIR];
const char* dirNames[4] = {"North", "East", "South", "West"};

// ================= STATE =================
bool pedestrianRequest = false;
bool emergencyActive = false;
int emergencyDirection = -1;
unsigned long lastSeenTime = 0;
String currentState = "Idle";
int currentTimeLeft = 0;
int currentDirection = 0;
String signalColor = "RED";

// ================= MULTI EMERGENCY QUEUE =================
#define MAX_QUEUE 10

int emergencyQueue[MAX_QUEUE];
int front = 0;
int rear = 0;

int currentEmergency = -1;

// ================= PINS =================
int redPins[4]    = {4, 16, 17, 5};
int yellowPins[4] = {18, 19, 21, 22};
int greenPins[4]  = {23, 25, 26, 27};
int emergencyPins[4] = {32, 33, 14, 15};

int buzzerPin = 13;
int buttonPin = 12;

// ================= FUNCTION DECLARATIONS =================
void generateTraffic();
void calculateWeights();
void runCycle();
void handlePedestrian();
void setSignal(int dir);
void setAllRed();
void checkRFID();
void handleEmergencySignal();
void handleRoot();

// ================= SETUP =================
void setup() {

  Serial.begin(115200); //Baud Rate for Serial Monitor
  randomSeed(analogRead(0)); //Produces different traffic each time

  SPI.begin();
  mfrc522.PCD_Init();

  lcd.init();
  lcd.backlight();

  lcd.setCursor(0, 0);
  lcd.print("Traffic System");

  WiFi.begin(ssid, password);

  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(2000 );
    Serial.print(".");
  }

  Serial.println("\nConnected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  server.on("/", handleRoot);
  server.on("/status", handleStatus);
  server.begin();

  for (int i = 0; i < 4; i++) {
    pinMode(redPins[i], OUTPUT);
    pinMode(yellowPins[i], OUTPUT);
    pinMode(greenPins[i], OUTPUT);
    pinMode(emergencyPins[i], OUTPUT);
  }

  pinMode(buzzerPin, OUTPUT);
  pinMode(buttonPin, INPUT);

  setAllRed();

  Serial.println("System Ready");
  Serial.println("Controls: e=Emergency | p=Pedestrian | r=Reset | 0-3=Direction"); //Manual controls
}

// ================= LOOP =================
void loop() {
  server.handleClient();
  checkRFID();

  // If already handling OR queue has items
  if (emergencyActive || !isQueueEmpty()) {

    // If no current emergency, pick next
    if (!emergencyActive) {
      currentEmergency = dequeue();

      if (currentEmergency != -1) {
        emergencyDirection = currentEmergency;
        emergencyActive = true;

        Serial.print("Now handling emergency: ");
        Serial.println(emergencyDirection);
      }
    }

    handleEmergencySignal();   

  } else {
    runCycle();  
  }  
}

// ================= TRAFFIC =================
void generateTraffic() {

  Serial.println("\n--- New Cycle ---");

  for (int i = 0; i < NUM_DIR; i++) {
    for (int j = 0; j < LANES; j++) {

      int cars = random(0, 10);
      int buses = random(0, 3);
      int bikes = random(0, 20);

      traffic[i][j] = cars + (buses * 3) + (bikes * 0.5); //Buses = 3x Cars, Bikes = 0.5x Cars

      Serial.print(dirNames[i]);
      Serial.print(" Lane ");
      Serial.print(j);
      Serial.print(" → ");
      Serial.println(traffic[i][j]);
    }
  }
}

void calculateWeights() {

  Serial.println("\nTotal Weights:");

  for (int i = 0; i < NUM_DIR; i++) {

    total[i] = 0; //Initialise the value

    for (int j = 0; j < LANES; j++) {
      total[i] += traffic[i][j]; //Calculates total traffic per direction
    }

    Serial.print(dirNames[i]);
    Serial.print(" → ");
    Serial.println(total[i]);
  }
}

// ================= SIGNAL CONTROL =================
void setAllRed() {

  for (int i = 0; i < 4; i++) {
    digitalWrite(redPins[i], HIGH);
    digitalWrite(yellowPins[i], LOW);
    digitalWrite(greenPins[i], LOW);
    digitalWrite(emergencyPins[i], LOW);
  }
}

void setSignal(int dir) {

  setAllRed();

  digitalWrite(redPins[dir], LOW);
  digitalWrite(greenPins[dir], HIGH);
}

// ================= MAIN CYCLE =================
void runCycle() {
  generateTraffic();
  calculateWeights();

  int baseTime = 3000;
  int factor = 200;

  for (int i = 0; i < NUM_DIR; i++) {

    if (digitalRead(buttonPin) == HIGH) {
      pedestrianRequest = true;
    }

    int greenTime = baseTime + (total[i] * factor); //Main logic
    int seconds = greenTime / 1000;

    Serial.print("\nServing: ");
    Serial.println(dirNames[i]);

    Serial.print("Serving Direction: ");
    Serial.println(dirNames[i]);

    Serial.print("Green Time: ");
    Serial.println(greenTime);

    setSignal(i);
    currentDirection = i;
    signalColor = "GREEN";

    for (int t = seconds; t > 0; t--) {
      
      currentState = String(dirNames[i]) + " GREEN ";
      currentTimeLeft = t;
      currentDirection = i;
      signalColor = "GREEN";

      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print(dirNames[i]);
      lcd.print(" GREEN ");

      lcd.setCursor(0, 1);
      lcd.print(" Time: ");
      lcd.print(t);

      Serial.print(dirNames[i]);
      Serial.print(" GREEN: ");
      Serial.println(t);

      server.handleClient();
      for (int d = 0; d < 100; d++) {
        server.handleClient();
        delay(10);
      }

      //check emergency during countdown
      checkRFID();
      if (emergencyActive) {
        return;
        }
    }

    // YELLOW
    digitalWrite(greenPins[i], LOW);
    digitalWrite(yellowPins[i], HIGH);
    for (int t = 2; t > 0; t--) {
      
      currentState = String(dirNames[i]) + " YELLOW ";
      currentTimeLeft = t;
      signalColor = "YELLOW";

      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print(dirNames[i]);
      lcd.print(" YELLOW");

      lcd.setCursor(0, 1);
      lcd.print("Time: ");
      lcd.print(t);

      Serial.print(dirNames[i]);
      Serial.print(" YELLOW: ");
      Serial.println(t);

      signalColor = "YELLOW";

      server.handleClient();
      for (int d = 0; d < 100; d++) {
        server.handleClient();
        delay(10);
      }
    }
    digitalWrite(yellowPins[i], LOW);

    // RED
    digitalWrite(redPins[i], HIGH);
    signalColor = "RED";

    if (pedestrianRequest) {
      handlePedestrian();
      pedestrianRequest = false;
    }
  }
}

// ================= PEDESTRIAN =================
void handlePedestrian() {

  Serial.println("Pedestrian Crossing");
  currentDirection = -1;
  signalColor = "RED";
  setAllRed();

  digitalWrite(buzzerPin, HIGH);
  for (int t = 7; t > 0; t--) {

    currentState = "Pedestrian Crossing";
    currentTimeLeft = t;

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("PEDESTRIAN");
    lcd.print(" YELLOW");

    lcd.setCursor(0, 1);
    lcd.print("Time: ");
    lcd.print(t);
    
    Serial.print("Crossing: ");
    Serial.println(t);

    for (int d = 0; d < 100; d++) {
      server.handleClient();
      delay(10);
    }
  }
  digitalWrite(buzzerPin, LOW);
}

// ================= RFID =================
void checkRFID() {

  // Simulation (press 'e')
  if (Serial.available()) {
    char input = Serial.read();

    if (input == 'e') {
      Serial.println("Manually Simulated Emergency");
      emergencyActive = true;
      emergencyDirection = random(0, 4);
      lastSeenTime = millis();
    }

    if (input == 'p') {
      Serial.println("Manual Pedestrian Trigger");
      pedestrianRequest = true;
    }

    if (input == 'r') {
      Serial.println("System Reset");
      emergencyActive = false;
      pedestrianRequest = false;
    }

    if (input >= '0' && input <= '3') {
      emergencyDirection = input - '0';
      emergencyActive = true;
      lastSeenTime = millis();

      Serial.print("Emergency forced at ");
      Serial.println(dirNames[emergencyDirection]);
    }
  }

  // Real RFID
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {

    String uid = "";

    for (byte i = 0; i < mfrc522.uid.size; i++) {
      uid += String(mfrc522.uid.uidByte[i], HEX);
    }

    Serial.print("Card UID: ");
    Serial.println(uid);

    String emergencyUID = "a1b2c3d4";

    if (uid == emergencyUID) {

      Serial.println("Emergency Vehicle Detected!");

      enqueue(0);   // or whichever direction, update later
      lastSeenTime = millis();
    }

    mfrc522.PICC_HaltA();
  }

  // Timeout (vehicle passed)
  if (emergencyActive && (millis() - lastSeenTime > 3000)) {
    Serial.println("Emergency Cleared");
    if (!mfrc522.PICC_IsNewCardPresent()) {

      Serial.println("Emergency cleared");

      delay(2000);

      emergencyActive = false;
      currentEmergency = -1;
    }
  }
}

// ================= EMERGENCY MODE =================
void handleEmergencySignal() {

  setAllRed();

  int dir = emergencyDirection;
  currentDirection = emergencyDirection;
  signalColor = "GREEN";
  digitalWrite(emergencyPins[dir], HIGH);
  digitalWrite(redPins[dir], LOW);
  digitalWrite(greenPins[dir], HIGH);

  digitalWrite(buzzerPin, HIGH);

  currentState = "Emergency " + String(dirNames[dir]);
  currentTimeLeft = 0;

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Emergency");

  lcd.setCursor(0, 1);
  lcd.print(dirNames[dir]);

  Serial.print("Emergency ACTIVE at direction ");
  Serial.println(dirNames[dir]);

  for (int d = 0; d < 10; d++) {
    server.handleClient();
    delay(10);
  }
}

// ================= WEB DASHBOARD =================
void handleStatus() {

  String json = "{";
  
  json += "\"direction\":" + String(currentDirection) + ",";
  json += "\"state\":\"" + signalColor + "\",";
  json += "\"emergency\":" + String(emergencyActive ? "true" : "false") + ",";
  json += "\"emergency_dir\":" + String(emergencyDirection) + ",";
  json += "\"pedestrian\":" + String(pedestrianRequest ? "true" : "false");

  json += ",\"north\":" + String(total[0]);
  json += ",\"east\":" + String(total[1]);
  json += ",\"south\":" + String(total[2]);
  json += ",\"west\":" + String(total[3]);
  json += "}";

  server.send(200, "application/json", json);
}

void handleRoot() {

  String html = "<html><head><meta http-equiv='refresh' content='1'/>";
  html += "<style>body{font-family:Arial;text-align:center;}h1{color:#333;}</style>";
  html += "</head><body>";

  html += "<h1>Smart Traffic System</h1>";

  html += "<p><b>State:</b> " + currentState + "</p>";
  html += "<p><b>Time Left:</b> " + String(currentTimeLeft) + " sec</p>";

  html += "<p><b>Emergency:</b> ";
  html += (emergencyActive ? "ACTIVE" : "OFF");
  html += "</p>";

  html += "<p><b>Pedestrian:</b> ";
  html += (pedestrianRequest ? "WAITING" : "NONE");
  html += "</p>";

  html += "</body></html>";

  server.send(200, "text/html", html);
}

void enqueue(int dir) {
  int next = (rear + 1) % MAX_QUEUE;

  if (next == front) {
    Serial.println("Queue Full - dropping request");
    return;
  }

  emergencyQueue[rear] = dir;
  rear = next;

  Serial.print("Enqueued Emergency: ");
  Serial.println(dir);
}

int dequeue() {
  if (front == rear) return -1;

  int val = emergencyQueue[front];
  front = (front + 1) % MAX_QUEUE;

  return val;
}

bool isQueueEmpty() {
  return front == rear;
}