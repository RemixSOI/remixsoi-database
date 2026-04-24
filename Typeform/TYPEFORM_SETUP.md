# Typeform MongoDB Integration Setup

## Required Environment Variables

Add these to your `.env` file:

```
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
TYPEFORM_FORM_ID=your_form_id_here
TYPEFORM_WEBHOOK_SECRET=your_webhook_secret_here
TYPEFORM_API_TOKEN=your_api_token_here  # Optional: for API polling
```

## Installation

```bash
pip install flask pymongo python-dotenv requests
```

## Running the Webhook Server

```bash
python typeform_handler.py
```

The server will run on `http://0.0.0.0:5000`

## Webhook URL Configuration

After starting the server, configure this URL in Typeform:

### Local Development (using ngrok for tunneling):

1. **Install ngrok**: https://ngrok.com/download

2. **Run ngrok to expose your local server**:
   ```bash
   ngrok http 5000
   ```
   This will give you a URL like: `https://xxxxx-xx-xxx-xx-xxxxx.ngrok.io`

3. **Your Typeform Webhook URL**:
   ```
   https://xxxxx-xx-xxx-xx-xxxxx.ngrok.io/webhook/typeform
   ```

### Production (with your own domain):
```
https://yourdomain.com/webhook/typeform
```

## Setting Up Webhook in Typeform

1. Go to your Typeform dashboard
2. Select your form → **Settings** → **Webhooks**
3. Click **Add webhook**
4. Paste your webhook URL (from above)
5. Copy the **Webhook Sign Secret** that Typeform provides
6. Add this secret to your `.env` file as `TYPEFORM_WEBHOOK_SECRET`

## MongoDB Collection Structure

Data will be stored in the `RemixDB` database under the `TypeformResponses` collection:

```json
{
  "response_id": "unique_response_id",
  "form_id": "your_form_id",
  "timestamp": "2024-01-15T10:30:00Z",
  "respondent_id": "respondent_id",
  "answers": [
    {
      "type": "text",
      "text": "answer content",
      "field": {
        "id": "field_id",
        "type": "short_text"
      }
    }
  ],
  "received_at": "2024-01-15T10:30:05Z",
  "webhook_event": "form_response"
}
```

## API Endpoints

### Get All Responses
```
GET http://localhost:5000/typeform/responses
```

### Get Specific Response
```
GET http://localhost:5000/typeform/responses/{response_id}
```

### Webhook Endpoint (Typeform sends here)
```
POST http://localhost:5000/webhook/typeform
```

## Testing

Use the `test_webhook.py` script to send test data:

```bash
python test_webhook.py
```

## Connecting to Different Database

To use a separate database for Typeform data, update line 25 in `typeform_handler.py`:

```python
db = client["YourDatabaseName"]  # Change "RemixDB" to your database name
```
