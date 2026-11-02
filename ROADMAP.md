# AutoMe Project Roadmap

**Status:** Phase 1 Complete (Auth System) | Phase 2 In Progress (Discord Connector + Unified Inbox UI)

---

## Project Overview

AutoMe is a full-stack multi-user AI platform that learns how users text and automatically replies to their WhatsApp, Instagram, and Discord messages when they are busy — responding exactly the way they would.

---

## Current State Assessment

| Component | Status | Notes |
|-----------|--------|-------|
| **Backend Auth System** | ✅ Complete | JWT + bcrypt, signup/login/me endpoints |
| **Backend Database** | ✅ Complete | SQLite + SQLAlchemy, User model |
| **Frontend Auth (Login/Signup)** | ✅ Complete | React + React Router + AuthContext |
| **Frontend Inbox (Placeholder)** | 🚧 Partial | Basic auth verification page only |
| **WhatsApp Service** | ❌ Not Started | Node.js service structure exists (empty) |
| **Discord Connector** | ❌ Not Started | Empty file exists |
| **Instagram Connector** | ❌ Not Started | Empty file exists |
| **AI Engine (Groq)** | ❌ Not Started | Empty files exist |
| **Session Manager** | ❌ Not Started | Empty file exists |
| **Analytics Dashboard** | ❌ Not Started | Frontend placeholder exists |
| **Settings Page** | ❌ Not Started | Frontend placeholder exists |

---

## Phase 1: Auth System ✅ **COMPLETE**

**Completed:**
- [x] User model (username, email, password hash, timestamps)
- [x] Database setup with SQLAlchemy + SQLite
- [x] Password hashing with bcrypt
- [x] JWT token creation/verification (7-day expiry)
- [x] FastAPI routes: `/auth/signup`, `/auth/login`, `/auth/me`
- [x] React Login page with validation
- [x] React Signup page with validation
- [x] AuthContext with token persistence (localStorage)
- [x] Protected/Public route guards
- [x] Axios interceptors for auth headers + 401 handling

---

## Phase 2: Discord Connector + Unified Inbox UI 🚧 **IN PROGRESS**

**Goal:** Connect Discord bot per-user, show real-time messages in unified inbox

### Backend Tasks
- [ ] **Discord Bot Implementation** (`backend/connectors/discord_bot.py`)
  - Per-user bot instances using individual bot tokens
  - Event handling for `on_message`, `on_ready`
  - Message persistence to DB (user-scoped)
  - WebSocket integration for real-time frontend updates

- [ ] **Message Model** (`backend/models/message.py`)
  - Fields: id, user_id, platform, platform_message_id, contact_id, content, direction, timestamp, is_read, mood, urgency, relationship_type
  - Indexes for efficient queries

- [ ] **Contact Model** (`backend/models/contact.py`)
  - Fields: id, user_id, platform, platform_user_id, username, display_name, avatar_url, relationship_type, last_interaction

- [ ] **Platform Model** (`backend/models/platform.py`)
  - Fields: id, user_id, platform_type, credentials (encrypted), is_connected, connected_at, settings JSON

- [ ] **API Routes for Messages** (`backend/api/messages.py`)
  - `GET /messages` - List messages with filters (platform, contact, unread)
  - `GET /messages/:id` - Single message detail
  - `POST /messages/:id/read` - Mark as read
  - WebSocket endpoint for real-time updates

- [ ] **API Routes for Contacts** (`backend/api/contacts.py`)
  - `GET /contacts` - List all contacts
  - `GET /contacts/:id` - Contact detail with message history

- [ ] **API Routes for Platforms** (`backend/api/platforms.py`)
  - `GET /platforms` - List connected platforms
  - `POST /platforms/discord/connect` - Connect Discord (token input)
  - `DELETE /platforms/:id` - Disconnect platform

- [ ] **Session Manager** (`backend/connectors/session_manager.py`)
  - Manage per-user platform connections
  - Start/stop Discord bots
  - Health monitoring

### Frontend Tasks
- [ ] **Inbox Page** (`frontend/src/pages/Inbox.jsx`)
  - Sidebar: Contact list with platform badges, unread counts
  - Main: Message thread view
  - Real-time updates via Socket.IO
  - Search/filter contacts

