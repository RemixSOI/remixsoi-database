"""
Local Azure Function Emulator for Typeform Webhook Testing
This mimics the Azure Function behavior locally without deployment
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import hmac
import hashlib
import os
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import threading

load_dotenv()

# Configuration
MONGODB_URI = os.getenv("MONGODB_URI")
TYPEFORM_SECRET = os.getenv("TYPEFORM_WEBHOOK_SECRET", "")
PORT = 7071  # Azure Functions local port

# MongoDB setup
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


class AzureFunctionHandler(BaseHTTPRequestHandler):
    """HTTP handler mimicking Azure Function behavior"""
    
    def do_POST(self):
        """Handle POST requests"""
        
        # Check if this is the typeform endpoint
        if self.path != "/api/typeform":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
            return
        
        try:
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            request_body = self.rfile.read(content_length)
            
            # Get signature
            signature = self.headers.get('X-Typeform-Signature', '')
            
            # Verify signature if secret is set
            if TYPEFORM_SECRET and signature:
                if not verify_typeform_signature(request_body, signature):
                    print("❌ Invalid signature")
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Invalid signature"}).encode())
                    return
            
            # Parse JSON
            data = json.loads(request_body.decode('utf-8'))
            form_response_data = data.get("form_response", {})
            
            # Create document
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
            result = typeform_collection.update_one(
                {"response_id": form_response["response_id"]},
                {"$set": form_response},
                upsert=True
            )
            
            print(f"✓ Response stored: {form_response['response_id']}")
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                "success": True,
                "response_id": form_response["response_id"],
                "message": "Response stored successfully"
            }
            self.wfile.write(json.dumps(response).encode())
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        return


def run_local_function():
    """Start the local Azure Function emulator"""
    server = HTTPServer(('0.0.0.0', PORT), AzureFunctionHandler)
    print(f"🔷 Azure Function Emulator running on http://localhost:{PORT}")
    print(f"📍 Webhook URL: http://localhost:{PORT}/api/typeform")
    print(f"\nFor testing with ngrok:")
    print(f"  ngrok http {PORT}")
    print(f"  Then use the ngrok URL + /api/typeform")
    print(f"\nPress Ctrl+C to stop\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        server.shutdown()


if __name__ == '__main__':
    run_local_function()
