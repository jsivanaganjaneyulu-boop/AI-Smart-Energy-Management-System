
# ============================================================
# AI-BASED SMART ENERGY MANAGEMENT SYSTEM
# Flask + YOLOv8 + OpenCV + MongoDB
# Registration + Login + Dashboard + Detection APIs
# File: backend/app.py
# ============================================================

from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from ultralytics import YOLO
from pymongo import MongoClient
from pymongo.errors import PyMongoError, DuplicateKeyError
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import cv2
import threading
import time
import re

# ============================================================
# 1. FLASK APPLICATION
# ============================================================

app = Flask(__name__)
CORS(app)

# ============================================================
# 2. MONGODB CONNECTION
# ============================================================

MONGO_URI = "mongodb://localhost:27017/"

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)

db = client["smart_energy"]

users = db["users"]
rooms = db["rooms"]
devices = db["devices"]
sensor_data = db["sensor_data"]
person_counts = db["person_counts"]
energy_records = db["energy_records"]
predictions = db["predictions"]
recommendations = db["recommendations"]
alerts = db["alerts"]
energy_reports = db["energy_reports"]

# Shared state locks
data_lock = threading.Lock()
camera_lock = threading.Lock()

# ============================================================
# 3. GLOBAL VARIABLES
# ============================================================

person_count = 0
room_status = "UNKNOWN"
energy_mode = "UNKNOWN"
camera_status = False
model_status = False

energy_today = 12.45       # Demo value; replace with real data
current_power = 560        # Demo value; replace with real data
total_devices = 18         # Demo value; replace with real data

last_saved_time = 0
SAVE_INTERVAL = 30

# ============================================================
# 4. LOAD YOLOv8 MODEL
# ============================================================

print("Loading YOLOv8 model...")

try:
    model = YOLO("yolov8n.pt")
    model_status = True
    print("YOLOv8 model loaded successfully.")

except Exception as error:
    model = None
    model_status = False
    print("YOLOv8 model loading failed:", error)

# ============================================================
# 5. OPEN CAMERA
# ============================================================

print("Opening camera...")

camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if camera.isOpened():
    camera_status = True
    print("Camera opened successfully.")
else:
    camera_status = False
    print("WARNING: Camera could not be opened.")

# ============================================================
# 6. USER REGISTRATION API
# ============================================================

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "")
    email = data.get("email", "")
    password = data.get("password", "")

    if not all(isinstance(v, str) for v in (name, email, password)):
        return jsonify({
            "success": False,
            "message": "Invalid input format"
        }), 400

    name = name.strip()
    email = email.strip().lower()

    if not name or not email or not password:
        return jsonify({
            "success": False,
            "message": "Name, email and password are required"
        }), 400

    if len(name) > 100 or len(email) > 254:
        return jsonify({
            "success": False,
            "message": "Name or email is too long"
        }), 400

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify({
            "success": False,
            "message": "Enter a valid email address"
        }), 400

    if len(password) < 8:
        return jsonify({
            "success": False,
            "message": "Password must be at least 8 characters"
        }), 400

    try:
        password_hash = generate_password_hash(password)

        user_document = {
            "name": name,
            "email": email,
            "password_hash": password_hash,
            "role": "user",
            "created_at": datetime.now(timezone.utc)
        }

        result = users.insert_one(user_document)

        return jsonify({
            "success": True,
            "message": "Registration successful",
            "user_id": str(result.inserted_id)
        }), 201

    except DuplicateKeyError:
        return jsonify({
            "success": False,
            "message": "This email is already registered"
        }), 409

    except PyMongoError:
        app.logger.exception("Registration database error")
        return jsonify({
            "success": False,
            "message": "Database operation failed"
        }), 503


# ============================================================
# 7. USER LOGIN API
# ============================================================

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "")
    password = data.get("password", "")

    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({
            "success": False,
            "message": "Invalid input format"
        }), 400

    email = email.strip().lower()

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password are required"
        }), 400

    try:
        user = users.find_one({"email": email})

        if (
            not user
            or not user.get("password_hash")
            or not check_password_hash(
                user["password_hash"], password
            )
        ):
            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401

        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": {
                "id": str(user["_id"]),
                "name": user["name"],
                "email": user["email"],
                "role": user.get("role", "user")
            }
        }), 200

    except PyMongoError:
        app.logger.exception("Login database error")
        return jsonify({
            "success": False,
            "message": "Database operation failed"
        }), 503