- [ ] **Conversation View** (`frontend/src/pages/Conversation.jsx`)
  - Message bubbles (incoming/outgoing styling)
  - Timestamps, read receipts
  - Mood badges, platform badges
  - Reply input (for manual replies)

- [ ] **Sidebar Component** (`frontend/src/components/Sidebar.jsx`)
  - Contact list with avatars, platform icons
  - Unread indicator badges
  - Search/filter input

- [ ] **MessageBubble Component** (`frontend/src/components/MessageBubble.jsx`)
  - Incoming/outgoing variants
  - Timestamp display
  - Mood indicator
  - Platform badge

- [ ] **PlatformBadge Component** (`frontend/src/components/PlatformBadge.jsx`)
  - Discord/WhatsApp/Instagram icons with colors

- [ ] **MoodBadge Component** (`frontend/src/components/MoodBadge.jsx`)
  - Visual mood indicators (positive/neutral/negative)

- [ ] **Socket.IO Hook** (`frontend/src/hooks/useSocket.js`)
  - Connection management
  - Event listeners for new messages, status updates

- [ ] **Messages Hook** (`frontend/src/hooks/useMessages.js`)
  - Fetch messages, contacts
  - Optimistic updates

- [ ] **Connect Platforms Page** (`frontend/src/pages/ConnectPlatforms.jsx`)
  - Discord connection form (bot token)
  - Connection status display
  - QR code placeholder for WhatsApp

---

## Phase 3: WhatsApp Service + QR Code Flow

**Goal:** WhatsApp Web integration via whatsapp-web.js Node.js service

### Backend Tasks
- [ ] **WhatsApp Service** (`whatsapp-service/index.js`)
  - Initialize whatsapp-web.js client per user
  - QR code generation and display
  - Session persistence (file-based per user)
  - Message send/receive handling
  - Forward messages to Python backend via HTTP/WebSocket

- [ ] **QR Code Handler** (`whatsapp-service/qr.js`)
  - QR code generation endpoint
  - Polling for scan status
  - Session save/load

- [ ] **API Routes for WhatsApp** (`backend/api/platforms.py` extend)
  - `POST /platforms/whatsapp/connect` - Initiate QR flow
  - `GET /platforms/whatsapp/qr` - Get current QR code
  - `GET /platforms/whatsapp/status` - Check connection status
  - `DELETE /platforms/whatsapp/disconnect` - Logout

### Frontend Tasks
- [ ] **QRScanner Component** (`frontend/src/components/QRScanner.jsx`)
  - Display QR code from backend
  - Auto-refresh until scanned
  - Status indicators (waiting/scanned/connected)

- [ ] **PlatformCard Component** (`frontend/src/components/PlatformCard.jsx`)
  - Connection status, disconnect button
  - Settings for each platform

- [ ] **Integrate WhatsApp into ConnectPlatforms page**

---

## Phase 4: Instagram Connector

**Goal:** Instagram DM integration via instagrapi

### Backend Tasks
- [ ] **Instagram Connector** (`backend/connectors/instagram.py`)
  - Login with username/password (encrypted storage)
  - DM polling/webhook handling
  - Message send/receive
  - Session persistence (challenge handling)

- [ ] **API Routes for Instagram** (`backend/api/platforms.py` extend)
  - `POST /platforms/instagram/connect` - Credentials input
  - `GET /platforms/instagram/status` - Check connection
  - `DELETE /platforms/instagram/disconnect`

### Frontend Tasks
- [ ] **Instagram credentials form** in ConnectPlatforms page
- [ ] **2FA/Challenge handling UI** if needed

---

## Phase 5: AI Engine (Groq) — Style Learner + Reply Generator

**Goal:** Core AI functionality — learn user style, generate contextual replies

### Backend Tasks
- [ ] **Groq Client** (`backend/ai/groq_client.py`)
  - Wrapper for Groq API (LLaMA 3.1 70B)
  - Retry logic, error handling, token counting
  - Separate methods for each AI task

