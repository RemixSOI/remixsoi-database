# Azure Functions Typeform Integration Setup

## Option 1: Local Testing (Undeployed) ✅ START HERE

For immediate testing WITHOUT deploying to Azure:

```bash
python local_azure_function.py
```

The function will run on `http://localhost:7071/api/typeform`

### Testing With ngrok (Tunnel to Typeform):

```bash
# In another terminal
ngrok http 7071
```

Use the ngrok URL + `/api/typeform` as your Typeform webhook:
```
https://xxxx-xx-xxx-xx-xxxxx.ngrok.io/api/typeform
```

---

## Option 2: Deploy to Azure

### Prerequisites

1. **Azure Account**: https://azure.microsoft.com/free/
2. **Azure CLI**: Download from https://docs.microsoft.com/cli/azure/install-azure-cli
3. **Azure Functions Core Tools**: 
   ```bash
   npm install -g azure-functions-core-tools@4 --unsafe-perm true
   ```

### Setup Steps

#### 1. Create Azure Resources

```bash
# Login to Azure
az login

# Create Resource Group
az group create --name RemixDataBase --location eastus

# Create Storage Account (required for Functions)
az storage account create \
  --name remixdatabasestorage \
  --resource-group RemixDataBase \
  --location eastus \
  --sku Standard_LRS

# Create Function App
az functionapp create \
  --resource-group RemixDataBase \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --name RemixTypeformFunction \
  --storage-account remixdatabasestorage
```

#### 2. Configure Environment Variables

Add these to your Function App settings:

```bash
az functionapp config appsettings set \
  --name RemixTypeformFunction \
  --resource-group RemixDataBase \
  --settings \
    MONGODB_URI="your_mongodb_uri" \
    TYPEFORM_WEBHOOK_SECRET="your_webhook_secret"
```

#### 3. Deploy the Function

```bash
func azure functionapp publish RemixTypeformFunction
```

#### 4. Get Your Webhook URL

After deployment, your webhook URL will be:
```
https://RemixTypeformFunction.azurewebsites.net/api/typeform
```

Add this to your Typeform webhook settings.

---

## Project Structure

For Azure deployment, organize your files as:

```
RemixDataBase/
├── azure_function.py      (main function code)
├── function.json          (Azure trigger config)
├── requirements.txt       (dependencies)
├── local_azure_function.py (local testing)
└── test_webhook.py        (testing script)
```

---

## Environment Variables

Required in `.env` or Azure Function Settings:

```
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
TYPEFORM_FORM_ID=your_form_id
TYPEFORM_WEBHOOK_SECRET=your_webhook_secret
TYPEFORM_API_TOKEN=your_api_token  # Optional
```

---

## Testing Workflow

### Using Local Azure Function Emulator:

1. **Start local function**:
   ```bash
   python local_azure_function.py
   ```

2. **In another terminal, test it**:
   ```bash
   python test_webhook.py
   ```
   
   (Modify `WEBHOOK_URL` in test_webhook.py to: `http://localhost:7071/api/typeform`)

### Using ngrok for real Typeform testing:

1. **Start local function**:
   ```bash
   python local_azure_function.py
   ```

2. **Tunnel with ngrok**:
   ```bash
   ngrok http 7071
   ```

3. **Use ngrok URL in Typeform**:
   - Go to Typeform Settings → Webhooks
   - Add: `https://xxxx-xx-xxx-xx-xxxxx.ngrok.io/api/typeform`

---

## API Reference

### Webhook Endpoint (HTTP POST)

**URL**: `https://RemixTypeformFunction.azurewebsites.net/api/typeform`

**Headers**:
- `X-Typeform-Signature`: SHA256 signature for verification
- `Content-Type`: application/json

**Body** (Typeform sends this):
```json
{
  "event_id": "event_id",
  "event_type": "form_response",
  "form_response": {
    "form_id": "form_id",
    "response_id": "response_id",
    "submitted_at": "2024-01-15T10:30:00Z",
    "respondent_id": "respondent_id",
    "answers": [
      {
        "type": "text",
        "text": "answer",
        "field": {"id": "field_id", "type": "short_text"}
      }
    ]
  }
}
```

**Response**:
```json
{
  "success": true,
  "response_id": "response_id",
  "message": "Response stored successfully"
}
```

---

## MongoDB Collection

Data stored in: `RemixDB.TypeformResponses`

```json
{
  "_id": ObjectId(...),
  "response_id": "unique_id",
  "form_id": "form_id",
  "timestamp": "2024-01-15T10:30:00Z",
  "respondent_id": "respondent_id",
  "answers": [...],
  "received_at": "2024-01-15T10:30:05Z",
  "webhook_event": "form_response"
}
```

---

## Troubleshooting

### "Invalid signature" error
- Verify `TYPEFORM_WEBHOOK_SECRET` matches Typeform dashboard
- Check that the secret is set in Azure Function Settings

### MongoDB connection errors
- Ensure `MONGODB_URI` is correct in Function Settings
- Check that your MongoDB cluster allows connections from Azure IPs

### Function not receiving webhooks
- Verify webhook URL is correct in Typeform dashboard
- Check Azure Function logs: `az functionapp logs tail --name RemixTypeformFunction --resource-group RemixDataBase`

### Local function not connecting to MongoDB
- Ensure `.env` file has `MONGODB_URI`
- Test MongoDB connection separately

---

## Cost Considerations

Azure Functions Consumption Plan pricing:
- **Free tier**: 1M executions/month + 400,000 GB-seconds/month
- Typical Typeform webhook: ~50-100ms execution time
- Most use cases stay within free tier

See: https://azure.microsoft.com/pricing/details/functions/
