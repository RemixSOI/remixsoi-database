from pymongo import MongoClient
from twilio.rest import Client
import time
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variables
mongobd_uri = os.getenv("MONGODB_URI")
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
from_number = os.getenv("TWILIO_FROM_NUMBER")
to_number = os.getenv("TWILIO_TO_NUMBER")

# Validate that all required credentials are set
if not all([mongobd_uri, account_sid, auth_token, from_number, to_number]):
    raise ValueError("Missing required environment variables. Please check your .env file.")

# Connect to MongoDB
client = MongoClient(mongobd_uri)
Twilio = client["TwilioDB"]
Messages = Twilio["Messages"]

Messages.insert_one({"message": "Hello, World!", "timestamp": "2023-10-01"})

# Initialize Twilio client
twilio_client = Client(account_sid, auth_token)

numbers = [to_number]

for to_number in numbers:
    try:
        message = twilio_client.messages.create(
            body="Test message from Twilio",
            from_=from_number,
            to=to_number
        )
        print(f"Message SID: {message.sid}")
        print(f"Status: {message.status}")
        message_data = {
                "sid": message.sid,
                "body": message.body,
                "from_": message.from_,
                "to": message.to,
                "status": message.status,
                "date_created": message.date_created,
                "date_sent": message.date_sent,
                "date_updated": message.date_updated,
                "error": None
            }
        Messages.insert_one(message_data)
        Messages.update_one(
                {"sid": message.sid},
                {"$set": {
                    "status": message.status,
                    "date_updated": message.date_updated,
                    "error": getattr(message, "error_message", None)
                }}
        )
        
        # Check message status after a few seconds
        time.sleep(2)
        msg = twilio_client.messages(message.sid).fetch()
        print(f"Updated Status: {msg.status}")

    except Exception as e:
        print("Send error:", e)
        Messages.insert_one({
                "sid": None,
                "body": "Test message from Twilio",
                "from_": from_number,
                "to": to_number,
                "status": "send_failed",
                "date_created": None,
                "date_sent": None,
                "date_updated": None,
                "error": str(e)
            })