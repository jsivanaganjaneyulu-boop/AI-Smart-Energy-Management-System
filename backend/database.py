# ============================================================
# AI-BASED SMART ENERGY MANAGEMENT SYSTEM
# MongoDB Database Connection
# ============================================================

from pymongo import MongoClient
from pymongo.errors import (
    ConnectionFailure,
    ServerSelectionTimeoutError,
    DuplicateKeyError
)
from bson import ObjectId
from datetime import datetime
import os


# ============================================================
# 1. MONGODB CONFIGURATION
# ============================================================

# Option 1:
# Put your MongoDB Atlas connection string directly here.
#
# Example:
# MONGO_URI = "mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/"

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://myuser:mypassword@cluster0.abc123.mongodb.net/?retryWrites=true&w=majority"
)

DATABASE_NAME = "smart_energy_db"


# ============================================================
# 2. CONNECT TO MONGODB
# ============================================================

client = None
db = None

users_collection = None
devices_collection = None
energy_collection = None
predictions_collection = None
alerts_collection = None
person_count_collection = None


def connect_database():

    global client
    global db

    global users_collection
    global devices_collection
    global energy_collection
    global predictions_collection
    global alerts_collection
    global person_count_collection

    try:

        if MONGO_URI == "YOUR_MONGODB_ATLAS_CONNECTION_STRING":

            print("\n========================================")
            print("MongoDB Atlas connection string missing!")
            print("Please update MONGO_URI in database.py")
            print("========================================\n")

            return False

        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000
        )

        # Test MongoDB connection
        client.admin.command("ping")

        # Select database
        db = client[DATABASE_NAME]

        # Select collections
        users_collection = db["users"]

        devices_collection = db["devices"]

        energy_collection = db["energy_usage"]

        predictions_collection = db["predictions"]

        alerts_collection = db["alerts"]

        person_count_collection = db["person_count"]

        # Create indexes
        users_collection.create_index(
            "email",
            unique=True
        )

        energy_collection.create_index(
            "timestamp"
        )

        devices_collection.create_index(
            "device_name"
        )

        predictions_collection.create_index(
            "prediction_time"
        )

        alerts_collection.create_index(
            "timestamp"
        )

        person_count_collection.create_index(
            "timestamp"
        )

        print("\n========================================")
        print("MongoDB Atlas Connected Successfully!")
        print(f"Database: {DATABASE_NAME}")
        print("========================================\n")

        return True

    except (
        ConnectionFailure,
        ServerSelectionTimeoutError
    ) as error:

        print("\n========================================")
        print("MongoDB Connection Failed!")
        print("========================================")
        print("Error:", error)
        print("========================================\n")

        return False

    except Exception as error:

        print("\n========================================")
        print("Unexpected MongoDB Error!")
        print("========================================")
        print("Error:", error)
        print("========================================\n")

        return False


# Connect automatically when this file is imported
connect_database()


# ============================================================
# 3. USER FUNCTIONS
# ============================================================

def create_user(
    name,
    email,
    password,
    role="user"
):

    if users_collection is None:
        return None

    user = {
        "name": name,
        "email": email,
        "password": password,
        "role": role,
        "created_at": datetime.utcnow()
    }

    try:

        result = users_collection.insert_one(user)

        return result.inserted_id

    except DuplicateKeyError:

        print("User with this email already exists.")

        return None

    except Exception as error:

        print("Error creating user:", error)

        return None


def get_user_by_email(email):

    if users_collection is None:
        return None

    try:

        return users_collection.find_one({
            "email": email
        })

    except Exception as error:

        print("Error finding user:", error)

        return None


def get_user_by_id(user_id):

    if users_collection is None:
        return None

    try:

        return users_collection.find_one({
            "_id": ObjectId(user_id)
        })

    except Exception as error:

        print("Error finding user:", error)

        return None


def get_all_users():

    if users_collection is None:
        return []

    try:

        return list(
            users_collection.find()
        )

    except Exception as error:

        print("Error getting users:", error)

        return []


def delete_user(user_id):

    if users_collection is None:
        return False

    try:

        result = users_collection.delete_one({
            "_id": ObjectId(user_id)
        })

        return result.deleted_count > 0

    except Exception as error:

        print("Error deleting user:", error)

        return False


