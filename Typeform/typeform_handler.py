from flask import Flask, request, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime
import hmac
import hashlib

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB setup
mongobd_uri = os.getenv("MONGODB_URI")
typeform_secret = os.getenv("TYPEFORM_WEBHOOK_SECRET")
typeform_form_id = os.getenv("TYPEFORM_FORM_ID")

if not all([mongobd_uri, typeform_secret, typeform_form_id]):
    raise ValueError("Missing required environment variables: MONGODB_URI, TYPEFORM_WEBHOOK_SECRET, TYPEFORM_FORM_ID")

client = MongoClient(mongobd_uri)
db = client["RemixDB"]
typeform_collection = db["TypeformResponses"]

# Create index for faster queries
typeform_collection.create_index("response_id", unique=True, sparse=True)


def verify_typeform_signature(request_body, signature_header):
    """Verify the Typeform webhook signature"""
    expected_signature = hmac.new(
        typeform_secret.encode(),
        request_body,
        hashlib.sha256
    ).digest()
    expected_signature = "sha256=" + hashlib.sha256(request_body).hexdigest()
    return signature_header == expected_signature


@app.route('/webhook/typeform', methods=['POST'])
def typeform_webhook():
    """Receive and store Typeform responses in MongoDB"""
    
    # Get the raw body for signature verification
    request_body = request.get_data()
    signature = request.headers.get('X-Typeform-Signature', '')
    
    # Verify signature
    if signature:
        expected = "sha256=" + hmac.new(
            typeform_secret.encode(),
            request_body,
            hashlib.sha256
        ).hexdigest()
        if signature != expected:
            return jsonify({"error": "Invalid signature"}), 401
    
    try:
        data = request.json
        
        # Extract relevant data from Typeform webhook
        form_response = {
            "response_id": data.get("form_response", {}).get("response_id"),
            "form_id": data.get("form_response", {}).get("form_id"),
            "timestamp": data.get("form_response", {}).get("submitted_at"),
            "answers": data.get("form_response", {}).get("answers", []),
            "respondent_id": data.get("form_response", {}).get("respondent_id"),
            "received_at": datetime.utcnow(),
            "webhook_event": data.get("event_type")
        }
        
        # Insert or update the response
        result = typeform_collection.update_one(
            {"response_id": form_response["response_id"]},
            {"$set": form_response},
            upsert=True
        )
        
        print(f"✓ Typeform response stored: {form_response['response_id']}")
        return jsonify({"success": True, "response_id": form_response["response_id"]}), 200
    
    except Exception as e:
        print(f"✗ Error processing Typeform webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/typeform/responses', methods=['GET'])
def get_typeform_responses():
    """Retrieve all Typeform responses from MongoDB"""
    try:
        responses = list(typeform_collection.find({}, {"_id": 0}))
        return jsonify(responses), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/typeform/responses/<response_id>', methods=['GET'])
def get_response(response_id):
    """Retrieve a specific Typeform response"""
    try:
        response = typeform_collection.find_one({"response_id": response_id}, {"_id": 0})
        if response:
            return jsonify(response), 200
        return jsonify({"error": "Response not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Run on port 5000 - update if needed
    app.run(debug=False, host='0.0.0.0', port=5000)