# ============================================================
# 8. SAVE PERSON DETECTION TO MONGODB
# ============================================================

def save_detection_record(count, status, mode, camera_working):
    try:
        person_counts.insert_one({
            "person_count": count,
            "room_status": status,
            "energy_mode": mode,
            "camera_status": camera_working,
            "recorded_at": datetime.now(timezone.utc)
        })
        return True

    except PyMongoError:
        app.logger.exception("Failed to save person detection")
        return False


# ============================================================
# 9. LIVE CAMERA AND YOLOv8 PERSON DETECTION
# ============================================================

def generate_frames():
    global person_count
    global room_status
    global energy_mode
    global camera_status
    global last_saved_time

    while True:
        if not camera.isOpened():
            camera_status = False
            time.sleep(1)
            continue

        with camera_lock:
            success, frame = camera.read()

        if not success:
            camera_status = False
            time.sleep(0.1)
            continue

        camera_status = True

        if model is None:
            with data_lock:
                room_status = "UNKNOWN"
                energy_mode = "UNKNOWN"
        else:
            try:
                results = model(frame, verbose=False)
                detected_people = 0

                for result in results:
                    if result.boxes is None:
                        continue

                    for box in result.boxes:
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])

                        # COCO class 0 represents a person
                        if class_id == 0 and confidence >= 0.40:
                            detected_people += 1

                            x1, y1, x2, y2 = map(
                                int, box.xyxy[0]
                            )

                            cv2.rectangle(
                                frame,
                                (x1, y1),
                                (x2, y2),
                                (0, 255, 0),
                                2
                            )

                            cv2.putText(
                                frame,
                                f"Person {confidence:.2f}",
                                (x1, max(y1 - 10, 20)),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                (0, 255, 0),
                                2
                            )

                with data_lock:
                    person_count = detected_people

                    if person_count > 0:
                        room_status = "OCCUPIED"
                        energy_mode = "NORMAL"
                    else:
                        room_status = "UNOCCUPIED"
                        energy_mode = "SAVING"

            except Exception:
                app.logger.exception("YOLO detection failed")

        with data_lock:
            count = person_count
            status = room_status
            mode = energy_mode

        status_color = (
            (0, 255, 0)
            if status == "OCCUPIED"
            else (0, 0, 255)
        )

        cv2.putText(
            frame,
            f"People Count: {count}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"Room: {status}",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            status_color,
            2
        )

        cv2.putText(
            frame,
            f"Energy Mode: {mode}",
            (20, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            status_color,
            2
        )

        # Save detection periodically while the camera feed is used
        now = time.time()

        if now - last_saved_time >= SAVE_INTERVAL:
            if save_detection_record(
                count, status, mode, camera_status
            ):
                last_saved_time = now

        success, buffer = cv2.imencode(".jpg", frame)

        if not success:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )


# ============================================================
# 10. HOME ROUTE
# ============================================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "project": "AI-Based Smart Energy Management System",
        "status": "Backend is running",
        "model": "YOLOv8",
        "model_loaded": model_status,
        "camera": camera_status
    })


# ============================================================
# 11. MONGODB HEALTH CHECK
# ============================================================

@app.route("/api/health", methods=["GET"])
def health():
    try:
        client.admin.command("ping")

        return jsonify({
            "status": "success",
            "database": db.name,
            "message": "MongoDB connected successfully"
        }), 200

    except PyMongoError:
        return jsonify({
            "status": "error",
            "message": "MongoDB connection failed"
        }), 503


# ============================================================
# 12. LIVE VIDEO ROUTE
# ============================================================

@app.route("/video_feed", methods=["GET"])
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# ============================================================
# 13. CURRENT DETECTION API
# ============================================================

@app.route("/api/detection", methods=["GET"])
def detection():
    with data_lock:
        return jsonify({
            "person_count": person_count,
            "room_status": room_status,
            "energy_mode": energy_mode,
            "camera": camera_status,
            "model_loaded": model_status
        })


