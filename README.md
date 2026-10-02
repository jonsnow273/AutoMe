<div align="center">

# AutoMe

### AI-Powered Social Proxy — Never Leave Anyone on Read Again

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.1-F55036?style=for-the-badge)](https://console.groq.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**AutoMe** is a full-stack multi-user AI platform that learns how you text and automatically replies to your WhatsApp, Instagram, and Discord messages when you are busy — responding exactly the way you would.

[Features](#-features) · [Tech Stack](#-tech-stack) · [Architecture](#-architecture) · [Setup](#-setup)

</div>

---

## The Problem

You are in a meeting, studying, or just need a break — but your phone keeps blowing up. People expect replies. Important messages get buried. You miss things that matter.

**AutoMe fixes that.**

It watches your messages, figures out who is texting and why, and replies the way *you* would — using AI trained on your own writing style.

---

## Features

| Feature | Description |
|---|---|
| Unified Inbox | All WhatsApp, Instagram and Discord messages in one clean dashboard |
| Style Learner | AI learns your vocabulary, tone, emoji use, and slang — replies sound like *you* |
| Relationship Classifier | Auto-labels every contact as Friend, Acquaintance, or Stranger based on chat history |
| Smart Auto-Reply | Auto-sends casual replies to friends, suggests replies for anything important |
| Mood Detector | Reads the sender emotional tone and adjusts reply warmth accordingly |
| Emergency Bypass | One mention of urgent or emergency triggers instant notification, no auto-reply |
| Calendar-Aware Replies | Checks your Google Calendar before replying to "are you free?" |
| Analytics Dashboard | Message volume, mood trends, activity heatmap, top senders — all in one view |
| Multi-User | Anyone can sign up, connect their own accounts, and use AutoMe independently |
| Secure by Design | JWT auth, bcrypt passwords, Fernet-encrypted platform credentials |

---

## Tech Stack

### Frontend
- **React 18 + Vite** — fast, modern UI
- **TailwindCSS** — clean styling
- **Socket.IO** — real-time message updates
- **React Query + React Router** — state management and routing

### Backend
- **Python FastAPI** — REST API + WebSocket server
- **SQLite + SQLAlchemy** — lightweight local database
- **JWT (python-jose) + bcrypt** — authentication
- **Fernet (cryptography)** — encrypted credential storage

### AI Engine
- **Groq API** (LLaMA 3.1 70B) — reply generation, style learning, mood detection, urgency classification

### Platform Connectors

| Platform | Library | Method |
|---|---|---|
| WhatsApp | whatsapp-web.js (Node.js) | QR code scan — no API key needed |
| Instagram | instagrapi (Python) | Username + password — no API key needed |
| Discord | discord.py (Python) | Bot token per user |

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│               React Dashboard (Vite)                 │
│   Login · Signup · Inbox · Analytics · Settings      │
└──────────────────────┬───────────────────────────────┘
                       │ HTTP + WebSocket (JWT)
┌──────────────────────▼───────────────────────────────┐
│              Python FastAPI Backend                   │
│                                                       │
│   Auth System    AI Engine (Groq)   Session Manager  │
│   Style Learner  Mood Detector      Analytics Engine  │
│                                                       │
│              SQLite (per-user scoped)                 │
└─────────┬──────────────┬──────────────┬──────────────┘
          │              │              │
   WhatsApp (Node)   Instagram      Discord
   QR per user       per-user       per-user bot token
```

---

## Project Structure

```
autome/
├── backend/
│   ├── auth/           # JWT, bcrypt, login/signup routes
│   ├── ai/             # Groq client, reply generator, style learner,
│   │                   # classifier, mood detector, prompts
│   ├── connectors/     # WhatsApp, Instagram, Discord, session manager
│   ├── models/         # SQLAlchemy DB models (all user-scoped)
│   ├── api/            # REST endpoints
│   ├── integrations/   # Google Calendar
│   ├── utils/          # Encryption, push notifications
│   ├── main.py
│   └── database.py
│
├── whatsapp-service/   # Node.js microservice (whatsapp-web.js)
│   ├── sessions/       # Per-user WA session data (gitignored)
│   ├── index.js
│   └── qr.js
│
└── frontend/
    └── src/
        ├── pages/      # Login, Signup, Inbox, Conversation,
        │               # Analytics, ConnectPlatforms, Settings
        ├── components/ # MessageBubble, SuggestedReply, BusyToggle,
        │               # MoodBadge, EmergencyAlert, QRScanner, etc.
        ├── context/    # AuthContext
        ├── hooks/      # useAuth, useSocket, useMessages
        └── utils/      # api.js, formatTime, constants
```

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Groq API key (free at [console.groq.com](https://console.groq.com))
- Discord bot token (free at [discord.com/developers](https://discord.com/developers))

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/autome.git
cd autome
```

### 2. Set up environment variables
```bash
cp .env.example .env
# Fill in GROQ_API_KEY, DISCORD_BOT_TOKEN, and SECRET_KEY
```

### 3. Install backend dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 4. Install WhatsApp service dependencies
```bash
cd ../whatsapp-service
npm install
```

### 5. Install frontend dependencies
```bash
cd ../frontend
npm install
```

### 6. Run all services

**Terminal 1 — Backend:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 — WhatsApp Service:**
```bash
cd whatsapp-service
node index.js
```

**Terminal 3 — Frontend:**
```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) → Sign up → Connect your accounts → Toggle **Busy Mode** → Done.

---

## How It Works

### When a message arrives:
```
Incoming message
      │
Is user in Busy Mode?
      │
   Yes ──► Emergency detected?
      │           │
      │        Yes ──► Notify user immediately, pause AutoMe
      │           │
      │        No  ──► Detect mood + classify relationship + score urgency
      │                         │
      │         Low urgency + friend ──► Auto-reply in user style
      │                         │
      │                    Otherwise ──► Suggest reply in dashboard
      │
     No ──► Show message in inbox, no action
```

### Style Learning
AutoMe analyzes your past messages to build a Style Profile:
- Average message length
- Emoji frequency and preferred emojis
- Common slang and phrases
- Tone (formal / casual / playful)
- How you open and close conversations

Every generated reply uses this profile so it sounds like you, not a bot.

---

## Security

- Passwords hashed with **bcrypt** — never stored in plain text
- Instagram passwords and Discord tokens encrypted with **Fernet** before DB storage
- JWT tokens expire after 7 days
- All DB queries scoped to `user_id` — users can never access each other's data
- WhatsApp sessions stored locally, never transmitted

---

## Roadmap

- [x] Project architecture and structure
- [ ] Phase 1 — Auth system (signup/login)
- [ ] Phase 2 — Discord connector + unified inbox UI
- [ ] Phase 3 — WhatsApp service + QR code flow
- [ ] Phase 4 — Instagram connector
- [ ] Phase 5 — AI engine (Groq) — style learner + reply generator
- [ ] Phase 6 — Mood detector + Emergency bypass
- [ ] Phase 7 — Context-Aware Replies (Google Calendar)
- [ ] Phase 8 — Analytics Dashboard
- [ ] Phase 9 — Polish and deploy

---

## License

MIT License — feel free to use, modify, and build on this.
