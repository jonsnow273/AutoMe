# CLAUDE.md — AutoMe Project Context

## Project Overview

**AutoMe** is a full-stack multi-user AI platform that learns how users text and automatically replies to their WhatsApp, Instagram, and Discord messages when they are busy — responding exactly the way they would.

**Current Phase:** Phase 2 (Discord Connector + Unified Inbox UI) — See [ROADMAP.md](ROADMAP.md) for full plan.

---

## Architecture Summary

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

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + Vite, TailwindCSS, Socket.IO, React Query, React Router |
| Backend | Python FastAPI, SQLAlchemy, SQLite, JWT (python-jose), bcrypt, Fernet |
| AI | Groq API (LLaMA 3.1 70B) |
| WhatsApp | whatsapp-web.js (Node.js microservice) |
| Instagram | instagrapi (Python) |
| Discord | discord.py (Python) |

---

## Key Project Structure

```
autome/
├── backend/
│   ├── auth/           # JWT, bcrypt, login/signup routes
│   ├── ai/             # Groq client, reply generator, style learner, classifier, mood detector, prompts
│   ├── connectors/     # WhatsApp, Instagram, Discord, session manager
│   ├── models/         # SQLAlchemy DB models (all user-scoped)
│   ├── api/            # REST endpoints
│   ├── integrations/   # Google Calendar
│   ├── utils/          # Encryption, push notifications
│   ├── main.py         # FastAPI app entry
│   └── database.py     # DB engine + session
│
├── whatsapp-service/   # Node.js microservice (whatsapp-web.js)
│   ├── sessions/       # Per-user WA session data (gitignored)
│   ├── index.js
│   └── qr.js
│
└── frontend/
    └── src/
        ├── pages/      # Login, Signup, Inbox, Conversation, Analytics, ConnectPlatforms, Settings
        ├── components/ # MessageBubble, SuggestedReply, BusyToggle, MoodBadge, EmergencyAlert, QRScanner, PlatformCard, PlatformBadge, Sidebar
        ├── context/    # AuthContext
        ├── hooks/      # useAuth, useSocket, useMessages
        └── utils/      # api.js, formatTime, constants
```

---

## Development Commands

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### WhatsApp Service (Node.js)
```bash
cd whatsapp-service
npm install
node index.js
# Runs on port 3001 (configurable)
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173
```

### Run All (3 terminals)
```bash
# Terminal 1
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2
cd whatsapp-service && node index.js

# Terminal 3
cd frontend && npm run dev
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
# Backend
SECRET_KEY=your-super-secret-jwt-key-min-32-chars
DATABASE_URL=sqlite:///./autome.db
GROQ_API_KEY=your-groq-api-key
FRONTEND_URL=http://localhost:5173

# Discord (per-user, stored in DB after connect)
DISCORD_BOT_TOKEN=your-discord-bot-token  # For testing only

# Google Calendar (Phase 7)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/calendar/callback

# WhatsApp Service
WHATSAPP_SERVICE_URL=http://localhost:3001
```

---

## Current Implementation Status

### ✅ Completed (Phase 1)
- **Backend Auth**: FastAPI routes for signup, login, get current user
- **Database**: SQLite + SQLAlchemy, User model with bcrypt passwords
- **JWT**: 7-day expiry tokens, HS256 algorithm
- **Frontend Auth**: Login/Signup pages, AuthContext with localStorage persistence, Protected/Public route guards, Axios interceptors

### 🚧 In Progress (Phase 2)
- Discord connector (empty file)
- Message/Contact/Platform models (empty)
- Inbox UI (placeholder only)
- Real-time WebSocket setup (not started)

### ❌ Not Started (Phases 3-9)
See [ROADMAP.md](ROADMAP.md) for detailed breakdown.

---

## Code Conventions

### Backend (Python)
- **Style**: PEP 8, type hints on all functions
- **Architecture**: Clean separation — routes → services → models
- **Database**: All queries scoped to `user_id` (multi-tenant safety)
- **Security**: Fernet encryption for platform credentials, never log secrets
- **Error Handling**: HTTPException with appropriate status codes, structured error responses

### Frontend (React)
- **Style**: Functional components, hooks, ES6+
- **Styling**: TailwindCSS utility classes, dark theme (dark-900 background, accent-500 primary)
- **State**: React Query for server state, Context for auth, local state for UI
- **Real-time**: Socket.IO client, custom hooks for connection management
- **Routing**: React Router v6, protected routes via wrapper components

### Database (SQLAlchemy)
- All models inherit from `Base` in `database.py`
- Every model has `user_id` foreign key (except User)
- Use `server_default=func.now()` for timestamps
- Indexes on frequently queried columns (user_id, platform, timestamps)

---

## Security Requirements