# ============================================================
# 4. DEVICE FUNCTIONS
# ============================================================

def add_device(
    device_name,
    device_type,
    status="OFF",
    power_consumption=0,
    user_id=None
):

    if devices_collection is None:
        return None

    device = {
        "device_name": device_name,
        "device_type": device_type,
        "status": status,
        "power_consumption": power_consumption,
        "user_id": user_id,
        "created_at": datetime.utcnow()
    }

    try:

        result = devices_collection.insert_one(
            device
        )

        return result.inserted_id

    except Exception as error:

        print("Error adding device:", error)

        return None


def get_all_devices():

    if devices_collection is None:
        return []

    try:

        return list(
            devices_collection.find()
        )

    except Exception as error:

        print("Error getting devices:", error)

        return []


def get_device(device_id):

    if devices_collection is None:
        return None

    try:

        return devices_collection.find_one({
            "_id": ObjectId(device_id)
        })

    except Exception as error:

        print("Error getting device:", error)

        return None


def update_device_status(
    device_name,
    status
):

    if devices_collection is None:
        return False

    try:

        result = devices_collection.update_one(
            {
                "device_name": device_name
            },
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return result.modified_count > 0

    except Exception as error:

        print(
            "Error updating device status:",
            error
        )

        return False


def update_device_power(
    device_name,
    power_consumption
):

    if devices_collection is None:
        return False

    try:

        result = devices_collection.update_one(
            {
                "device_name": device_name
            },
            {
                "$set": {
                    "power_consumption":
                        power_consumption,
                    "updated_at":
                        datetime.utcnow()
                }
            }
        )

        return result.modified_count > 0

    except Exception as error:

        print(
            "Error updating device power:",
            error
        )

        return False


# ============================================================
# 5. ENERGY USAGE FUNCTIONS
# ============================================================

def save_energy_data(
    device_name,
    voltage,
    current,
    power_consumption,
    status="ON",
    user_id=None
):

    if energy_collection is None:
        return None

    energy_data = {

        "device_name": device_name,

        "voltage": float(voltage),

        "current": float(current),

        "power_consumption":
            float(power_consumption),

        "status": status,

        "user_id": user_id,

        "timestamp": datetime.utcnow()
    }

    try:

        result = energy_collection.insert_one(
            energy_data
        )

        return result.inserted_id

    except Exception as error:

        print(
            "Error saving energy data:",
            error
        )

        return None


def get_energy_data(
    limit=100
):

    if energy_collection is None:
        return []

    try:

        return list(
            energy_collection
            .find()
            .sort(
                "timestamp",
                -1
            )
            .limit(limit)
        )

    except Exception as error:

        print(
            "Error getting energy data:",
            error
        )

        return []


def get_device_energy_data(
    device_name,
    limit=100
):

    if energy_collection is None:
        return []

    try:

        return list(
            energy_collection
            .find({
                "device_name":
                    device_name
            })
            .sort(
                "timestamp",
                -1
            )
            .limit(limit)
        )

    except Exception as error:

        print(
            "Error getting device energy data:",
            error
        )

        return []


def get_latest_energy_data():

    if energy_collection is None:
        return None

    try:

        return energy_collection.find_one(
            sort=[
                ("timestamp", -1)
            ]
        )

    except Exception as error:

        print(
            "Error getting latest energy data:",
            error
        )

        return None


# ============================================================
# 6. AI PREDICTION FUNCTIONS
# ============================================================

def save_prediction(
    device_name,
    predicted_consumption,
    confidence=None,
    prediction_type="energy"
):

    if predictions_collection is None:
        return None

    prediction = {

        "device_name":
            device_name,

        "predicted_consumption":
            float(predicted_consumption),

        "confidence":
            confidence,

        "prediction_type":
            prediction_type,

        "prediction_time":
            datetime.utcnow()
    }

    try:

        result = predictions_collection.insert_one(
            prediction
        )

        return result.inserted_id

    except Exception as error:

        print(
            "Error saving prediction:",
            error
        )

        return None


def get_predictions(
    limit=100
):

    if predictions_collection is None:
        return []

    try:

        return list(
            predictions_collection
            .find()
            .sort(
                "prediction_time",
                -1
            )
            .limit(limit)
        )

    except Exception as error:

        print(
            "Error getting predictions:",
            error
        )

        return []


def get_latest_prediction(
    device_name=None
):

    if predictions_collection is None:
        return None

    try:

        query = {}

        if device_name is not None:

            query = {
                "device_name":
                    device_name
            }

        return predictions_collection.find_one(
            query,
            sort=[
                ("prediction_time", -1)
            ]
        )

    except Exception as error:

        print(
            "Error getting prediction:",
            error
        )

        return None


# ============================================================
# 7. ALERT FUNCTIONS
# ============================================================

def create_alert(
    device_name,
    alert_type,
    message,
    severity="warning"
):

    if alerts_collection is None:
        return None

    alert = {

        "device_name":
            device_name,

        "alert_type":
            alert_type,

        "message":
            message,

        "severity":
            severity,

        "status":
            "unread",

        "timestamp":
            datetime.utcnow()
    }

    try:

        result = alerts_collection.insert_one(
            alert
        )

        return result.inserted_id

    except Exception as error:

        print(
            "Error creating alert:",
            error
        )

        return None


def get_alerts(
    limit=100
):

    if alerts_collection is None:
        return []

    try:

        return list(
            alerts_collection
            .find()
            .sort(
                "timestamp",
                -1
            )
            .limit(limit)
        )

    except Exception as error:

        print(
            "Error getting alerts:",
            error
        )

        return []


def mark_alert_as_read(
    alert_id
):

    if alerts_collection is None:
        return False

    try:

        result = alerts_collection.update_one(

            {
                "_id":
                    ObjectId(alert_id)
            },

            {
                "$set": {
                    "status":
                        "read"
                }
            }
        )

        return result.modified_count > 0

    except Exception as error:

        print(
            "Error updating alert:",
            error
        )

        return False


# ============================================================
# 8. PERSON COUNT FUNCTIONS
# ============================================================

def save_person_count(
    count,
    location="default"
):

    if person_count_collection is None:
        return None

    data = {

        "person_count":
            int(count),

        "location":
            location,

        "timestamp":
            datetime.utcnow()
    }

    try:

        result = person_count_collection.insert_one(
            data
        )

        return result.inserted_id

    except Exception as error:

        print(
            "Error saving person count:",
            error
        )

        return None


def get_latest_person_count():

    if person_count_collection is None:
        return None

    try:

        return person_count_collection.find_one(
            sort=[
                ("timestamp", -1)
            ]
        )

    except Exception as error:

        print(
            "Error getting person count:",
            error
        )

        return None


def get_person_count_history(
    limit=100
):

    if person_count_collection is None:
        return []

    try:

        return list(
            person_count_collection
            .find()
            .sort(
                "timestamp",
                -1
            )
            .limit(limit)
        )

    except Exception as error:

        print(
            "Error getting person count:",
            error
        )

        return []


# ============================================================
# 9. DASHBOARD STATISTICS
# ============================================================

def get_database_statistics():

    if db is None:

        return {}

    try:

        return {

            "users":
                users_collection.count_documents({}),

            "devices":
                devices_collection.count_documents({}),

            "energy_records":
                energy_collection.count_documents({}),

            "predictions":
                predictions_collection.count_documents({}),

            "alerts":
                alerts_collection.count_documents({}),

            "person_count_records":
                person_count_collection
                .count_documents({})
        }

    except Exception as error:

        print(
            "Error getting statistics:",
            error
        )

        return {}


# ============================================================
# 10. CLOSE DATABASE CONNECTION
# ============================================================

def close_database():

    global client

    if client is not None:

        client.close()

        print(
            "MongoDB connection closed."
        )


# ============================================================
# 11. MAIN TEST
# ============================================================

if __name__ == "__main__":

    print("\nTesting MongoDB connection...\n")

    if db is not None:

        print(
            "Database statistics:"
        )

        print(
            get_database_statistics()
        )

    else:

        print(
            "Database is not connected."
        )