# ============================================================
# 14. SAVE DETECTION ON REQUEST
# ============================================================

@app.route("/api/detection/save", methods=["POST"])
def save_detection():
    with data_lock:
        count = person_count
        status = room_status
        mode = energy_mode
        working = camera_status

    if not save_detection_record(count, status, mode, working):
        return jsonify({
            "error": "Could not save detection to MongoDB"
        }), 503

    return jsonify({
        "message": "Detection saved successfully",
        "person_count": count
    }), 201


# ============================================================
# 15. DETECTION HISTORY API
# ============================================================

@app.route("/api/detection/history", methods=["GET"])
def detection_history():
    try:
        records = list(
            person_counts.find(
                {},
                {"_id": 0}
            ).sort("recorded_at", -1).limit(50)
        )

        return jsonify(records), 200

    except PyMongoError:
        app.logger.exception("Detection history retrieval failed")
        return jsonify({
            "error": "Could not retrieve detection history"
        }), 503


# ============================================================
# 16. DASHBOARD API
# ============================================================

@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    with data_lock:
        count = person_count
        status = room_status
        mode = energy_mode
        working = camera_status

    return jsonify({
        "energy": energy_today,
        "power": current_power,
        "devices": total_devices,
        "person_count": count,
        "room_status": status,
        "energy_mode": mode,
        "camera": working
    })


# ============================================================
# 17. SAVE SENSOR DATA API
# ============================================================

@app.route("/api/sensor-data", methods=["POST"])
def save_sensor_data():
    data = request.get_json(silent=True) or {}

    try:
        temperature = float(data["room_temperature"])
        humidity = float(data["humidity"])

        if not 0 <= temperature <= 60:
            raise ValueError("Invalid temperature")

        if not 0 <= humidity <= 100:
            raise ValueError("Invalid humidity")

        result = sensor_data.insert_one({
            "room_temperature": temperature,
            "humidity": humidity,
            "recorded_at": datetime.now(timezone.utc)
        })

        return jsonify({
            "message": "Sensor data saved successfully",
            "id": str(result.inserted_id)
        }), 201

    except (KeyError, TypeError, ValueError):
        return jsonify({
            "error": "Provide valid temperature and humidity"
        }), 400

    except PyMongoError:
        app.logger.exception("Sensor data save failed")
        return jsonify({
            "error": "Database operation failed"
        }), 503


# ============================================================
# 18. READ SENSOR DATA API
# ============================================================

@app.route("/api/sensor-data", methods=["GET"])
def get_sensor_data():
    try:
        records = list(
            sensor_data.find(
                {},
                {"_id": 0}
            ).sort("recorded_at", -1).limit(50)
        )

        return jsonify(records), 200

    except PyMongoError:
        app.logger.exception("Sensor data retrieval failed")
        return jsonify({
            "error": "Could not retrieve sensor data"
        }), 503


# ============================================================
# 19. START APPLICATION
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print(" AI-BASED SMART ENERGY MANAGEMENT SYSTEM")
    print("=" * 55)

    try:
        # Verify MongoDB connection
        client.admin.command("ping")

        # Ensure email addresses are unique
        users.create_index("email", unique=True)

        print("MongoDB: Connected")
        print("Database:", db.name)

    except PyMongoError as error:
        print("MongoDB connection failed:", error)
        print("Check that MongoDB Server is running.")
        client.close()
        raise SystemExit(1)

    print("YOLOv8 loaded:", model_status)
    print("Camera opened:", camera_status)
    print("Backend: http://127.0.0.1:5000")
    print("Registration: POST /api/register")
    print("Login: POST /api/login")
    print("Live video: http://127.0.0.1:5000/video_feed")
    print("Detection: http://127.0.0.1:5000/api/detection")
    print("Dashboard: http://127.0.0.1:5000/api/dashboard")
    print("MongoDB health: http://127.0.0.1:5000/api/health")
    print("=" * 55)

    try:
        app.run(
            host="127.0.0.1",
            port=5000,
            debug=False,
            threaded=True
        )
    finally:
        with camera_lock:
            camera.release()

        client.close()
        print("Camera and MongoDB connection closed.")