- [ ] **Style Profile Model** (`backend/models/style_profile.py`)
  - Fields: avg_length, emoji_frequency, preferred_emojis, common_phrases, tone, opener_patterns, closer_patterns, formality_score
  - Updated periodically from message history

- [ ] **Style Learner** (`backend/ai/style_learner.py`)
  - Analyze user's outgoing messages
  - Extract linguistic patterns
  - Build/update StyleProfile
  - Incremental learning (new messages only)

- [ ] **Classifier** (`backend/ai/classifier.py`)
  - Relationship classification: Friend / Acquaintance / Stranger
  - Urgency scoring: Low / Medium / High / Emergency
  - Intent detection: Question / Statement / Request / Greeting

- [ ] **Mood Detector** (`backend/ai/mood_detector.py`)
  - Sender mood: Positive / Neutral / Negative / Urgent
  - Adjust reply warmth/empathy accordingly

- [ ] **Reply Generator** (`backend/ai/reply_generator.py`)
  - Generate reply using style profile + context
  - Inputs: incoming message, contact relationship, mood, urgency, calendar context, style profile
  - Output: suggested reply text + confidence score

- [ ] **Prompts** (`backend/ai/prompts.py`)
  - System prompts for each AI task
  - Few-shot examples
  - JSON schema for structured outputs

- [ ] **API Routes for AI** (`backend/api/ai.py` new)
  - `POST /ai/suggest-reply` - Generate reply suggestion
  - `POST /ai/analyze-style` - Trigger style re-analysis
  - `GET /ai/style-profile` - Get current style profile

---

## Phase 6: Mood Detector + Emergency Bypass

**Goal:** Emotional intelligence + safety override

### Backend Tasks
- [ ] **Emergency Detection** (in `classifier.py` or separate)
  - Keyword detection: "emergency", "urgent", "help", "asap", "911"
  - High urgency + negative mood = emergency flag
  - Configurable per user

- [ ] **Notification System** (`backend/utils/notifications.py`)
  - Push notifications (web push / email / in-app)
  - Emergency alert delivery
  - Rate limiting

- [ ] **Busy Mode Toggle** (User settings)
  - Enable/disable auto-reply globally
  - Per-platform toggle
  - Schedule (e.g., "Busy 9-5 weekdays")

- [ ] **API Routes for Settings** (`backend/api/settings.py`)
  - `GET /settings` - Get user preferences
  - `PATCH /settings` - Update preferences
  - `PATCH /settings/busy-mode` - Toggle busy mode

### Frontend Tasks
- [ ] **BusyToggle Component** (`frontend/src/components/BusyToggle.jsx`)
  - Main busy mode switch
  - Per-platform toggles
  - Schedule configuration

- [ ] **EmergencyAlert Component** (`frontend/src/components/EmergencyAlert.jsx`)
  - Prominent alert banner/modal
  - Dismiss/action buttons

- [ ] **Settings Page** (`frontend/src/pages/Settings.jsx`)
  - Busy mode configuration
  - Notification preferences
  - Platform management

---

## Phase 7: Context-Aware Replies (Google Calendar)

**Goal:** Check calendar before replying to availability questions

### Backend Tasks
- [ ] **Calendar Integration** (`backend/integrations/calendar.py`)
  - Google OAuth2 flow
  - Token storage (encrypted)
  - Free/busy query for time ranges
  - Event parsing for context

- [ ] **Calendar-Aware Reply Logic** (in `reply_generator.py`)
  - Detect "are you free", "when can we meet", etc.
  - Query calendar for suggested times
  - Include availability in generated reply

- [ ] **API Routes for Calendar** (`backend/api/calendar.py` new)
  - `GET /calendar/auth-url` - Start OAuth flow
  - `GET /calendar/callback` - Handle OAuth callback
  - `GET /calendar/availability` - Check free/busy
  - `DELETE /calendar/disconnect`

### Frontend Tasks
- [ ] **Google Calendar connect button** in Settings
- [ ] **Availability preview** in reply suggestions

---

## Phase 8: Analytics Dashboard

**Goal:** Insights into messaging patterns

