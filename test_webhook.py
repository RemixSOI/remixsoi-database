import requests
import json
import hmac
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

# Test webhook - choose one:
# For Flask server:          http://localhost:5000/webhook/typeform
# For Azure Function local:  http://localhost:7071/api/typeform
# For deployed Azure:        https://RemixTypeformFunction.azurewebsites.net/api/typeform
WEBHOOK_URL = "http://localhost:7071/api/typeform"  # Azure Function local version
TYPEFORM_SECRET = os.getenv("TYPEFORM_WEBHOOK_SECRET", "your_secret_here")

# Sample Typeform webhook payload
test_payload = {
    "event_id": "00000000-0000-0000-0000-000000000000",
    "event_type": "form_response",
    "form_response": {
        "form_id": "abc123",
        "response_id": "test_response_001",
        "submitted_at": "2024-01-15T10:30:00Z",
        "respondent_id": "respondent_123",
        "answers": [
            {
                "type": "text",
                "text": "Test Answer",
                "field": {
                    "id": "field_1",
                    "type": "short_text",
                    "title": "What is your name?"
                }
            },
            {
                "type": "email",
                "email": "test@example.com",
                "field": {
                    "id": "field_2",
                    "type": "email",
                    "title": "What is your email?"
                }
            }
        ]
    }
}

# Convert payload to JSON bytes
payload_bytes = json.dumps(test_payload).encode('utf-8')

# Create signature
signature = "sha256=" + hmac.new(
    TYPEFORM_SECRET.encode(),
    payload_bytes,
    hashlib.sha256
).hexdigest()

# Send test webhook
headers = {
    "X-Typeform-Signature": signature,
    "Content-Type": "application/json"
}

print("Sending test webhook...")
print(f"Payload: {json.dumps(test_payload, indent=2)}")
print(f"Signature: {signature}")

try:
    response = requests.post(WEBHOOK_URL, json=test_payload, headers=headers)
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
