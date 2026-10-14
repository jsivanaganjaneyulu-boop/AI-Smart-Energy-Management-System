
from pymongo import MongoClient
from pymongo.errors import (
    ServerSelectionTimeoutError,
    PyMongoError
)
from datetime import datetime, timezone

# MongoDB connection URL
MONGO_URI = "mongodb://localhost:27017/"

# Connect to MongoDB
client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)

# Select project database
db = client["smart_energy"]


def test_connection():
    try:
        # Check whether MongoDB Server is running
        client.admin.command("ping")

        print("=" * 45)
        print("MONGODB CONNECTION SUCCESSFUL")
        print("=" * 45)
        print("Database name:", db.name)

        # Display existing collections
        collections = db.list_collection_names()
        print("Existing collections:", collections)

        # Check or create the users collection
        users = db["users"]

        # Insert a temporary test document
        test_document = {
            "test": True,
            "message": "Database connection test",
            "created_at": datetime.now(timezone.utc)
        }

        result = users.insert_one(test_document)
        print("Test document inserted successfully!")
        print("Inserted document ID:", result.inserted_id)

        # Read the inserted document
        saved_document = users.find_one(
            {"_id": result.inserted_id}
        )

        if saved_document:
            print("Test document retrieved successfully!")

        # Delete the temporary test document
        users.delete_one({"_id": result.inserted_id})
        print("Temporary test document deleted.")

        print("=" * 45)
        print("ALL DATABASE TESTS PASSED")
        print("=" * 45)

    except ServerSelectionTimeoutError:
        print("ERROR: Cannot connect to MongoDB.")
        print("Check that MongoDB Server is running.")
        print("Connection URL:", MONGO_URI)

    except PyMongoError as error:
        print("MongoDB operation failed:", error)

    finally:
        client.close()


if __name__ == "__main__":
    test_connection()