1. **Passwords**: bcrypt via passlib — never plain text
2. **Platform Credentials**: Fernet encryption before DB storage
3. **JWT**: 7-day expiry, HS256, secret from env
4. **Data Isolation**: Every query filtered by `user_id`
5. **WhatsApp Sessions**: Stored locally in Node service, never transmitted
6. **CORS**: Restricted to FRONTEND_URL only

---

## AI Engine Design (Phase 5+)

### Groq Client
- Single wrapper class for all Groq API calls
- Model: `llama-3.1-70b-versatile` (or configured via env)
- Retry logic with exponential backoff
- Token usage tracking

### Style Profile (per user)
```python
class StyleProfile:
    avg_length: int
    emoji_frequency: float
    preferred_emojis: List[str]
    common_phrases: List[str]
    tone: Literal["formal", "casual", "playful"]
    opener_patterns: List[str]
    closer_patterns: List[str]
    formality_score: float  # 0-1
```

### Reply Generation Pipeline
```
Incoming Message
       │
       ▼
Relationship Classification (Friend/Acquaintance/Stranger)
       │
       ▼
Mood Detection (Positive/Neutral/Negative/Urgent)
       │
       ▼
Urgency Scoring (Low/Medium/High/Emergency)
       │
       ▼
Emergency? ──Yes──► Notify User, STOP
       │
       No
       ▼
Calendar Check (if availability question)
       │
       ▼
Style Profile Applied
       │
       ▼
Generate Reply (Groq)
       │
       ▼
Low Urgency + Friend? ──Yes──► Auto-Send
       │
       No ──► Suggest in Dashboard
```

---

## Platform Connector Patterns

### Discord (Phase 2)
- One `discord.Client` instance per user
- Token stored encrypted in DB
- WebSocket events forwarded to FastAPI via HTTP callback or shared Redis
- Message persistence → `Message` model

### WhatsApp (Phase 3)
- Separate Node.js process per user (or pooled)
- `whatsapp-web.js` with LocalAuth (file-based session)
- QR code served via HTTP endpoint → frontend polls
- Messages forwarded to FastAPI REST endpoint

### Instagram (Phase 4)
- `instagrapi.Client` per user
- Username/password encrypted in DB
- Challenge/2FA handling
- DM polling (no webhook support)

---

## Frontend Component Patterns

### Page Components
- Located in `src/pages/`
- Use hooks for data fetching (`useMessages`, `useAuth`)
- Compose UI from `src/components/`

### Reusable Components
- Located in `src/components/`
- Pure presentational where possible
- Accept props, emit callbacks
- Tailwind for styling

### Hooks
- Located in `src/hooks/`
- `useAuth` — auth state + login/logout
- `useSocket` — Socket.IO connection + events
- `useMessages` — message/contact data + mutations

---

## Testing Strategy

### Backend
- `pytest` with `httpx.AsyncClient` for API tests
- Unit tests for AI modules (mock Groq)
- Integration tests for auth + platform flows
- Database: use SQLite `:memory:` for tests

### Frontend
- `vitest` + React Testing Library
- Component tests for critical UI
- Mock API with MSW

### E2E
- Playwright for critical user journeys
- Auth flow, platform connect, message send/receive

---

## Common Tasks for Claude

When working on this project, you may be asked to:

1. **Implement a connector** — Follow the pattern: model → service → API route → frontend UI
2. **Add AI functionality** — Extend `groq_client.py`, add prompt in `prompts.py`, wire into pipeline
3. **Build frontend pages** — Create page component, add route in `App.jsx`, compose from existing components
4. **Add database models** — Create model in `models/`, add to `__init__.py`, create migration (or recreate tables)
5. **Debug real-time issues** — Check Socket.IO connection, event names, CORS, JWT in handshake
6. **Handle encryption** — Use `cryptography.fernet.Fernet` with key from `SECRET_KEY` derivative

---

## Key Files to Reference

| Purpose | File |
|---------|------|
| App entry | `backend/main.py` |
| DB setup | `backend/database.py` |
| User model | `backend/models/user.py` |
| Auth routes | `backend/auth/router.py` |
| JWT handling | `backend/auth/jwt_handler.py` |
| Password hashing | `backend/auth/hashing.py` |
| Frontend app | `frontend/src/App.jsx` |
| Auth context | `frontend/src/context/AuthContext.jsx` |
| API client | `frontend/src/utils/api.js` |
| Roadmap | `ROADMAP.md` |

---

## Notes for Future Sessions

- **Phase 1 is complete** — Auth works end-to-end
- **Start Phase 2** by implementing Discord connector and Message/Contact models
- **Database recreation**: `Base.metadata.create_all(bind=engine)` runs on startup — models auto-create tables
- **Frontend dev server** proxies to `localhost:8000` — ensure backend runs first
- **WhatsApp service** is separate Node process — communicate via HTTP
- **All user data isolated** by `user_id` — never forget this filter

---

*Generated for AutoMe project — update as project evolves*