# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

White-label B2B2C LMS platform (FastAPI backend). Multi-tenant: SaaS operator → tenants (course creators/agencies) → corporate client companies → employees. Full PRD in `PRD.md`.

## Commands

```bash
# Dev setup
docker-compose up -d              # PostgreSQL 16 + Redis 7
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Tests (always use real DB, no mocks)
pytest tests/integration/         # integration tests
pytest tests/unit/                # unit tests
pytest tests/ -k "test_name"      # single test
pytest tests/ -x                  # stop on first failure

# Migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Celery worker
celery -A app.tasks worker --loglevel=info

# Linting
ruff check app/
mypy app/
```

## Architecture

### Stack
- **FastAPI** async with Pydantic v2 schemas
- **SQLAlchemy 2.x async** + asyncpg driver + Alembic migrations
- **Redis**: refresh token revocation, rate limiting (slowapi), presence TTL, Celery broker, pub/sub for WebSocket
- **Celery**: emails, webhook processing, transcription, gamification events, AI moderation
- **WebSocket**: presence, notifications, direct messages

### Multi-tenancy (critical)
Every table with user/content data has `tenant_id NOT NULL`. Middleware extracts tenant from domain/subdomain and injects into request context. **No query runs without `WHERE tenant_id = :current_tenant`**.

The four dependency functions in `app/core/dependencies.py` enforce all isolation:
- `get_current_tenant(request)` — resolves tenant from domain
- `get_current_user(tenant, token)` — validates JWT within tenant
- `require_admin(user)` — enforces `role = 'admin'`
- `require_company_access(company_id, user, tenant)` — validates company belongs to tenant; for `manager` role, ignores any `company_id` in request body and uses only `JWT claims.company_id`

### Role hierarchy
```
super_admin  → all tenants (only /superadmin/* endpoints)
  admin      → all resources within own tenant
    manager  → own company only (company_id locked to JWT, never body)
      student → own data only
```

### Security rules (never break these)
- Manager's `company_id` comes from JWT claims — never accept from request body
- Admin of tenant A cannot access company_id from tenant B, even with valid UUID
- When company_id is not found or belongs to wrong tenant → return **404** (not 403, to avoid leaking existence)
- Signed Bunny.net video URLs only (TTL 2h), never expose raw URLs
- Webhook: validate HMAC signature before any processing; return 200 immediately, process via Celery

### Async pattern
All I/O must be async. No blocking calls in request/response cycle. Heavy tasks (email sends, webhook processing, transcription, AI calls, badge evaluation) go to Celery.

### Folder structure
```
app/
├── main.py                  # FastAPI app, routers, CORS, middleware
├── core/
│   ├── config.py            # pydantic-settings from .env
│   ├── security.py          # JWT, bcrypt, magic link tokens
│   ├── dependencies.py      # DI: tenant, user, role, company guards
│   └── database.py          # async SQLAlchemy engine + session factory
├── models/                  # SQLAlchemy ORM (one file per domain)
├── schemas/                 # Pydantic v2 request/response schemas
├── routers/                 # One file per domain (auth, courses, webhooks, etc.)
├── services/                # Business logic decoupled from routers
├── tasks/                   # Celery tasks (email, webhooks, transcription, gamification, moderation)
├── integrations/
│   ├── bunny.py
│   ├── assemblyai.py
│   ├── resend.py
│   ├── anthropic.py
│   └── webhooks/            # Per-gateway parsers (hotmart.py, kiwify.py, greenn.py, etc.)
└── websockets/              # Presence, notifications, messaging handlers
```

### Key design decisions
- **JSONB for flexibility**: `menu_configs.items`, `webhook_logs.payload`, `transcript_text`, `badges.rule_conditions`, `email_automations.steps` — avoids frequent migrations
- **Adapter pattern for payment gateways**: each gateway has its own parser in `integrations/webhooks/`; adding a new gateway = new file, no core changes
- **Presence via Redis TTL**: no `is_online` column; key `presence:{tenant_id}:{user_id}` with TTL 60s
- **Full-text search on transcripts**: PostgreSQL `tsvector` + GIN index; migrate to pgvector later for semantic search
- **Composite indexes**: all major tables need `(tenant_id, ...)` compound indexes for performance

### Video hosting providers
Adapter pattern — each provider lives in `integrations/video/`. Lesson stores `video_provider` + `video_external_id`. Admin configures provider per tenant (or per course). All providers implement the same interface:

```python
class VideoProvider(Protocol):
    async def get_playback_url(self, video_id: str, ttl_seconds: int) -> str: ...
    async def get_metadata(self, video_id: str) -> VideoMetadata: ...
    async def delete(self, video_id: str) -> None: ...
```

| Provider | Notes |
|---|---|
| **Bunny.net** | Signed URL (TTL), HLS streaming, bulk import via library API |
| **Mux** | Signed playback tokens, adaptive bitrate, best analytics |
| **Vimeo** | Embed token via private link, no raw URL exposed |
| **YouTube** | Unlisted embed only (no signed URL) — tenant accepts public risk |
| **Panda Video** | Brazilian CDN, signed URL |

`lessons.video_provider ENUM('bunny','mux','vimeo','youtube','panda','custom')`  
`lessons.video_external_id VARCHAR` — provider-specific ID  
`lessons.video_metadata JSONB` — duration, thumbnails, captions from provider

YouTube does not support signed URLs — use only for unlisted videos. Never expose raw Bunny/Mux/Panda URLs (always sign with short TTL).

### AI integrations
- **Claude Haiku** (via Anthropic API): lesson AI summaries, community content moderation
- **AssemblyAI**: video transcription with word-level timestamps → stored as JSONB in `lessons.transcript_text`
- Transcription flow: admin triggers → Celery → AssemblyAI → webhook callback `POST /internal/transcription-callback` → save transcript → trigger summary

### Gamification
XP events are append-only (`xp_events` table). Users never lose XP. Rankings filtered strictly by `company_id` — no cross-company data exposure. Inter-company league shows only aggregate engagement scores, never individual employee data from other companies.

## Testing policy
Tests use a real PostgreSQL database — no DB mocks. Isolation tests for multi-tenancy are mandatory. Use `pytest-asyncio` with `httpx.AsyncClient` for endpoint tests.

## Environment variables
See `PRD.md` section 17 or `.env.example` for all required variables. Key ones:
- `DATABASE_URL` — `postgresql+asyncpg://...`
- `REDIS_URL`
- `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES=15`, `REFRESH_TOKEN_EXPIRE_DAYS=30`
- `ANTHROPIC_API_KEY` — Claude Haiku for summaries and moderation
- `BUNNY_*`, `ASSEMBLYAI_API_KEY`, `RESEND_API_KEY`, `R2_*`
- Gateway HMAC secrets: `HOTMART_WEBHOOK_SECRET`, `KIWIFY_WEBHOOK_SECRET`, etc.
