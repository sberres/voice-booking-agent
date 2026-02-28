# Architecture

## Overview

```
┌─────────────┐     ┌──────────┐     ┌───────────────┐
│   Caller     │────▶│  Vapi.ai │────▶│  LLM (GPT/    │
│  (Phone)     │◀────│  Voice   │◀────│  OpenRouter)   │
└─────────────┘     └────┬─────┘     └───────┬───────┘
                         │                    │
                         │  Tool Calls        │
                         ▼                    ▼
                    ┌──────────┐     ┌───────────────┐
                    │ Composio │     │  Web App       │
                    │ Calendar │     │  (Next.js)     │
                    └──────────┘     └───────────────┘
```

## Flow

1. **Inbound Call** → Vapi receives the call via assigned phone number
2. **Voice → Text** → Vapi transcribes speech in real-time
3. **LLM Processing** → Processes intent, generates response
4. **Tool Calls** → When needed, calls Composio to check/book calendar
5. **Text → Voice** → ElevenLabs generates natural speech response
6. **Confirmation** → After booking, triggers notification (SMS/email)

## Web Dashboard

The Next.js app provides:
- View all appointments
- Manual booking interface
- Agent conversation logs
- Configuration panel
