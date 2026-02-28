# 🗓️ Voice Booking Agent

AI-powered voice agent for appointment booking over phone calls.

Built for the [AI Tinkerers Nürnberg UnHackathon](https://www.meetup.com/ai-tinkerers-nuremberg/) — Team Nabla.

## 🎯 What It Does

A voice AI agent that handles appointment booking via phone calls:
1. Customer calls in (or agent calls out)
2. Agent greets and asks what they need
3. Checks real-time calendar availability
4. Books the appointment
5. Sends confirmation (SMS/email)

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Voice AI** | [Vapi.ai](https://vapi.ai) — Real-time voice conversations |
| **Calendar** | [Composio](https://composio.dev) — Google Calendar integration |
| **Voice Quality** | [ElevenLabs](https://elevenlabs.io) — Natural TTS |
| **Web App** | Next.js — Dashboard & booking management |
| **LLM** | OpenRouter / GPT — Conversation intelligence |

## 📁 Project Structure

```
voice-booking-agent/
├── README.md
├── app/                    # Next.js web application
│   ├── page.tsx           # Landing page
│   ├── dashboard/         # Booking dashboard
│   └── api/               # API routes
├── agent/                  # Voice agent configuration
│   ├── config.json        # Vapi agent settings
│   ├── prompts/           # System prompts & scripts
│   └── functions/         # Custom tool functions
├── integrations/           # External service connectors
│   ├── composio/          # Calendar integration
│   ├── elevenlabs/        # Voice configuration
│   └── notifications/     # SMS/email confirmations
├── docs/                   # Documentation
│   ├── SETUP.md           # Setup guide
│   ├── ARCHITECTURE.md    # System architecture
│   └── API.md             # API reference
└── .env.example           # Environment variables template
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Vapi.ai account ([free credits with code `Openclaw022026`](https://vapi.ai))
- Composio account ([quickstart](https://docs.composio.dev/docs/quickstart))
- Google Calendar API access

### Setup

```bash
# Clone the repo
git clone https://github.com/sberres/voice-booking-agent.git
cd voice-booking-agent

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run development server
npm run dev
```

## 📋 Environment Variables

```env
# Vapi
VAPI_API_KEY=
VAPI_PHONE_NUMBER=

# Composio
COMPOSIO_API_KEY=

# ElevenLabs
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=

# OpenRouter (LLM)
OPENROUTER_API_KEY=

# Google Calendar
GOOGLE_CALENDAR_ID=
```

## 👥 Team Nabla

- **Estefan** — Lead / Architecture
- **Nishith Kumar Alugandula** — Development

## 📄 License

MIT
