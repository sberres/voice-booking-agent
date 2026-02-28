# 🗓️ Voice Booking Agent

AI-powered voice agent for appointment booking over phone calls — with real Google Calendar integration.

Built for the [AI Tinkerers Nürnberg UnHackathon](https://www.meetup.com/ai-tinkerers-nuremberg/) — **Team Nabla**.

## 🎯 What It Does

A voice AI agent that handles appointment booking via phone calls:
1. Customer calls in (or uses web widget)
2. Agent greets and asks what they need
3. Checks **real-time Google Calendar** availability
4. Books the appointment directly on Google Calendar
5. Confirms the booking with date, time, and purpose

## 🎬 Demo

Voice call → checks availability → books on Google Calendar → confirmation:

> *"Thank you for calling Wellness Partners. This is Riley, your scheduling assistant. How may I help you today?"*

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Voice AI** | [Vapi.ai](https://vapi.ai) — Real-time voice conversations |
| **LLM** | OpenAI GPT-4o-mini — Conversation intelligence |
| **Calendar** | Google Calendar API — Real-time availability & booking |
| **Backend** | Python Flask — Webhook handler & REST API |
| **Database** | SQLite (fallback) + Google Calendar (primary) |
| **TLS Tunnel** | Cloudflare Tunnel — HTTPS for Vapi webhooks |
| **Web Dashboard** | Vanilla HTML/JS — Manual booking & appointment view |

## 📁 Project Structure

```
voice-booking-agent/
├── README.md
├── .env.example            # Environment variables template
├── .gitignore
├── server/
│   ├── app.py              # Flask server — Vapi webhook + REST API
│   ├── google_calendar.py  # Google Calendar integration
│   ├── requirements.txt    # Python dependencies
│   └── bookings.db         # SQLite fallback database
├── agent/
│   ├── config.json         # Vapi assistant configuration
│   └── prompts/
│       └── system.md       # Voice agent system prompt
├── web/
│   └── index.html          # Booking dashboard UI
└── docs/
    ├── SETUP.md            # Setup guide
    └── ARCHITECTURE.md     # System architecture
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- [Vapi.ai](https://vapi.ai) account (free credits with code `Openclaw022026`)
- Google Cloud project with Calendar API enabled
- Google Calendar shared with service account

### 1. Clone & Install

```bash
git clone https://github.com/sberres/voice-booking-agent.git
cd voice-booking-agent/server
pip install -r requirements.txt
```

### 2. Configure Google Calendar

1. Create a **Service Account** in [Google Cloud Console](https://console.cloud.google.com)
2. Download the JSON key file → save as `server/google-credentials.json`
3. Share your Google Calendar with the service account email
4. Set permission to **Make changes to events**

### 3. Run the Server

```bash
cd server
python3 app.py
```

Server starts on `http://localhost:3020`

### 4. Expose with HTTPS (for Vapi)

```bash
# Option A: Cloudflare Tunnel (recommended)
cloudflared tunnel --url http://localhost:3020

# Option B: ngrok
ngrok http 3020
```

### 5. Configure Vapi

1. Go to [Vapi Dashboard](https://dashboard.vapi.ai) → **Tools**
2. Create 3 tools (type: Function):

**Tool 1: `check_availability`**
- Description: Check available appointment slots for a given date
- Server URL: `https://your-tunnel-url.com/vapi/webhook`
- Parameters: `date` (string, required)

**Tool 2: `book_appointment`**
- Description: Book an appointment for a caller
- Server URL: `https://your-tunnel-url.com/vapi/webhook`
- Parameters: `name` (string, required), `date` (string, required), `time` (string, required), `purpose` (string, optional)

**Tool 3: `cancel_appointment`**
- Description: Cancel an existing appointment
- Server URL: `https://your-tunnel-url.com/vapi/webhook`
- Parameters: `name` (string, required), `date` (string, required)

3. Create an **Assistant** → add the 3 tools → set system prompt from `agent/config.json`

### 6. Test

- Use the Vapi web widget to make a test call
- Or assign a phone number and call it
- Check your Google Calendar for booked appointments!

## 🌐 Web Dashboard

Open `http://localhost:3020` for the booking dashboard:
- View available time slots
- Book appointments manually
- See upcoming appointments
- Cancel bookings

## 📋 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/slots/<date>` | Available slots for a date |
| `GET` | `/api/appointments` | List all appointments |
| `POST` | `/api/appointments` | Create appointment |
| `DELETE` | `/api/appointments/<id>` | Cancel appointment |
| `POST` | `/vapi/webhook` | Vapi webhook handler |

## 🔧 Features

- **Flexible date parsing** — understands "Monday", "tomorrow", "next Friday", "March 1st"
- **Dual calendar support** — Google Calendar primary, SQLite fallback
- **Timezone-aware** — configurable via `CALENDAR_TIMEZONE` env var
- **30-minute slots** — business hours 9 AM – 5 PM (configurable)
- **Real-time sync** — reads and writes directly to Google Calendar
- **Supports both Vapi webhook formats** — `function-call` and `tool-calls`

## 📋 Environment Variables

```env
# Server
PORT=3020

# Google Calendar
GOOGLE_CALENDAR_ID=your-email@gmail.com
CALENDAR_TIMEZONE=Europe/Berlin

# Vapi (for API-based setup)
VAPI_API_KEY=

# Optional
PYTHONUNBUFFERED=1
```

## 👥 Team Nabla

- **Estefan** — Lead / Architecture / Infrastructure
- **Nishith Kumar Alugandula** — Development / Vapi Setup

## 🏆 Hackathon

- **Event:** AI Tinkerers Nürnberg UnHackathon
- **Date:** February 28, 2026
- **Sponsors:** Vapi, OpenRouter, Composio, ElevenLabs, Auth0

## 📄 License

MIT