### Backend Tasks
- [ ] **Analytics Model** (`backend/models/analytics.py`)
  - Pre-aggregated tables or materialized views
  - Message volume by day/hour/platform
  - Mood trends over time
  - Top contacts by volume
  - Response times
  - Auto-reply vs manual ratios

- [ ] **Analytics Engine** (`backend/ai/analytics.py` or utils)
  - Aggregation queries
  - Time-series data preparation
  - Export functionality

- [ ] **API Routes for Analytics** (`backend/api/analytics.py`)
  - `GET /analytics/overview` - Summary stats
  - `GET /analytics/volume` - Message volume time series
  - `GET /analytics/mood` - Mood trends
  - `GET /analytics/activity-heatmap` - Hour/day heatmap
  - `GET /analytics/top-senders` - Top contacts
  - `GET /analytics/export` - CSV/JSON export

### Frontend Tasks
- [ ] **Analytics Page** (`frontend/src/pages/Analytics.jsx`)
  - Overview cards (total messages, auto-replies, platforms)
  - Volume chart (Recharts/Chart.js)
  - Mood trend chart
  - Activity heatmap (calendar-style)
  - Top senders leaderboard
  - Date range picker

---

## Phase 9: Polish & Deploy

**Goal:** Production readiness

### Tasks
- [ ] **Error Handling & Logging**
  - Structured logging (backend + frontend)
  - Error boundaries (React)
  - User-friendly error messages

- [ ] **Testing**
  - Backend: pytest (unit + integration)
  - Frontend: Vitest + React Testing Library
  - E2E: Playwright (critical flows)

- [ ] **Performance**
  - Database indexes optimization
  - Pagination for large lists
  - Caching (Redis for sessions/style profiles)
  - Frontend code splitting

- [ ] **Security Hardening**
  - Rate limiting on auth endpoints
  - CORS tightening
  - Input validation/sanitization
  - Dependency scanning

- [ ] **Dockerization**
  - `Dockerfile.backend`
  - `Dockerfile.frontend`
  - `Dockerfile.whatsapp-service`
  - `docker-compose.yml` for local dev
  - `docker-compose.prod.yml` for production

- [ ] **Deployment**
  - Backend: Railway/Render/Fly.io
  - Frontend: Vercel/Netlify
  - WhatsApp Service: Railway/Render (persistent storage)
  - Database: SQLite → PostgreSQL migration
  - Environment variable management
  - SSL/HTTPS setup

- [ ] **Documentation**
  - API docs (OpenAPI/Swagger)
  - User guide
  - Developer setup guide
  - Architecture decision records

---

## Milestone Tracking

| Milestone | Target | Status |
|-----------|--------|--------|
| Auth System Working | Phase 1 | ✅ Done |
| Discord Messages in Inbox | Phase 2 | 🚧 In Progress |
| WhatsApp QR Flow Working | Phase 3 | ⏳ Pending |
| Instagram DMs Working | Phase 4 | ⏳ Pending |
| AI Replies Generating | Phase 5 | ⏳ Pending |
| Emergency Bypass Active | Phase 6 | ⏳ Pending |
| Calendar-Aware Replies | Phase 7 | ⏳ Pending |
| Analytics Dashboard Live | Phase 8 | ⏳ Pending |
| Production Deployed | Phase 9 | ⏳ Pending |

---

## Technical Debt & Risks

| Risk | Mitigation |
|------|------------|
| WhatsApp Web JS stability | Monitor session health, auto-reconnect, fallback to paired devices API if needed |
| Instagram API rate limits | Implement exponential backoff, respect headers, queue requests |
| Groq API costs/limits | Cache style profiles, batch requests, implement fallback templates |
| Multi-user Discord bots | One bot process per user (isolated), or single bot with user routing |
| SQLite concurrency | Migrate to PostgreSQL before production |
| Encrypted credential rotation | Fernet key rotation strategy, re-encrypt on key change |

---

## Definition of Done per Phase

A phase is complete when:
1. All backend endpoints implemented and tested
2. Frontend UI functional and connected
3. Real-time updates work (where applicable)
4. Error states handled gracefully
5. Basic tests passing
6. Code reviewed and merged
7. Documentation updated