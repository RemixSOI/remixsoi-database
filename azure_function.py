import azure.functions as func
import json
import hmac
import hashlib
import os
from datetime import datetime
from pymongo import MongoClient
import logging

# Get environment variables
MONGODB_URI = os.getenv("MONGODB_URI")
TYPEFORM_SECRET = os.getenv("TYPEFORM_WEBHOOK_SECRET")

# MongoDB setup
if MONGODB_URI:
    client = MongoClient(MONGODB_URI)
    db = client["RemixDB"]
    typeform_collection = db["TypeformResponses"]


def verify_typeform_signature(request_body: bytes, signature_header: str) -> bool:
    """Verify the Typeform webhook signature"""
    expected = "sha256=" + hmac.new(
        TYPEFORM_SECRET.encode(),
        request_body,
        hashlib.sha256
    ).hexdigest()
    return signature_header == expected


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to receive and store Typeform responses in MongoDB
    
    Trigger: HTTP POST to the function URL
    Input: Typeform webhook payload
    Output: Stored in MongoDB TypeformResponses collection
    """
    
    logging.info("Typeform webhook received")
    
    try:
        # Get the raw body for signature verification
        request_body = req.get_body()
        signature = req.headers.get('X-Typeform-Signature', '')
        
        # Verify signature if secret is configured
        if TYPEFORM_SECRET and signature:
            if not verify_typeform_signature(request_body, signature):
                logging.warning("Invalid Typeform signature")
                return func.HttpResponse(
                    json.dumps({"error": "Invalid signature"}),
                    status_code=401,
                    mimetype="application/json"
                )
        
        # Parse the JSON payload
        data = req.json
        
        # Extract Typeform data
        form_response_data = data.get("form_response", {})
        
        form_response = {
            "response_id": form_response_data.get("response_id"),
            "form_id": form_response_data.get("form_id"),
            "timestamp": form_response_data.get("submitted_at"),
            "answers": form_response_data.get("answers", []),
            "respondent_id": form_response_data.get("respondent_id"),
            "received_at": datetime.utcnow().isoformat(),
            "webhook_event": data.get("event_type"),
            "landing_id": form_response_data.get("landing_id"),
            "token": form_response_data.get("token")
        }
        
        # Store in MongoDB
        if typeform_collection:
            result = typeform_collection.update_one(
                {"response_id": form_response["response_id"]},
                {"$set": form_response},
                upsert=True
            )
            logging.info(f"Stored response: {form_response['response_id']}")
        else:
            logging.warning("MongoDB not configured, response not stored")
        
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "response_id": form_response["response_id"],
                "message": "Response stored successfully"
            }),
            status_code=200,
            mimetype="application/json"
        )
    
    except Exception as e:
        logging.error(f"Error processing Typeform webhook: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
