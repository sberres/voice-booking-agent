# Setup Guide

## 1. Run the Backend

```bash
cd server
pip install -r requirements.txt
python app.py
```

Server starts on `http://localhost:3020`

## 2. Open the Dashboard

Go to `http://localhost:3020` — you'll see the booking dashboard.

## 3. Connect to Vapi

1. Go to [Vapi Dashboard](https://dashboard.vapi.ai)
2. Create a new Assistant
3. Copy the system prompt from `agent/config.json` → model.messages
4. Add the 3 functions from `agent/config.json` → functions
5. Set **Server URL** to your public server URL + `/vapi/webhook`
   - For local dev: use [ngrok](https://ngrok.com) → `ngrok http 3020`
   - For production: deploy to your server
6. Assign a phone number to the assistant

## 4. Test

- Call the assigned phone number
- Or use Vapi's web widget to test in browser
- Check the dashboard for booked appointments

## 5. Expose Server (for Vapi webhook)

Vapi needs to reach your server. Options:

### Option A: ngrok (local dev)
```bash
ngrok http 3020
```
Copy the `https://xxx.ngrok.io` URL → set as Server URL in Vapi.

### Option B: Deploy on server
```bash
# On your server
cd voice-booking-agent/server
pip install -r requirements.txt
PORT=3020 python app.py
```
Set Server URL to `https://your-server:3020/vapi/webhook`
