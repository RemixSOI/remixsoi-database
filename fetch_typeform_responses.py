import requests
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime

load_dotenv()

# Configuration
TYPEFORM_API_TOKEN = os.getenv("TYPEFORM_API_TOKEN")
TYPEFORM_FORM_ID = os.getenv("TYPEFORM_FORM_ID")
MONGODB_URI = os.getenv("MONGODB_URI")

if not all([TYPEFORM_API_TOKEN, TYPEFORM_FORM_ID, MONGODB_URI]):
    raise ValueError("Missing: TYPEFORM_API_TOKEN, TYPEFORM_FORM_ID, or MONGODB_URI")

# Typeform API endpoint
TYPEFORM_API_URL = f"https://api.typeform.com/forms/{TYPEFORM_FORM_ID}/responses"

# MongoDB connection
client = MongoClient(MONGODB_URI)
db = client["RemixDB"]
typeform_collection = db["TypeformResponses"]

print(f"Fetching responses from form: {TYPEFORM_FORM_ID}")

try:
    # Fetch all responses
    headers = {
        "Authorization": f"Bearer {TYPEFORM_API_TOKEN}"
    }
    
    params = {
        "page_size": 1000
    }
    
    response = requests.get(TYPEFORM_API_URL, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        exit(1)
    
    data = response.json()
    responses = data.get("items", [])
    
    print(f"Found {len(responses)} responses")
    
    # Insert responses into MongoDB
    inserted_count = 0
    updated_count = 0
    
    for form_response in responses:
        response_doc = {
            "response_id": form_response.get("response_id"),
            "form_id": form_response.get("form_id"),
            "timestamp": form_response.get("submitted_at"),
            "respondent_id": form_response.get("respondent_id"),
            "answers": form_response.get("answers", []),
            "landing_id": form_response.get("landing_id"),
            "token": form_response.get("token"),
            "stored_at": datetime.utcnow(),
            "from_api_fetch": True
        }
        
        result = typeform_collection.update_one(
            {"response_id": response_doc["response_id"]},
            {"$set": response_doc},
            upsert=True
        )
        
        if result.upserted_id:
            inserted_count += 1
        else:
            updated_count += 1
    
    print(f"\n✓ Inserted: {inserted_count} new responses")
    print(f"✓ Updated: {updated_count} existing responses")
    print(f"✓ Total in database: {typeform_collection.count_documents({})}")
    
    # Show sample
    sample = typeform_collection.find_one({})
    if sample:
        print(f"\nSample response:")
        print(f"  Response ID: {sample.get('response_id')}")
        print(f"  Submitted: {sample.get('timestamp')}")
        print(f"  Answers: {len(sample.get('answers', []))}")

except Exception as e:
    print(f"Error: {str(e)}")
