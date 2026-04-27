# Backend MVP — Task Breakdown

**Feature**: Full LMS Backend (Phases 1–3 of PRD)
**PRD**: `PRD.md`
**Status**: Draft

---

## Testing Policy (from CLAUDE.md)

- **No DB mocks** — all tests hit real PostgreSQL
- **Test types**: `integration` (endpoint tests via httpx.AsyncClient + real DB), `unit` (pure logic, no I/O)
- **Gate commands**:
  - `quick` → `pytest tests/unit/ -x`
  - `full` → `pytest tests/ -x`
  - `build` → `ruff check app/ && mypy app/ && pytest tests/ -x`
- **Parallelism**: integration tests NOT parallel-safe (shared DB state). Unit tests are parallel-safe.

---

## Execution Plan

### Phase 0 — Infrastructure (Sequential)
```
T01 → T02 → T03 → T04 → T05
```

### Phase 1 — Core Foundation (Sequential then Parallel)
```
T05 → T06 → T07 → T08 → T09

T09 ──┬─→ T10 [P]
      ├─→ T11 [P]
      └─→ T12 [P]

T10, T11, T12 → T13 → T14
```

### Phase 2 — Auth & Multi-tenancy (Sequential)
```
T14 → T15 → T16 → T17
```

### Phase 3 — Courses & Content (Parallel after T17)
```
T17 ──┬─→ T18 [P]
      ├─→ T19 [P]
      └─→ T20 [P]

T18, T19, T20 → T21 → T22 → T23
```

### Phase 4 — Webhooks & Enrollments (Parallel after T17)
```
T17 ──┬─→ T24 [P]
      └─→ T25 [P]

T24, T25 ──┬─→ T26 [P]
           ├─→ T27 [P]
           ├─→ T28 [P]
           └─→ T29 [P]

T26, T27, T28, T29 → T30 → T31
```

### Phase 5 — Admin & Menu (after Phase 3+4)
```
T23, T31 ──┬─→ T32 [P]
           └─→ T33 [P]
```

### Phase 6 — B2B Companies (after T17)
```
T17 → T34 → T35 → T36 → T37
```

### Phase 7 — Content Intelligence (Parallel after T18)
```
T18 ──┬─→ T38 [P]
      ├─→ T39 [P]
      └─→ T40 [P]

T38, T39, T40 → T41 → T42
```

### Phase 8 — Email Marketing (after T09)
```
T09 → T43 → T44 → T45 → T46
```

### Phase 9 — Landing Pages & Presence (after T17)
```
T17 ──┬─→ T47 [P]
      └─→ T48 [P]
```

### Phase 10 — Gamification (after T17, T14)
```
T14, T17 → T49 → T50 → T51 → T52 → T53 → T54
```

### Phase 11 — Community (after T14, T17)
```
T14, T17 → T55 → T56 → T57 → T58
```

### Phase 12 — Messaging & Notifications (after T14)
```
T14 ──┬─→ T59 [P]
      └─→ T60 [P]

T59, T60 → T61 → T62
```

### Phase 13 — Analytics & Storage (after Phase 3+6)
```
T23, T37 ──┬─→ T63 [P]
           └─→ T64 [P]
```

### Phase 14 — Integration Tests (after all above)
```
T64 → T65 → T66 → T67
```

---

## Task Breakdown

---

### T01: Docker Compose Setup

**What**: `docker-compose.yml` with PostgreSQL 16 + Redis 7 services, health checks, volume mounts, and `.env.example` with all required variables from PRD §17
**Where**: `docker-compose.yml`, `.env.example`, `Dockerfile`
**Depends on**: None
**Reuses**: N/A

**Done when**:
- [ ] `docker-compose up -d` starts postgres:16 and redis:7 containers
- [ ] PostgreSQL reachable at `localhost:5432`
- [ ] Redis reachable at `localhost:6379`
- [ ] `Dockerfile` builds FastAPI app image
- [ ] `.env.example` has every variable from PRD §17
- [ ] Health checks defined for both services
- [ ] `docker-compose ps` shows all services healthy

**Tests**: none
**Gate**: build (manual docker check)

---

### T02: FastAPI App Skeleton

**What**: `app/main.py` with FastAPI instance, CORS middleware (origins per tenant from settings), lifespan startup/shutdown (DB pool, Redis), router registration stubs, and global exception handlers
**Where**: `app/main.py`
**Depends on**: T01
**Reuses**: N/A

**Done when**:
- [ ] `uvicorn app.main:app --reload` starts without errors
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] CORS configured (allow_origins from settings, not wildcard in prod)
- [ ] Startup: creates DB pool + Redis connection
- [ ] Shutdown: cleanly closes DB pool + Redis
- [ ] 422 validation errors return consistent JSON format
- [ ] Gate check passes: `ruff check app/`

**Tests**: unit
**Gate**: quick

---

### T03: Pydantic-Settings Config

**What**: `app/core/config.py` with `Settings` class loading all env vars (DATABASE_URL, REDIS_URL, JWT_*, BUNNY_*, ASSEMBLYAI_*, RESEND_*, R2_*, gateway HMAC secrets, ANTHROPIC_API_KEY, FRONTEND_URL)
**Where**: `app/core/config.py`
**Depends on**: T01
**Reuses**: N/A

**Done when**:
- [ ] All variables from PRD §17 are typed fields in `Settings`
- [ ] Sensitive fields use `SecretStr`
- [ ] `get_settings()` cached with `@lru_cache`
- [ ] Missing required vars raise clear `ValidationError` on startup
- [ ] Unit test: `Settings` loads from test `.env` correctly
- [ ] Gate check passes: `pytest tests/unit/test_config.py -x`

**Tests**: unit
**Gate**: quick

---

### T04: Async SQLAlchemy Database Setup

**What**: `app/core/database.py` with async engine (asyncpg), `AsyncSessionLocal` factory, `Base` declarative base, and `get_db` async dependency yielding sessions
**Where**: `app/core/database.py`
**Depends on**: T03
**Reuses**: N/A

**Done when**:
- [ ] `create_async_engine` configured with `DATABASE_URL`
- [ ] `AsyncSession` yielded by `get_db` dependency
- [ ] Session auto-committed / rolled-back on exception
- [ ] `Base` imported by all models
- [ ] Unit test: engine connects to test DB without error
- [ ] Gate check passes: `pytest tests/unit/test_database.py -x`

**Tests**: unit
**Gate**: quick

---

### T05: Alembic Migrations Setup

**What**: Initialize Alembic, configure `env.py` for async SQLAlchemy, set `target_metadata = Base.metadata`, verify `alembic upgrade head` runs on empty DB
**Where**: `alembic/`, `alembic.ini`, `alembic/env.py`
**Depends on**: T04
**Reuses**: `app/core/database.py`

**Done when**:
- [ ] `alembic init alembic` completed and configured
- [ ] `env.py` uses async engine from `app/core/database.py`
- [ ] `alembic upgrade head` on empty DB succeeds (no-op, no models yet)
- [ ] `alembic downgrade -1` works
- [ ] `alembic revision --autogenerate` detects model changes
- [ ] Gate check passes: manual `alembic upgrade head`

**Tests**: none
**Gate**: build (manual migration check)

---

### T06: Celery Setup

**What**: `app/core/celery_app.py` with Celery instance configured to use Redis broker + backend, `celery_worker.py` entrypoint, task autodiscovery for `app/tasks/`
**Where**: `app/core/celery_app.py`
**Depends on**: T03
**Reuses**: N/A

**Done when**:
- [ ] `celery -A app.tasks worker --loglevel=info` starts without errors
- [ ] Celery connects to Redis broker from `REDIS_URL`
- [ ] Task result backend configured (Redis)
- [ ] `app/tasks/__init__.py` autodiscovers task modules
- [ ] Unit test: Celery app instance created with correct broker URL
- [ ] Gate check passes: `pytest tests/unit/test_celery.py -x`

**Tests**: unit
**Gate**: quick

---

### T07: Tenant ORM Model + Migration

**What**: `app/models/tenant.py` — SQLAlchemy `Tenant` model matching PRD schema (id, slug, name, custom_domain, subdomain, logo_url, favicon_url, primary_color, secondary_color, font_family, app_name, plan ENUM, features JSONB, created_at) + Alembic migration
**Where**: `app/models/tenant.py`, new Alembic migration
**Depends on**: T05
**Reuses**: `app/core/database.py` Base

**Done when**:
- [ ] `Tenant` model has all fields from PRD §8.3 schema
- [ ] `plan` is PostgreSQL ENUM (`free`, `starter`, `pro`, `enterprise`)
- [ ] `features` is JSONB column
- [ ] Unique constraint on `slug` and `custom_domain`
- [ ] `alembic upgrade head` creates `tenants` table
- [ ] Unit test: `Tenant` model instantiation and field types correct
- [ ] Gate check passes: `pytest tests/unit/test_models.py::test_tenant -x`

**Tests**: unit
**Gate**: quick

---

### T08: User ORM Model + Migration

**What**: `app/models/user.py` — SQLAlchemy `User` model (id, tenant_id FK, email, password_hash nullable, name, avatar_url, bio, role ENUM, company_id FK nullable, is_active, is_suspended, last_seen_at, created_at), composite unique on `(tenant_id, email)`, index on `(tenant_id, role)` + Alembic migration
**Where**: `app/models/user.py`, new Alembic migration
**Depends on**: T07
**Reuses**: `app/models/tenant.py`

**Done when**:
- [ ] `User` model has all fields from PRD §8.1 schema
- [ ] `role` ENUM: `student`, `manager`, `admin`, `super_admin`
- [ ] `UNIQUE(tenant_id, email)` constraint
- [ ] Composite index `(tenant_id, role)` and `(tenant_id, is_active)`
- [ ] `company_id` nullable FK (FK to `companies` added later via migration)
- [ ] `alembic upgrade head` creates `users` table
- [ ] Unit test: `User` model constraints verified
- [ ] Gate check passes: `pytest tests/unit/test_models.py::test_user -x`

**Tests**: unit
**Gate**: quick

---

### T09: Security Module (JWT + bcrypt + Magic Link)

**What**: `app/core/security.py` with: `hash_password`, `verify_password` (bcrypt cost 12), `create_access_token` (15min exp), `create_refresh_token` (30d exp), `decode_token` (raises on expired/invalid), `create_magic_link_token` (15min exp, one-time), `verify_magic_link_token`
**Where**: `app/core/security.py`
**Depends on**: T03
**Reuses**: N/A

**Done when**:
- [ ] `hash_password` uses bcrypt cost factor 12
- [ ] `verify_password` returns True/False without timing attacks
- [ ] Access token payload includes `sub` (user_id), `tenant_id`, `role`, `company_id`, `exp`
- [ ] Refresh token stored in Redis with TTL 30d; `create_refresh_token` returns opaque token
- [ ] `decode_token` raises `HTTPException 401` on expired/invalid
- [ ] Magic link token: UUID stored in Redis with TTL 15min + email key; `verify_magic_link_token` deletes key after use (one-time)
- [ ] Unit tests: hash/verify, token create/decode, magic link flow
- [ ] Gate check passes: `pytest tests/unit/test_security.py -x`

**Tests**: unit
**Gate**: quick

---

### T10: Auth Pydantic Schemas [P]

**What**: `app/schemas/auth.py` — Pydantic v2 schemas: `RegisterRequest`, `LoginRequest`, `TokenResponse`, `RefreshRequest`, `MagicLinkRequest`, `MagicLinkVerifyRequest`, `ForgotPasswordRequest`, `ResetPasswordRequest`, `UserMeResponse`, `UserUpdateRequest`
**Where**: `app/schemas/auth.py`
**Depends on**: T09
**Reuses**: N/A

**Done when**:
- [ ] All schemas use `model_config = ConfigDict(from_attributes=True)`
- [ ] Email fields use `EmailStr`
- [ ] Password fields exclude from serialization
- [ ] `TokenResponse` has `access_token`, `token_type`, `expires_in`
- [ ] `UserMeResponse` maps all non-sensitive `User` fields
- [ ] Unit tests: schema validation, serialization, edge cases
- [ ] Gate check passes: `pytest tests/unit/test_schemas.py::test_auth -x`

**Tests**: unit
**Gate**: quick

---

### T11: Tenant Pydantic Schemas [P]

**What**: `app/schemas/tenant.py` — `TenantBrandingResponse`, `TenantBrandingUpdate`, `TenantSettingsResponse`, `TenantSettingsUpdate`
**Where**: `app/schemas/tenant.py`
**Depends on**: T07
**Reuses**: N/A

**Done when**:
- [ ] `TenantBrandingUpdate` validates hex colors (`#RRGGBB`)
- [ ] `features` field typed as dict with known keys
- [ ] Unit tests: schema validation
- [ ] Gate check passes: `pytest tests/unit/test_schemas.py::test_tenant -x`

**Tests**: unit
**Gate**: quick

---

### T12: Core Dependency Injection [P]

**What**: `app/core/dependencies.py` — implement `get_current_tenant` (resolve from domain header/subdomain, cache in Redis 5min), `get_current_user` (decode JWT, load user within tenant), `require_admin` (enforce role=admin), `require_company_access` (validate company belongs to tenant; manager gets company_id from JWT only)
**Where**: `app/core/dependencies.py`
**Depends on**: T08, T09
**Reuses**: `app/core/security.py`, `app/models/`

**Done when**:
- [ ] `get_current_tenant`: extracts host from request, queries `tenants` by `custom_domain` OR `subdomain`, raises 404 if not found, caches result
- [ ] `get_current_user`: validates Bearer token, queries user WHERE `tenant_id = tenant.id`, raises 401 if invalid, 403 if suspended
- [ ] `require_admin`: raises 403 if role not admin/super_admin
- [ ] `require_company_access`: for manager role, extracts `company_id` from JWT claims (ignores body); for admin, validates `company.tenant_id = tenant.id`; returns 404 (not 403) if company not found or wrong tenant
- [ ] Unit tests: each dependency path (valid, invalid token, wrong tenant, suspended user, manager override, admin cross-tenant blocked)
- [ ] Gate check passes: `pytest tests/unit/test_dependencies.py -x`

**Tests**: unit
**Gate**: quick

---

### T13: Tenant Middleware

**What**: `app/core/middleware.py` — `TenantMiddleware` that extracts tenant from `Host` header, injects `request.state.tenant` for every request, returns 404 for unknown domains
**Where**: `app/core/middleware.py`
**Depends on**: T10, T11, T12
**Reuses**: `app/core/dependencies.py`

**Done when**:
- [ ] Middleware registered in `app/main.py` before routers
- [ ] Unknown host → `{"detail": "Tenant not found"}` with 404
- [ ] Known host → `request.state.tenant` set
- [ ] `X-Tenant-Slug` debug header added in development mode
- [ ] Integration test: two tenants, requests from each domain return isolated data
- [ ] Gate check passes: `pytest tests/integration/test_middleware.py -x`

**Tests**: integration
**Gate**: full

---

### T14: Rate Limiting Setup

**What**: `app/core/rate_limit.py` — slowapi `Limiter` with Redis backend; apply `10/15min` to `/auth/login` and `/auth/magic-link`; apply `5/min` to `/auth/forgot-password`
**Where**: `app/core/rate_limit.py`
**Depends on**: T13
**Reuses**: `app/core/config.py`

**Done when**:
- [ ] `Limiter` uses Redis from `REDIS_URL`
- [ ] Rate limit decorators applied in auth router
- [ ] 429 response returns `Retry-After` header
- [ ] Unit test: limiter configured with correct limits
- [ ] Gate check passes: `pytest tests/unit/test_rate_limit.py -x`

**Tests**: unit
**Gate**: quick

---

### T15: Auth Service

**What**: `app/services/auth.py` — business logic: `register_user`, `login_user` (returns tokens), `logout_user` (revoke refresh token in Redis), `refresh_access_token` (rotate refresh token), `send_magic_link` (store token in Redis + dispatch email task), `verify_magic_link` (validate + auto-login), `send_password_reset`, `reset_password`
**Where**: `app/services/auth.py`
**Depends on**: T09, T12
**Reuses**: `app/core/security.py`, `app/models/user.py`

**Done when**:
- [ ] `register_user`: checks `(tenant_id, email)` uniqueness; hashes password; creates user
- [ ] `login_user`: verifies password; creates access + refresh tokens; stores refresh in Redis
- [ ] `logout_user`: deletes refresh token from Redis
- [ ] `refresh_access_token`: validates refresh token in Redis; rotates (delete old, create new)
- [ ] `send_magic_link`: stores `magic:{token}` in Redis TTL 15min; dispatches email Celery task
- [ ] `verify_magic_link`: validates token, deletes from Redis (one-time use), returns new tokens
- [ ] Integration tests: full register/login/logout/refresh flows against real DB + Redis
- [ ] Gate check passes: `pytest tests/integration/test_auth_service.py -x`

**Tests**: integration
**Gate**: full

---

### T16: Auth Router

**What**: `app/routers/auth.py` — all endpoints from PRD §8.1: `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/magic-link`, `/auth/magic-link/verify`, `/auth/forgot-password`, `/auth/reset-password`, `GET /users/me`, `PATCH /users/me`; refresh token set as `httpOnly` cookie
**Where**: `app/routers/auth.py`
**Depends on**: T15, T14
**Reuses**: `app/services/auth.py`, `app/schemas/auth.py`

**Done when**:
- [ ] All 10 endpoints return documented status codes
- [ ] Refresh token delivered as `httpOnly; Secure; SameSite=Strict` cookie
- [ ] `GET /users/me` requires `get_current_user` dependency
- [ ] Rate limiting applied on login + magic-link endpoints
- [ ] Integration tests: each endpoint, including 401/403/429 cases
- [ ] Gate check passes: `pytest tests/integration/test_auth_router.py -x`

**Tests**: integration
**Gate**: full

---

### T17: Tenant Branding + Settings Router

**What**: `app/routers/admin/tenant.py` — `GET /admin/tenant/branding`, `PATCH /admin/tenant/branding`, `GET /admin/tenant/settings`, `PATCH /admin/tenant/settings`; invalidate Redis cache after update
**Where**: `app/routers/admin/tenant.py`
**Depends on**: T16, T11
**Reuses**: `app/core/dependencies.py` require_admin

**Done when**:
- [ ] Admin-only endpoints (require_admin dependency)
- [ ] PATCH updates only provided fields (partial update)
- [ ] Redis tenant cache invalidated on branding/settings change
- [ ] Integration tests: get and update branding; verify tenant isolation
- [ ] Gate check passes: `pytest tests/integration/test_tenant_router.py -x`

**Tests**: integration
**Gate**: full

---

### T18: Course/Module/Lesson ORM Models + Migration [P]

**What**: `app/models/course.py` — `Course`, `Module`, `Lesson` models with all fields from PRD §8.5; `Lesson.drip_type` ENUM, `drip_value` JSONB, `transcript_text` JSONB, `video_provider` ENUM, `video_external_id`; composite indexes `(tenant_id, slug)`, `(module_id, order_index)` + Alembic migration
**Where**: `app/models/course.py`, new migration
**Depends on**: T07
**Reuses**: `app/models/tenant.py`

**Done when**:
- [ ] All three models with correct FKs and constraints
- [ ] `drip_type` ENUM: `immediate`, `fixed_date`, `days_after_enrollment`, `prerequisite`
- [ ] `video_provider` ENUM: `bunny`, `mux`, `vimeo`, `youtube`, `panda`, `custom`
- [ ] `lesson_type` ENUM: `video`, `text`, `pdf`, `live`, `quiz`, `embed`, `download`
- [ ] `tsvector` generated column on `transcript_text` with GIN index for FTS
- [ ] Migration runs cleanly
- [ ] Unit tests: model instantiation, field types
- [ ] Gate check passes: `pytest tests/unit/test_models.py::test_course -x`

**Tests**: unit
**Gate**: quick

---

### T19: LessonProgress + Notes ORM Models + Migration [P]

**What**: `app/models/progress.py` — `LessonProgress` (user_id, lesson_id, completed_at, last_watched_at, watch_seconds, UNIQUE), `Note` (user_id, lesson_id, content, video_timestamp_seconds, timestamps) + migration
**Where**: `app/models/progress.py`, new migration
**Depends on**: T18
**Reuses**: `app/models/course.py`

**Done when**:
- [ ] `UNIQUE(user_id, lesson_id)` on LessonProgress
- [ ] Indexes: `(user_id, lesson_id)`, `(lesson_id)` for analytics
- [ ] Migration runs cleanly
- [ ] Unit tests: constraints
- [ ] Gate check passes: `pytest tests/unit/test_models.py::test_progress -x`

**Tests**: unit
**Gate**: quick

---

### T20: Product/Enrollment ORM Models + Migration [P]

**What**: `app/models/product.py` — `Product` (id, tenant_id, type ENUM, title, slug, status, visibility, price, gateway_ids JSONB, access_days), `ProductCourse` join; `app/models/enrollment.py` — `Enrollment` (tenant_id, user_id, product_id, status ENUM, expires_at, enrolled_by ENUM, company_id) + migrations
**Where**: `app/models/product.py`, `app/models/enrollment.py`, new migrations
**Depends on**: T18
**Reuses**: `app/models/course.py`

**Done when**:
- [ ] `product.type` ENUM: `course`, `trail`, `mentorship`, `bundle`
- [ ] `enrollment.status` ENUM: `active`, `expired`, `suspended`, `cancelled`, `refunded`
- [ ] `enrollment.enrolled_by` ENUM: `webhook`, `manual`, `admin`, `bulk_import`
- [ ] Unique constraint on `product.slug` per tenant
- [ ] Composite index `(tenant_id, user_id)` on enrollments
- [ ] Migrations run cleanly
- [ ] Unit tests: model constraints
- [ ] Gate check passes: `pytest tests/unit/test_models.py::test_enrollment -x`

**Tests**: unit
**Gate**: quick

---

### T21: Bunny.net Integration

**What**: `app/integrations/video/bunny.py` — implements `VideoProvider` protocol: `get_playback_url(video_id, ttl_seconds)` returns signed URL, `get_metadata(video_id)` returns `VideoMetadata`, `delete(video_id)`, plus `list_library_folder(folder)` for bulk import; `app/integrations/video/base.py` defines `VideoProvider` Protocol and `VideoMetadata` dataclass
**Where**: `app/integrations/video/bunny.py`, `app/integrations/video/base.py`
**Depends on**: T03
**Reuses**: `app/core/config.py`

**Done when**:
- [ ] `VideoProvider` protocol defined with exact interface from CLAUDE.md
- [ ] Signed URL uses HMAC-SHA256 with `BUNNY_STREAM_LIBRARY_ID` + expiry timestamp
- [ ] Raw CDN URLs never returned directly
- [ ] `list_library_folder`: calls Bunny API, returns list of `{video_id, title, duration_seconds, thumbnail_url}`
- [ ] Unit tests: URL signing logic (deterministic), metadata parsing
- [ ] Gate check passes: `pytest tests/unit/test_bunny.py -x`

**Tests**: unit
**Gate**: quick

---

### T22: Admin Courses Router

**What**: `app/routers/admin/courses.py` — `POST /admin/courses`, `PATCH /admin/courses/{id}`, `GET /admin/courses`, `POST /admin/courses/{id}/modules`, `PATCH /admin/modules/{id}`, `PATCH /admin/modules/{id}/reorder`, `POST /admin/modules/{id}/lessons`, `PATCH /admin/lessons/{id}`, `DELETE /admin/lessons/{id}`, `POST /admin/modules/{id}/lessons/bulk-import`, `GET /admin/bunny/library/{folder}`
**Where**: `app/routers/admin/courses.py`
**Depends on**: T18, T21, T17
**Reuses**: `app/core/dependencies.py`, `app/integrations/video/bunny.py`

**Done when**:
- [ ] All endpoints require `require_admin` dependency
- [ ] All queries filter by `tenant_id`
- [ ] `bulk-import`: fetches Bunny folder, creates `Lesson` rows in one transaction
- [ ] `reorder`: accepts `{lesson_ids: [...]}`, updates `order_index` in bulk
- [ ] Course `slug` auto-generated from title if not provided, unique per tenant
- [ ] Integration tests: CRUD, bulk import, reorder, tenant isolation
- [ ] Gate check passes: `pytest tests/integration/test_admin_courses.py -x`

**Tests**: integration
**Gate**: full

---

### T23: Student Courses Router

**What**: `app/routers/courses.py` — `GET /courses`, `GET /courses/{slug}`, `GET /lessons/{id}` (signed video URL), `POST /lessons/{id}/progress`, `GET /courses/{id}/continue`, `GET /courses/{course_id}/search?q=` (PostgreSQL FTS on `transcript_text`)
**Where**: `app/routers/courses.py`
**Depends on**: T19, T22
**Reuses**: `app/integrations/video/bunny.py`, `app/core/dependencies.py`

**Done when**:
- [ ] `GET /courses`: returns only enrolled, active courses for `current_user`
- [ ] `GET /lessons/{id}`: returns signed Bunny URL (TTL 2h), never raw URL; checks enrollment + drip rules
- [ ] `POST /lessons/{id}/progress`: upserts `LessonProgress`, dispatches XP Celery task (if gamification enabled)
- [ ] `GET /courses/{id}/continue`: last `LessonProgress.last_watched_at` record
- [ ] FTS search: `WHERE to_tsvector('portuguese', ...) @@ plainto_tsquery('portuguese', :q)`, ordered by relevance
- [ ] Integration tests: enrollment gate, drip gate, FTS search, signed URL returned
- [ ] Gate check passes: `pytest tests/integration/test_student_courses.py -x`

**Tests**: integration
**Gate**: full

---

### T24: Notes Router [P]

**What**: `app/routers/notes.py` — `GET /lessons/{id}/notes`, `POST /lessons/{id}/notes`, `PATCH /notes/{id}`, `DELETE /notes/{id}` — student owns their notes; filter by `user_id + lesson_id`
**Where**: `app/routers/notes.py`
**Depends on**: T19, T16
**Reuses**: `app/core/dependencies.py`

**Done when**:
- [ ] CRUD for notes scoped to `current_user.id`
- [ ] `video_timestamp_seconds` optional field
- [ ] Cannot access another user's notes (404, not 403)
- [ ] Integration tests: CRUD, ownership isolation
- [ ] Gate check passes: `pytest tests/integration/test_notes.py -x`

**Tests**: integration
**Gate**: full

---

### T25: Drip Content Service [P]

**What**: `app/services/drip.py` — `is_lesson_accessible(user, lesson, enrollment) -> bool` with logic for all four `drip_type` values: `immediate` (always), `fixed_date` (compare date), `days_after_enrollment` (enrollment date + days), `prerequisite` (check `LessonProgress.completed_at` for prerequisite lesson_id)
**Where**: `app/services/drip.py`
**Depends on**: T19, T20
**Reuses**: `app/models/course.py`, `app/models/progress.py`

**Done when**:
- [ ] All four drip types handled correctly
- [ ] `prerequisite`: resolves `drip_value.lesson_id`, checks `LessonProgress.completed_at IS NOT NULL`
- [ ] Returns `{"accessible": bool, "reason": str, "unlocks_at": datetime|None}`
- [ ] Unit tests: all four drip type scenarios, edge cases
- [ ] Gate check passes: `pytest tests/unit/test_drip.py -x`

**Tests**: unit
**Gate**: quick

---

### T26: WebhookLog + Lead ORM Models + Migration [P]

**What**: `app/models/webhook.py` — `WebhookLog` (tenant_id, provider ENUM, event_type, payload JSONB, signature_valid, processed, error_message, attempts, received_at), `Lead` (tenant_id, email, name, source ENUM, UTM fields, product_id nullable, created_at) + migration with index on `(tenant_id, processed, received_at)`
**Where**: `app/models/webhook.py`, new migration
**Depends on**: T07
**Reuses**: `app/models/tenant.py`

**Done when**:
- [ ] `provider` ENUM: `hotmart`, `kiwify`, `greenn`, `monetizze`, `stripe`, `custom`
- [ ] `Lead.source` ENUM: `hotmart_checkout`, `kiwify_checkout`, `greenn_checkout`, `landing_page`
- [ ] Indexes: `(tenant_id, processed)`, `(tenant_id, provider, received_at)`
- [ ] Migration runs cleanly
- [ ] Unit tests: model constraints
- [ ] Gate check passes: `pytest tests/unit/test_models.py::test_webhook -x`

**Tests**: unit
**Gate**: quick

---

### T27: Hotmart Webhook Parser [P]

**What**: `app/integrations/webhooks/hotmart.py` — parse Hotmart webhook payload, validate HMAC-SHA256 signature using `HOTMART_WEBHOOK_SECRET`, return normalized `WebhookEvent(provider, event_type, product_id, buyer_email, buyer_name, status, raw_payload)`
**Where**: `app/integrations/webhooks/hotmart.py`, `app/integrations/webhooks/base.py`
**Depends on**: T03
**Reuses**: `app/integrations/webhooks/base.py` (WebhookEvent dataclass)

**Done when**:
- [ ] `WebhookEvent` base dataclass defined in `base.py`
- [ ] Hotmart HMAC-SHA256 signature validation matches Hotmart docs spec
- [ ] Handles events: `PURCHASE_APPROVED`, `PURCHASE_REFUNDED`, `PURCHASE_CANCELED`, `SUBSCRIPTION_CANCELLATION`
- [ ] Maps Hotmart event types to normalized `status`: `active`, `refunded`, `cancelled`
- [ ] Returns `signature_valid=False` (does NOT raise) when signature fails — router decides behavior
- [ ] Unit tests: valid/invalid signature, each event type mapping
- [ ] Gate check passes: `pytest tests/unit/test_webhook_parsers.py::test_hotmart -x`

**Tests**: unit
**Gate**: quick

---

### T28: Kiwify Webhook Parser [P]

**What**: `app/integrations/webhooks/kiwify.py` — same pattern as T27 for Kiwify, using `KIWIFY_WEBHOOK_SECRET`, Kiwify signature algorithm, Kiwify event types
**Where**: `app/integrations/webhooks/kiwify.py`
**Depends on**: T27
**Reuses**: `app/integrations/webhooks/base.py`

**Done when**:
- [ ] Kiwify HMAC signature validated per Kiwify spec
- [ ] Events: `order.approved`, `order.refunded`, `order.chargeback`
- [ ] Normalized to `WebhookEvent` same as Hotmart parser
- [ ] Unit tests: valid/invalid signature, event mapping
- [ ] Gate check passes: `pytest tests/unit/test_webhook_parsers.py::test_kiwify -x`

**Tests**: unit
**Gate**: quick

---

### T29: Greenn + Monetizze + Stripe Webhook Parsers [P]

**What**: `app/integrations/webhooks/greenn.py`, `monetizze.py`, `stripe.py` — parsers for each gateway following same `WebhookEvent` pattern; Stripe uses `stripe` SDK for signature verification
**Where**: `app/integrations/webhooks/greenn.py`, `monetizze.py`, `stripe.py`
**Depends on**: T27
**Reuses**: `app/integrations/webhooks/base.py`

**Done when**:
- [ ] All three parsers normalize to `WebhookEvent`
- [ ] Stripe uses `stripe.Webhook.construct_event` for signature verification
- [ ] Greenn uses its HMAC method per documentation
- [ ] Monetizze uses its token-based auth per documentation
- [ ] Unit tests for each parser
- [ ] Gate check passes: `pytest tests/unit/test_webhook_parsers.py -x`

**Tests**: unit
**Gate**: quick

---

### T30: Webhook Router + Celery Processing Task

**What**: `app/routers/webhooks.py` — `POST /webhooks/{provider}` for each gateway: validates HMAC immediately, saves `WebhookLog`, returns 200, dispatches Celery task; `app/tasks/webhooks.py` — Celery task: find product by `gateway_id`, upsert enrollment, handle refund (status=refunded), retry with exponential backoff
**Where**: `app/routers/webhooks.py`, `app/tasks/webhooks.py`
**Depends on**: T26, T27, T28, T29, T20
**Reuses**: all parsers, enrollment model

**Done when**:
- [ ] Returns 200 immediately even if signature invalid (logs it, does NOT process)
- [ ] `WebhookLog` created BEFORE any processing
- [ ] Celery task: finds product by `products.gateway_ids->>provider_id`, creates/updates enrollment
- [ ] Refund event: sets `enrollment.status = 'refunded'`, removes active access
- [ ] `WEBHOOK_TEST_MODE=true`: logs but doesn't create enrollments
- [ ] Exponential backoff on task failure: 60s, 300s, 1800s
- [ ] Integration tests: full flow from webhook receipt to enrollment creation, refund flow, test mode
- [ ] Gate check passes: `pytest tests/integration/test_webhooks.py -x`

**Tests**: integration
**Gate**: full

---

### T31: Webhook Admin Router (Logs + Replay)

**What**: `app/routers/admin/webhooks.py` — `GET /admin/webhooks/logs` (paginated, filter by provider/status/date), `POST /admin/webhooks/{id}/replay` (re-dispatch Celery task for specific log), `POST /admin/webhooks/test` (test mode flag)
**Where**: `app/routers/admin/webhooks.py`
**Depends on**: T30
**Reuses**: `app/core/dependencies.py`

**Done when**:
- [ ] Logs paginated with cursor-based pagination
- [ ] Replay: re-runs the Celery task with original payload, increments `attempts`
- [ ] Test endpoint: sets `test_mode=true` for next N requests (stored in Redis)
- [ ] Integration tests: pagination, replay flow
- [ ] Gate check passes: `pytest tests/integration/test_admin_webhooks.py -x`

**Tests**: integration
**Gate**: full

---

### T32: Admin Dashboard + Analytics Endpoints [P]

**What**: `app/routers/admin/dashboard.py` — `GET /admin/dashboard` returning JSON from PRD §8.13; `GET /admin/analytics/engagement`, `/courses`, `/community`, `/revenue`; optimized with CTEs or materialized queries; all scoped to `tenant_id`
**Where**: `app/routers/admin/dashboard.py`
**Depends on**: T23, T31
**Reuses**: `app/core/dependencies.py`

**Done when**:
- [ ] Dashboard JSON matches PRD §8.13 schema exactly
- [ ] All metrics filtered by `tenant_id`
- [ ] Engagement: DAU/WAU/MAU computed from `user_sessions`
- [ ] Revenue: sum of active enrollments' product prices for current month
- [ ] Queries use indexes on `(tenant_id, ...)` composite columns
- [ ] Integration tests: dashboard metrics with seeded data
- [ ] Gate check passes: `pytest tests/integration/test_dashboard.py -x`

**Tests**: integration
**Gate**: full

---

### T33: Menu Config Model + Router [P]

**What**: `app/models/menu.py` — `MenuConfig` (tenant_id, role ENUM, items JSONB, updated_at) + migration; `app/routers/menu.py` — `GET /menu` (role-aware, current user), `GET /admin/menu`, `PUT /admin/menu`
**Where**: `app/models/menu.py`, `app/routers/menu.py`, new migration
**Depends on**: T16
**Reuses**: `app/core/dependencies.py`

**Done when**:
- [ ] `GET /menu` returns correct items for `current_user.role`
- [ ] Default menu items seeded for new tenants on creation
- [ ] `PUT /admin/menu` validates item schema (id, label, icon, url, order, group, visible)
- [ ] Integration tests: student/manager/admin get different menus
- [ ] Gate check passes: `pytest tests/integration/test_menu.py -x`

**Tests**: integration
**Gate**: full

---

### T34: Company ORM Models + Migration

**What**: `app/models/company.py` — `Company` (tenant_id, cnpj, legal_name, trade_name, contract_start, contract_end, max_seats, status ENUM), `CompanyMember` (company_id, user_id, team, job_role, joined_at, is_active, UNIQUE), `CompanyGoal` (company_id, title, target_metric ENUM, target_value, course_id nullable, deadline, badge_reward_id nullable, status ENUM) + migrations; add FK from `users.company_id` to `companies.id`
**Where**: `app/models/company.py`, new migrations
**Depends on**: T08
**Reuses**: `app/models/user.py`

**Done when**:
- [ ] All three models with correct ENUMs from PRD §8.4
- [ ] Composite index `(tenant_id, status)` on companies
- [ ] `UNIQUE(company_id, user_id)` on company_members
- [ ] FK `users.company_id → companies.id` via new migration
- [ ] `alembic upgrade head` clean
- [ ] Unit tests: model constraints
- [ ] Gate check passes: `pytest tests/unit/test_models.py::test_company -x`

**Tests**: unit
**Gate**: quick

---

### T35: Admin Companies Router

**What**: `app/routers/admin/companies.py` — all admin company endpoints from PRD §8.4: CRUD on companies, member management (`GET/POST/PATCH/DELETE`), bulk CSV import, individual invite, engagement report (CSV/PDF), company dashboard — all `company_id` validated against `tenant_id`
**Where**: `app/routers/admin/companies.py`
**Depends on**: T34, T17
**Reuses**: `app/core/dependencies.py`

**Done when**:
- [ ] `POST /admin/companies/{company_id}/members/bulk-import`: parse CSV (email, name, team, job_role), create users with role=student, create company_member records, send invite emails via Celery task
- [ ] `POST /admin/companies/{company_id}/members/invite`: single email invite with signed JWT link
- [ ] Report endpoints: return CSV via `StreamingResponse`
- [ ] All endpoints: `company.tenant_id != current_tenant.id` → 404 (not 403)
- [ ] Integration tests: CRUD, bulk import (500 rows), isolation (admin A cannot access company of tenant B)
- [ ] Gate check passes: `pytest tests/integration/test_admin_companies.py -x`

**Tests**: integration
**Gate**: full

---

### T36: Manager Router

**What**: `app/routers/manager/` — `GET /manager/dashboard`, `GET /manager/members`, `POST /manager/goals`, `GET /manager/goals`, `POST /manager/goals/{goal_id}/reminder`, `GET /manager/report`; all use `company_id` from JWT claims exclusively
**Where**: `app/routers/manager/dashboard.py`
**Depends on**: T34, T35
**Reuses**: `app/core/dependencies.py` require_company_access

**Done when**:
- [ ] `company_id` never read from request body — always from `current_user.company_id` (JWT)
- [ ] Manager with different `company_id` in body → ignored, uses JWT value
- [ ] `POST /manager/goals/{goal_id}/reminder`: sends in-app notification to members behind target; dispatches Celery task
- [ ] `GET /manager/report`: same CSV as admin report but scoped to manager's company
- [ ] Integration tests: manager isolation (cannot access other company even with crafted JWT company_id)
- [ ] Gate check passes: `pytest tests/integration/test_manager.py -x`

**Tests**: integration
**Gate**: full

---

### T37: Enrollment Admin Router

**What**: `app/routers/admin/enrollments.py` — `GET /admin/enrollments` (paginated, filters), `POST /admin/enrollments` (manual), `PATCH /admin/enrollments/{id}`, `DELETE /admin/enrollments/{id}`, `POST /admin/enrollments/bulk` (mass actions); `GET /users/me/enrollments` for students
**Where**: `app/routers/admin/enrollments.py`, add to `app/routers/courses.py`
**Depends on**: T20, T17
**Reuses**: `app/core/dependencies.py`

**Done when**:
- [ ] All admin endpoints require `require_admin`
- [ ] Bulk endpoint: accepts `{action: enroll|suspend|cancel, user_ids: [...], product_id}`, processes in Celery task for >50 records
- [ ] `GET /users/me/enrollments`: returns active enrollments with product details
- [ ] Integration tests: manual enrollment, bulk, student view
- [ ] Gate check passes: `pytest tests/integration/test_enrollments.py -x`

**Tests**: integration
**Gate**: full

---

### T38: AssemblyAI Integration [P]

**What**: `app/integrations/assemblyai.py` — `submit_transcription(video_url) -> transcript_id`, `get_transcript_status(transcript_id) -> TranscriptStatus`, `get_transcript_words(transcript_id) -> list[WordTimestamp]` (mapped to `{text, start_ms, end_ms}` JSONB format)
**Where**: `app/integrations/assemblyai.py`
**Depends on**: T03
**Reuses**: `app/core/config.py`

**Done when**:
- [ ] Async HTTP calls using `httpx.AsyncClient`
- [ ] `WordTimestamp` dataclass: `{text: str, start_ms: int, end_ms: int}`
- [ ] Maps AssemblyAI word-level timestamps to JSONB format stored in `lessons.transcript_text`
- [ ] Unit tests: response parsing with fixture data
- [ ] Gate check passes: `pytest tests/unit/test_assemblyai.py -x`

**Tests**: unit
**Gate**: quick

---

### T39: Claude (Anthropic) Integration [P]

**What**: `app/integrations/anthropic.py` — `generate_lesson_summary(transcript_text: str) -> str` using Claude Haiku; `moderate_content(text: str) -> ModerationResult` with toxicity score; uses Anthropic Python SDK with prompt caching where applicable
**Where**: `app/integrations/anthropic.py`
**Depends on**: T03
**Reuses**: `app/core/config.py`

**Done when**:
- [ ] Uses `anthropic` Python SDK with `claude-haiku-4-5-20251001` model
- [ ] `generate_lesson_summary`: system prompt instructs concise bullet-point summary in Portuguese
- [ ] `moderate_content`: returns `ModerationResult(score: float, flagged: bool, reason: str)`, threshold 0.7
- [ ] Prompt caching enabled for system prompts (cache_control breakpoints)
- [ ] Unit tests: response parsing with mocked SDK (sdk mock, not HTTP)
- [ ] Gate check passes: `pytest tests/unit/test_anthropic.py -x`

**Tests**: unit
**Gate**: quick

---

### T40: Transcription Celery Task + Callback Endpoint [P]

**What**: `app/tasks/transcription.py` — `transcribe_lesson_task(lesson_id)`: gets signed Bunny URL, submits to AssemblyAI, polls or waits for webhook; `app/routers/internal.py` — `POST /internal/transcription-callback`: AssemblyAI notifies completion, saves transcript JSONB, dispatches `summarize_lesson_task`; `summarize_lesson_task(lesson_id)`: calls Claude Haiku, saves `ai_summary`
**Where**: `app/tasks/transcription.py`, `app/routers/internal.py`
**Depends on**: T38, T39, T18
**Reuses**: `app/integrations/assemblyai.py`, `app/integrations/anthropic.py`

**Done when**:
- [ ] `transcribe_lesson_task`: submits transcription, stores `assemblyai_transcript_id` in Redis pending set
- [ ] `/internal/transcription-callback`: validates AssemblyAI auth header, maps transcript to lesson, saves JSONB, triggers summary task
- [ ] `summarize_lesson_task`: calls Claude Haiku, saves to `lessons.ai_summary`
- [ ] Admin endpoints: `POST /admin/lessons/{id}/transcribe`, `GET /admin/lessons/{id}/transcript`, `POST /admin/lessons/{id}/summarize`
- [ ] Integration tests: mock AssemblyAI + Claude calls, verify DB state after callback
- [ ] Gate check passes: `pytest tests/integration/test_transcription.py -x`

**Tests**: integration
**Gate**: full

---

### T41: Resend Email Integration

**What**: `app/integrations/resend.py` — `send_email(to, subject, html_body, from_email)` using Resend API; `app/tasks/email.py` — `send_transactional_email_task`, `send_campaign_batch_task` (batch via Resend), `process_automation_step_task`
**Where**: `app/integrations/resend.py`, `app/tasks/email.py`
**Depends on**: T06, T03
**Reuses**: `app/core/config.py`

**Done when**:
- [ ] `send_email` uses Resend Python SDK with `RESEND_API_KEY`
- [ ] `send_campaign_batch_task`: chunks audience into batches of 100, sends sequentially
- [ ] Email open tracking: appends `<img src="/track/{send_id}/open.gif" width="1" height="1">` unique per send
- [ ] `process_automation_step_task`: evaluates `trigger_event`, applies delay, checks condition, sends email
- [ ] Unit tests: send function with mocked Resend SDK, batch chunking logic
- [ ] Gate check passes: `pytest tests/unit/test_email_tasks.py -x`

**Tests**: unit
**Gate**: quick

---

### T42: Email Marketing Router

**What**: `app/routers/admin/email.py` — audiences CRUD, templates CRUD, campaigns CRUD + `POST /admin/email/campaigns/{id}/send`, automations CRUD; `app/models/email.py` — all email models + migration; open tracking pixel endpoint
**Where**: `app/models/email.py`, `app/routers/admin/email.py`, new migration
**Depends on**: T41, T17
**Reuses**: `app/core/dependencies.py`

**Done when**:
- [ ] All email models from PRD §8.11 with correct ENUMs
- [ ] `audience.filter_json` supports: `{enrolled_in: product_id}`, `{role: student}`, `{company_id: ...}`, `{enrolled_at_after: date}` — service evaluates dynamically
- [ ] Campaign send: resolves audience, creates `email_sends` records, dispatches batch Celery task
- [ ] `GET /track/{send_id}/open.gif`: returns 1x1 GIF, marks `email_sends.status = opened`
- [ ] Integration tests: campaign send flow, open tracking
- [ ] Gate check passes: `pytest tests/integration/test_email_marketing.py -x`

**Tests**: integration
**Gate**: full

---

### T43: Landing Pages Models + Router [P]

**What**: `app/models/landing_page.py` — `LandingPage`, `PageView` + migration; `app/routers/admin/landing_pages.py` — CRUD + analytics; `app/routers/public.py` — `GET /p/{slug}` (serve page), `POST /p/{slug}/lead` (capture lead + UTM params), `POST /admin/landing-pages/{id}/links` (generate UTM link)
**Where**: `app/models/landing_page.py`, `app/routers/admin/landing_pages.py`, `app/routers/public.py`, new migration
**Depends on**: T17
**Reuses**: `app/core/dependencies.py`

**Done when**:
- [ ] `GET /p/{slug}`: returns `jsx_code` + SEO metadata; resolves tenant from domain
- [ ] `POST /p/{slug}/lead`: creates `Lead` record with UTM params, `ip_hash` (SHA256 of IP), product_id if applicable
- [ ] `POST /p/{slug}/lead` does NOT require auth
- [ ] Analytics: `{views: N, leads: N, conversion_rate: float}` per UTM breakdown
- [ ] Integration tests: lead capture with UTM, analytics aggregation
- [ ] Gate check passes: `pytest tests/integration/test_landing_pages.py -x`

**Tests**: integration
**Gate**: full

---

### T44: Presence WebSocket Handler [P]

**What**: `app/websockets/presence.py` — WebSocket handler for `GET /ws/presence`: receives heartbeat every 30s with `{page: str}`, sets Redis key `presence:{tenant_id}:{user_id}` → `{page, last_seen}` TTL 60s; `GET /admin/users/online` queries Redis pattern `presence:{tenant_id}:*` returns list of online users
**Where**: `app/websockets/presence.py`, add endpoint to admin router
**Depends on**: T16
**Reuses**: `app/core/dependencies.py`

**Done when**:
- [ ] WebSocket accepts JWT in first message (not header, for browser compatibility)
- [ ] Heartbeat updates Redis TTL; connection drop → key expires in 60s naturally
- [ ] `GET /admin/users/online`: scans `presence:{tenant_id}:*` keys, returns `[{user_id, name, page, last_seen}]`
- [ ] No `is_online` column in DB
- [ ] Integration tests: WebSocket connection, heartbeat updates Redis, admin endpoint shows online users
- [ ] Gate check passes: `pytest tests/integration/test_presence.py -x`

**Tests**: integration
**Gate**: full

---

### T45: Gamification ORM Models + Migration

**What**: `app/models/gamification.py` — `XPEvent`, `UserLevel`, `Badge`, `UserBadge`, `UserStreak`, `SpecialEvent` with all fields from PRD §9; `League`, `LeagueCompany` from PRD §9.8 + migrations; all with `tenant_id` + composite indexes
**Where**: `app/models/gamification.py`, new migrations
**Depends on**: T07
**Reuses**: `app/models/tenant.py`

**Done when**:
- [ ] All XP/Level/Badge/Streak/Event/League models with correct ENUMs
- [ ] `xp_events` append-only (no UPDATE/DELETE in service layer enforced via comment)
- [ ] `badge.category` ENUM: `behavior`, `completion`, `social`, `event`
- [ ] `badge.rarity` ENUM: `common`, `rare`, `epic`, `legendary`
- [ ] Composite indexes: `(tenant_id, user_id)` on xp_events and user_levels
- [ ] Migrations run cleanly
- [ ] Unit tests: model constraints, XP is append-only pattern
- [ ] Gate check passes: `pytest tests/unit/test_models.py::test_gamification -x`

**Tests**: unit
**Gate**: quick

---

### T46: XP Award Service

**What**: `app/services/gamification/xp.py` — `award_xp(user_id, tenant_id, company_id, action, reference_id, reference_type)`: creates `XPEvent`, updates `UserLevel.total_xp`, checks for level-up (compare to tenant XP thresholds), dispatches `evaluate_badges_task` if level-up; applies `SpecialEvent.xp_multiplier` if active event exists for company
**Where**: `app/services/gamification/xp.py`
**Depends on**: T45
**Reuses**: `app/models/gamification.py`

**Done when**:
- [ ] XP amounts configurable via `tenant.features` JSONB (fallback to PRD defaults)
- [ ] `SpecialEvent` multiplier applied if `starts_at <= now <= ends_at` and `company_id` matches
- [ ] Level-up triggers notification dispatch (Celery task)
- [ ] XP events are append-only — never UPDATE existing rows
- [ ] Unit tests: XP award, level-up detection, multiplier application, event boundary conditions
- [ ] Gate check passes: `pytest tests/unit/test_xp_service.py -x`

**Tests**: unit
**Gate**: quick

---

### T47: Badge Evaluation Service

**What**: `app/services/gamification/badges.py` — `evaluate_badges(user_id, tenant_id, company_id, trigger_event)`: loads all active badges for tenant where `rule_event = trigger_event`, evaluates `rule_conditions` JSONB against user stats, awards `UserBadge` if conditions met and not already awarded; dispatches feed/notification task
**Where**: `app/services/gamification/badges.py`
**Depends on**: T46
**Reuses**: `app/models/gamification.py`

**Done when**:
- [ ] Badge conditions interpreter handles: `{min_xp: N}`, `{courses_completed: N}`, `{streak_days: N}`, `{hour_before: 8}` (Madrugador), `{answers_given: N}` (Mentor)
- [ ] `UNIQUE(user_id, badge_id)` prevents duplicate awards (handle gracefully)
- [ ] Legendary/Epic badge award triggers broadcast notification
- [ ] Unit tests: each condition type, duplicate award prevention
- [ ] Gate check passes: `pytest tests/unit/test_badge_service.py -x`

**Tests**: unit
**Gate**: quick

---

### T48: Streak Service

**What**: `app/services/gamification/streaks.py` — `update_streak(user_id, company_id)`: called on daily first lesson completion; increments `current_streak` if consecutive day, resets to 1 if gap > 1 day (minus available shields), updates `longest_streak`, awards streak-based XP multiplier; `consume_streak_shield` if gap = 1 day and shield available
**Where**: `app/services/gamification/streaks.py`
**Depends on**: T46
**Reuses**: `app/models/gamification.py`

**Done when**:
- [ ] Streak logic handles timezones (use `last_activity_date` in user's timezone — use UTC for MVP)
- [ ] Shield consumption: gap of exactly 1 day + `shields_available > 0` → decrement shield, maintain streak
- [ ] Streak never causes XP loss — only resets counter
- [ ] Celery task `update_streak_task` wraps service call, triggered from lesson progress endpoint
- [ ] Unit tests: consecutive days, gap with shield, gap without shield, longest_streak tracking
- [ ] Gate check passes: `pytest tests/unit/test_streak_service.py -x`

**Tests**: unit
**Gate**: quick

---

### T49: Gamification Celery Tasks

**What**: `app/tasks/gamification.py` — `award_xp_task(user_id, tenant_id, company_id, action, reference_id, reference_type)`, `evaluate_badges_task(user_id, tenant_id, trigger_event)`, `update_streak_task(user_id, company_id)`, `evaluate_company_goal_task(goal_id)`: checks all members' progress against goal target, marks goal achieved and awards badge reward if threshold met
**Where**: `app/tasks/gamification.py`
**Depends on**: T46, T47, T48
**Reuses**: all gamification services

**Done when**:
- [ ] All tasks idempotent (can be replayed safely)
- [ ] Tasks dispatched from: lesson completion (XP+streak), community post (XP), quiz battle (XP)
- [ ] `evaluate_company_goal_task`: aggregates progress for all company members; marks `CompanyGoal.status = achieved`; awards badge to all members
- [ ] Integration tests: full flow — lesson completed → XP awarded → badge evaluated → goal updated
- [ ] Gate check passes: `pytest tests/integration/test_gamification_tasks.py -x`

**Tests**: integration
**Gate**: full

---

### T50: Gamification Router

**What**: `app/routers/gamification.py` — `GET /gamification/leaderboard?company_id=` (company members ranked by XP, period filter), `GET /gamification/my-stats` (XP, level, badges, streak for current user), `GET /gamification/badges` (all tenant badges, user's earned), `GET /admin/gamification/badges` (CRUD), `GET /admin/gamification/events` (CRUD special events), `GET /admin/gamification/leagues` (CRUD leagues)
**Where**: `app/routers/gamification.py`
**Depends on**: T49, T45
**Reuses**: `app/core/dependencies.py`

**Done when**:
- [ ] Leaderboard: `company_id` validated against tenant; never exposes cross-company data
- [ ] League leaderboard: returns company ranks with aggregate scores only — no individual employee data from other companies
- [ ] `GET /gamification/my-stats`: includes `quiz_battles_won`, `top_badges` (3 rarest)
- [ ] Integration tests: leaderboard isolation, cross-company data never leaks
- [ ] Gate check passes: `pytest tests/integration/test_gamification_router.py -x`

**Tests**: integration
**Gate**: full

---

### T51: Community ORM Models + Migration

**What**: `app/models/community.py` — `Space`, `Channel`, `Post`, `Comment`, `PostLike`, `Report` with all fields from PRD §8.8 + migration; indexes: `(channel_id, created_at)` for feed, `(user_id, post_id)` for likes
**Where**: `app/models/community.py`, new migration
**Depends on**: T07
**Reuses**: `app/models/tenant.py`

**Done when**:
- [ ] All models with correct ENUMs (`channel.type`, `channel.post_policy`, `report.status`)
- [ ] `Post.likes_count` and `comments_count` as denormalized integer columns (updated via triggers or service)
- [ ] `PostLike` composite PK `(user_id, post_id)`
- [ ] Migrations run cleanly
- [ ] Unit tests: model constraints
- [ ] Gate check passes: `pytest tests/unit/test_models.py::test_community -x`

**Tests**: unit
**Gate**: quick

---

### T52: Community Student Router

**What**: `app/routers/community.py` — all student endpoints from PRD §8.8: spaces, channels, posts (CRUD), likes, comments (CRUD), reports; `post_policy` enforcement; `likes_count` and `comments_count` updated on mutations
**Where**: `app/routers/community.py`
**Depends on**: T51, T16
**Reuses**: `app/core/dependencies.py`

**Done when**:
- [ ] `post_policy = moderators/admins`: students cannot `POST` to channel
- [ ] `POST /community/posts/{id}/like`: upsert PostLike, increment `likes_count` atomically
- [ ] `DELETE /community/posts/{id}/like`: remove PostLike, decrement `likes_count`
- [ ] All posts/comments scoped to `tenant_id` via channel → space → tenant FK chain
- [ ] `POST /community/posts/{id}/report`: creates Report, dispatches AI moderation task
- [ ] Integration tests: post CRUD, like/unlike, comment, policy enforcement, report creation
- [ ] Gate check passes: `pytest tests/integration/test_community.py -x`

**Tests**: integration
**Gate**: full

---

### T53: Community Admin Router + AI Moderation Task

**What**: `app/routers/admin/community.py` — moderation queue, approve/reject reports, suspend users; `app/tasks/moderation.py` — `moderate_content_task(post_id|comment_id)`: calls Claude Haiku `moderate_content`, if `flagged=true` creates Report with `ai_flagged=true`
**Where**: `app/routers/admin/community.py`, `app/tasks/moderation.py`
**Depends on**: T52, T39
**Reuses**: `app/integrations/anthropic.py`

**Done when**:
- [ ] Moderation task dispatched after every new post and comment
- [ ] Score > 0.7 → auto-creates Report with `ai_flagged=true`, optionally auto-hides post
- [ ] `POST /admin/community/users/{id}/suspend`: sets `user.is_suspended=true`, closes all active WebSocket connections via Redis pub/sub
- [ ] Integration tests: moderation task flow with mocked Claude, admin actions
- [ ] Gate check passes: `pytest tests/integration/test_community_admin.py -x`

**Tests**: integration
**Gate**: full

---

### T54: Community Hall of Fame

**What**: `app/services/community/hall_of_fame.py` — `compute_monthly_hall_of_fame(company_id, tenant_id)`: top 3 users by XP in current month; `GET /gamification/hall-of-fame?company_id=` endpoint; result cached in Redis for 1h; Celery beat task runs daily at midnight
**Where**: `app/services/community/hall_of_fame.py`
**Depends on**: T50, T52
**Reuses**: `app/models/gamification.py`

**Done when**:
- [ ] Result respects `company.features.feed_public = false` → 404 if disabled
- [ ] Top 3 computed from `xp_events` in current calendar month, grouped by user
- [ ] Celery beat schedule configured
- [ ] Integration tests: hall of fame with seeded XP data
- [ ] Gate check passes: `pytest tests/integration/test_hall_of_fame.py -x`

**Tests**: integration
**Gate**: full

---

### T55: Direct Messaging ORM Models + Migration [P]

**What**: `app/models/messaging.py` — `Conversation`, `ConversationParticipant`, `Message` from PRD §8.9 + migration; index `(conversation_id, created_at)`
**Where**: `app/models/messaging.py`, new migration
**Depends on**: T07
**Reuses**: N/A

**Done when**:
- [ ] All three models with correct FKs
- [ ] `ConversationParticipant.last_read_at` nullable TIMESTAMP
- [ ] Migration runs cleanly
- [ ] Unit tests: model constraints
- [ ] Gate check passes: `pytest tests/unit/test_models.py::test_messaging -x`

**Tests**: unit
**Gate**: quick

---

### T56: Messages REST Router [P]

**What**: `app/routers/messages.py` — `GET /messages/conversations`, `POST /messages/conversations`, `GET /messages/conversations/{id}/messages` (paginated), `POST /messages/conversations/{id}/messages`; all scoped to `tenant_id` via participants
**Where**: `app/routers/messages.py`
**Depends on**: T55, T16
**Reuses**: `app/core/dependencies.py`

**Done when**:
- [ ] `GET /messages/conversations`: returns conversations where `current_user` is participant, with last message preview and unread count
- [ ] `POST /messages/conversations/{id}/messages`: creates message, dispatches WebSocket push via Redis pub/sub, dispatches notification task
- [ ] Users can only see conversations they participate in (no cross-tenant)
- [ ] Integration tests: conversation flow, unread counts, isolation
- [ ] Gate check passes: `pytest tests/integration/test_messages.py -x`

**Tests**: integration
**Gate**: full

---

### T57: WebSocket Messaging Handler

**What**: `app/websockets/messages.py` — `GET /ws/messages`: accepts JWT, subscribes to Redis pub/sub channel `messages:{tenant_id}:{user_id}`, forwards new message events; `POST /messages/.../messages` publishes to Redis after DB write
**Where**: `app/websockets/messages.py`
**Depends on**: T56
**Reuses**: Redis pub/sub pattern from presence

**Done when**:
- [ ] WebSocket authentication via first message JWT (same pattern as presence)
- [ ] Message published to Redis → all active WebSocket connections for recipient receive it
- [ ] Disconnect: unsubscribe from Redis channel
- [ ] Integration tests: WebSocket message delivery (two clients in test)
- [ ] Gate check passes: `pytest tests/integration/test_ws_messages.py -x`

**Tests**: integration
**Gate**: full

---

### T58: Notifications ORM Model + Migration [P]

**What**: `app/models/notification.py` — `Notification`, `UserSession` from PRD §8.10 + migration; index `(user_id, is_read, created_at)`
**Where**: `app/models/notification.py`, new migration
**Depends on**: T07
**Reuses**: N/A

**Done when**:
- [ ] `Notification.type` as VARCHAR (flexible: `xp_gained`, `badge_earned`, `goal_achieved`, `message_received`, `streak_reminder`, `broadcast`)
- [ ] `UserSession.pages_visited` as JSONB array
- [ ] Migration runs cleanly
- [ ] Unit tests: model constraints
- [ ] Gate check passes: `pytest tests/unit/test_models.py::test_notification -x`

**Tests**: unit
**Gate**: quick

---

### T59: Notifications Router + WebSocket Handler [P]

**What**: `app/routers/notifications.py` — `GET /notifications` (paginated), `POST /notifications/read-all`, `PATCH /notifications/{id}/read`, `POST /admin/notifications/broadcast`; `app/websockets/notifications.py` — `GET /ws/notifications`: Redis pub/sub channel `notifications:{tenant_id}:{user_id}`
**Where**: `app/routers/notifications.py`, `app/websockets/notifications.py`
**Depends on**: T58, T16
**Reuses**: Redis pub/sub pattern

**Done when**:
- [ ] `POST /admin/notifications/broadcast`: creates Notification for all `tenant_id` users (or segment), dispatches in Celery batch task
- [ ] WebSocket: new notification → push to `current_user`'s channel
- [ ] `is_read` updated atomically (no race condition on read-all)
- [ ] Integration tests: notification creation, WebSocket delivery, broadcast
- [ ] Gate check passes: `pytest tests/integration/test_notifications.py -x`

**Tests**: integration
**Gate**: full

---

### T60: Push Notifications Service (PWA)

**What**: `app/services/push.py` — `send_push_notification(user_id, title, body, action_url)` using Web Push Protocol (VAPID keys); `app/models/push_subscription.py` — `PushSubscription` (user_id, tenant_id, endpoint, keys JSONB) + migration; `POST /push/subscribe` (save subscription), `DELETE /push/subscribe` (remove)
**Where**: `app/services/push.py`, `app/models/push_subscription.py`, new migration
**Depends on**: T59
**Reuses**: `app/core/config.py`

**Done when**:
- [ ] Uses `pywebpush` library with VAPID keys from env
- [ ] `PushSubscription` stores browser push endpoint + `p256dh` + `auth` keys
- [ ] Called from notification Celery task for streak reminders and badge awards
- [ ] Integration tests: subscribe/unsubscribe endpoints
- [ ] Gate check passes: `pytest tests/integration/test_push.py -x`

**Tests**: integration
**Gate**: full

---

### T61: Cloudflare R2 Storage Integration

**What**: `app/integrations/r2.py` — `upload_file(file_content, key, content_type) -> str` (returns public URL), `delete_file(key)` using `boto3` S3-compatible client with R2 credentials; `app/routers/uploads.py` — `POST /uploads/avatar`, `POST /uploads/thumbnail`, `POST /uploads/post-image`; max 10MB, validate content-type
**Where**: `app/integrations/r2.py`, `app/routers/uploads.py`
**Depends on**: T16
**Reuses**: `app/core/config.py`

**Done when**:
- [ ] `boto3` client configured with `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, endpoint URL for R2
- [ ] File size validated before upload (reject >10MB with 413)
- [ ] Content-type whitelist: `image/jpeg`, `image/png`, `image/webp`, `image/gif`
- [ ] Returns `{url: "https://..."}` with public R2 URL
- [ ] Old file deleted from R2 when avatar replaced
- [ ] Integration tests: upload validation, size limit, type checking
- [ ] Gate check passes: `pytest tests/integration/test_uploads.py -x`

**Tests**: integration
**Gate**: full

---

### T62: Quiz Battle ORM Models + Router

**What**: `app/models/quiz.py` — `QuizBattle`, `QuizBattleAnswer` from PRD §9.6 + migration; `app/routers/quiz.py` — `POST /quiz/battles` (challenge), `GET /quiz/battles` (list), `POST /quiz/battles/{id}/answer`, `GET /quiz/battles/{id}` (status + results); XP awarded on completion
**Where**: `app/models/quiz.py`, `app/routers/quiz.py`, new migration
**Depends on**: T49, T18
**Reuses**: `app/services/gamification/xp.py`

**Done when**:
- [ ] Battle created: picks N random questions from course quizzes (or lesson content — use transcript-based questions for MVP)
- [ ] Async mode: 24h `expires_at`; both users answer independently; winner = most correct answers
- [ ] `QuizBattle.winner_id` set when both answered or expired; XP awarded via Celery task
- [ ] Integration tests: challenge flow, answer submission, winner determination, XP award
- [ ] Gate check passes: `pytest tests/integration/test_quiz_battle.py -x`

**Tests**: integration
**Gate**: full

---

### T63: Catalog (Products) Admin + Public Router [P]

**What**: `app/routers/admin/products.py` — `POST /admin/products`, `PATCH /admin/products/{id}`, `PATCH /admin/products/{id}/status`, `GET /admin/products`; `app/routers/catalog.py` — `GET /catalog` (public, published only), `GET /catalog/{slug}` (product landing page data)
**Where**: `app/routers/admin/products.py`, `app/routers/catalog.py`
**Depends on**: T20, T17
**Reuses**: `app/core/dependencies.py`

**Done when**:
- [ ] Product slug auto-generated, unique per tenant
- [ ] `GET /catalog`: no auth required, returns only `status=published AND visibility=public` products
- [ ] `GET /catalog/{slug}`: returns product metadata + included courses (for bundles/trails)
- [ ] Admin: full CRUD including `gateway_ids` JSONB update
- [ ] Integration tests: CRUD, public catalog isolation between tenants
- [ ] Gate check passes: `pytest tests/integration/test_catalog.py -x`

**Tests**: integration
**Gate**: full

---

### T64: Superadmin Router [P]

**What**: `app/routers/superadmin.py` — `GET /superadmin/tenants`, `POST /superadmin/tenants`, `PATCH /superadmin/tenants/{id}`, `GET /superadmin/tenants/{id}/stats`; only accessible by `role=super_admin`; separate auth check from tenant middleware (super_admin not bound to a single tenant)
**Where**: `app/routers/superadmin.py`
**Depends on**: T17
**Reuses**: `app/core/dependencies.py`

**Done when**:
- [ ] `super_admin` check separate from tenant-scoped `require_admin`
- [ ] Can create new tenants (seeds default menu config, default branding)
- [ ] Tenant stats: total users, active enrollments, last_seen
- [ ] Integration tests: super_admin access, regular admin blocked
- [ ] Gate check passes: `pytest tests/integration/test_superadmin.py -x`

**Tests**: integration
**Gate**: full

---

### T65: Test Conftest + Fixtures

**What**: `tests/conftest.py` — async test DB setup (separate test schema or test DB), `AsyncClient` fixture, fixtures: `create_tenant`, `create_user(role, tenant_id, company_id)`, `auth_headers(user)`, `create_enrollment`, `create_course`, `create_company`; database reset between tests (truncate or transaction rollback)
**Where**: `tests/conftest.py`, `tests/integration/conftest.py`
**Depends on**: T16
**Reuses**: all models

**Done when**:
- [ ] `pytest tests/ -x` runs with clean DB state per test
- [ ] `create_tenant` fixture creates a unique tenant with subdomain
- [ ] `auth_headers` returns `{"Authorization": "Bearer <token>"}` dict
- [ ] DB isolation: each test runs in a transaction that is rolled back
- [ ] Gate check passes: `pytest tests/integration/ -x --co` (collection, no execution) succeeds

**Tests**: none
**Gate**: build

---

### T66: Multi-Tenancy Isolation Integration Tests

**What**: `tests/integration/test_isolation.py` — mandatory isolation tests per PRD risk matrix: tenant A data not visible to tenant B, manager cannot access other company, admin cannot access other tenant's company, student cannot access other user's data, webhook from wrong tenant does not affect enrollments
**Where**: `tests/integration/test_isolation.py`
**Depends on**: T65, T36, T37
**Reuses**: all fixtures

**Done when**:
- [ ] Test: two tenants with same course slug — each only sees own course
- [ ] Test: manager sends `company_id` of different company in body — ignored, uses JWT
- [ ] Test: admin of tenant A requests `company_id` from tenant B — 404 (not 403)
- [ ] Test: student requests `/lessons/{id}` without enrollment — 403
- [ ] Test: student requests another user's notes — 404
- [ ] Test: webhook arrives for tenant A, product in tenant B — enrollment not created for tenant B
- [ ] All tests pass: `pytest tests/integration/test_isolation.py -v`
- [ ] Gate check passes: `pytest tests/integration/test_isolation.py -x`

**Tests**: integration
**Gate**: full

---

### T67: Audit Logging

**What**: `app/services/audit.py` — `log_admin_action(user_id, tenant_id, action, resource_type, resource_id, details JSONB)`; `app/models/audit.py` — `AuditLog` model + migration; call from: enrollment changes, company CRUD, user suspension, webhook replay, branding changes; `GET /admin/audit-log` endpoint
**Where**: `app/models/audit.py`, `app/services/audit.py`, new migration
**Depends on**: T37, T35
**Reuses**: `app/core/dependencies.py`

**Done when**:
- [ ] AuditLog: id, tenant_id, user_id, action VARCHAR, resource_type, resource_id, details JSONB, created_at
- [ ] Called as fire-and-forget (async, never blocks response)
- [ ] `GET /admin/audit-log`: paginated, filterable by action/user/resource/date range
- [ ] Integration tests: audit trail created for key admin actions
- [ ] Gate check passes: `pytest tests/integration/test_audit.py -x`

**Tests**: integration
**Gate**: full

---

## Granularity Check

| Task | Scope | Status |
|------|-------|--------|
| T01: Docker setup | Config files | ✅ |
| T02: FastAPI skeleton | 1 file | ✅ |
| T03: Config module | 1 file | ✅ |
| T04: Database setup | 1 file | ✅ |
| T05: Alembic init | Config + env | ✅ |
| T06: Celery setup | 1 file | ✅ |
| T07: Tenant model | 1 model file | ✅ |
| T08: User model | 1 model file | ✅ |
| T09: Security module | 1 file, cohesive JWT/bcrypt | ✅ |
| T10: Auth schemas | 1 schema file | ✅ |
| T11: Tenant schemas | 1 schema file | ✅ |
| T12: Dependencies | 1 file, 4 related DI functions | ✅ |
| T13: Tenant middleware | 1 middleware file | ✅ |
| T14: Rate limiting | 1 config file + router decorators | ✅ |
| T15: Auth service | 1 service file | ✅ |
| T16: Auth router | 1 router file, all auth endpoints | ✅ |
| T17: Tenant branding router | 1 router file | ✅ |
| T18: Course models | 3 related models, 1 file | ✅ |
| T19: Progress models | 2 related models, 1 file | ✅ |
| T20: Product/Enrollment models | 2 related model files | ✅ |
| T21: Bunny integration | 1 integration file + protocol | ✅ |
| T22: Admin courses router | 1 router file | ✅ |
| T23: Student courses router | 1 router file | ✅ |
| T24: Notes router | 1 router file | ✅ |
| T25: Drip service | 1 service file | ✅ |
| T26: Webhook models | 1 model file | ✅ |
| T27: Hotmart parser | 1 integration file | ✅ |
| T28: Kiwify parser | 1 integration file | ✅ |
| T29: Greenn/Monetizze/Stripe parsers | 3 related parsers | ✅ |
| T30: Webhook router + Celery task | 1 router + 1 task file | ✅ |
| T31: Webhook admin router | 1 router file | ✅ |
| T32: Admin dashboard | 1 router file | ✅ |
| T33: Menu model + router | 1 model + 1 router | ✅ |
| T34: Company models | 3 related models, 1 file | ✅ |
| T35: Admin companies router | 1 router file | ✅ |
| T36: Manager router | 1 router file | ✅ |
| T37: Enrollment admin router | 1 router file | ✅ |
| T38: AssemblyAI integration | 1 integration file | ✅ |
| T39: Claude integration | 1 integration file | ✅ |
| T40: Transcription task + callback | 1 task file + 1 internal route | ✅ |
| T41: Resend + email tasks | 1 integration + 1 task file | ✅ |
| T42: Email marketing router | 1 model file + 1 router file | ✅ |
| T43: Landing pages | 1 model + 2 routers | ✅ |
| T44: Presence WebSocket | 1 WS handler | ✅ |
| T45: Gamification models | 6 related models, 1 file | ✅ |
| T46: XP service | 1 service file | ✅ |
| T47: Badge service | 1 service file | ✅ |
| T48: Streak service | 1 service file | ✅ |
| T49: Gamification Celery tasks | 1 task file | ✅ |
| T50: Gamification router | 1 router file | ✅ |
| T51: Community models | 6 related models, 1 file | ✅ |
| T52: Community student router | 1 router file | ✅ |
| T53: Community admin + moderation | 1 router + 1 task file | ✅ |
| T54: Hall of Fame | 1 service + endpoint | ✅ |
| T55: Messaging models | 3 related models, 1 file | ✅ |
| T56: Messages REST router | 1 router file | ✅ |
| T57: WebSocket messaging | 1 WS handler | ✅ |
| T58: Notification models | 1 model file | ✅ |
| T59: Notifications router + WS | 1 router + 1 WS handler | ✅ |
| T60: Push notifications | 1 service + 1 model + endpoints | ✅ |
| T61: R2 storage | 1 integration + 1 router | ✅ |
| T62: Quiz Battle | 1 model + 1 router | ✅ |
| T63: Catalog router | 1 admin + 1 public router | ✅ |
| T64: Superadmin router | 1 router file | ✅ |
| T65: Test conftest | Test infrastructure | ✅ |
| T66: Isolation tests | 1 test file | ✅ |
| T67: Audit logging | 1 model + 1 service + 1 endpoint | ✅ |

---

## Diagram-Definition Cross-Check

| Task | Depends On (body) | Diagram Shows | Status |
|------|-------------------|---------------|--------|
| T01 | None | Start | ✅ |
| T02 | T01 | T01 → T02 | ✅ |
| T03 | T01 | T01 → T03 | ✅ |
| T04 | T03 | T03 → T04 | ✅ |
| T05 | T04 | T04 → T05 | ✅ |
| T06 | T03 | T03 → T06 | ✅ |
| T07 | T05 | T05 → T07 | ✅ |
| T08 | T07 | T07 → T08 | ✅ |
| T09 | T03 | T03 → T09 | ✅ |
| T10 | T09 | T09 → T10 [P] | ✅ |
| T11 | T07 | T09 → T11 [P] | ✅ |
| T12 | T08, T09 | T09 → T12 [P] | ✅ |
| T13 | T10, T11, T12 | T10+T11+T12 → T13 | ✅ |
| T14 | T13 | T13 → T14 | ✅ |
| T15 | T09, T12 | T14 → T15 | ✅ |
| T16 | T15, T14 | T15 → T16 | ✅ |
| T17 | T16, T11 | T16 → T17 | ✅ |
| T18 | T07 | T17 → T18 [P] | ✅ |
| T19 | T18 | T17 → T19 [P] | ✅ |
| T20 | T18 | T17 → T20 [P] | ✅ |
| T21 | T03 | T17 → T21 [phase 3 parallel] | ✅ |
| T22 | T18, T21, T17 | T18+T21 → T22 | ✅ |
| T23 | T19, T22 | T22 → T23 | ✅ |
| T24 | T19, T16 | T17 → T24 [P] | ✅ |
| T25 | T19, T20 | T17 → T25 [P] | ✅ |
| T26 | T07 | T17 → T26 [P] | ✅ |
| T27 | T03 | T24+T25 → T27 [P] | ✅ |
| T28 | T27 | T26+T27 → T28 [P] | ✅ |
| T29 | T27 | T26+T27 → T29 [P] | ✅ |
| T30 | T26, T27, T28, T29, T20 | T26-T29 → T30 | ✅ |
| T31 | T30 | T30 → T31 | ✅ |
| T32 | T23, T31 | T23+T31 → T32 [P] | ✅ |
| T33 | T16 | T23+T31 → T33 [P] | ✅ |
| T34 | T08 | T17 → T34 | ✅ |
| T35 | T34, T17 | T34 → T35 | ✅ |
| T36 | T34, T35 | T35 → T36 | ✅ |
| T37 | T20, T17 | T36 → T37 | ✅ |
| T38 | T03 | T18 → T38 [P] | ✅ |
| T39 | T03 | T18 → T39 [P] | ✅ |
| T40 | T38, T39, T18 | T18 → T40 [P] | ✅ |
| T41 | T06, T03 | T09 → T41 via email phase | ✅ |
| T42 | T41, T17 | T41 → T42 | ✅ |
| T43 | T17 | T17 → T43 [P] | ✅ |
| T44 | T16 | T17 → T44 [P] | ✅ |
| T45 | T07 | T14+T17 → T45 | ✅ |
| T46 | T45 | T45 → T46 | ✅ |
| T47 | T46 | T46 → T47 | ✅ |
| T48 | T46 | T47 → T48 | ✅ |
| T49 | T46, T47, T48 | T48 → T49 | ✅ |
| T50 | T49, T45 | T49 → T50 | ✅ |
| T51 | T07 | T14+T17 → T51 | ✅ |
| T52 | T51, T16 | T51 → T52 | ✅ |
| T53 | T52, T39 | T52 → T53 | ✅ |
| T54 | T50, T52 | T53 → T54 | ✅ |
| T55 | T07 | T14 → T55 [P] | ✅ |
| T56 | T55, T16 | T55 → T56 [P] | ✅ |
| T57 | T56 | T56 → T57 | ✅ |
| T58 | T07 | T14 → T58 [P] | ✅ |
| T59 | T58, T16 | T58 → T59 [P] | ✅ |
| T60 | T59 | T59+T60 → T61 | ✅ |
| T61 | T16 | T59+T60 → T61 | ✅ |
| T62 | T49, T18 | Phase 12 → T62 | ✅ |
| T63 | T20, T17 | T23+T37 → T63 [P] | ✅ |
| T64 | T17 | T23+T37 → T64 [P] | ✅ |
| T65 | T16 | T64 → T65 | ✅ |
| T66 | T65, T36, T37 | T65 → T66 | ✅ |
| T67 | T37, T35 | T66 → T67 | ✅ |

---

## Test Co-location Validation

| Task | Layer Created | Test Type | Task Says | Status |
|------|--------------|-----------|-----------|--------|
| T01 | Config files | none | none | ✅ |
| T02 | FastAPI app skeleton | unit | unit | ✅ |
| T03 | Settings module | unit | unit | ✅ |
| T04 | DB engine + session | unit | unit | ✅ |
| T05 | Migration config | none | none | ✅ |
| T06 | Celery instance | unit | unit | ✅ |
| T07 | ORM model | unit | unit | ✅ |
| T08 | ORM model | unit | unit | ✅ |
| T09 | Security functions | unit | unit | ✅ |
| T10 | Pydantic schemas | unit | unit | ✅ |
| T11 | Pydantic schemas | unit | unit | ✅ |
| T12 | DI functions | unit | unit | ✅ |
| T13 | Middleware | integration | integration | ✅ |
| T14 | Rate limiter config | unit | unit | ✅ |
| T15 | Business logic service | integration | integration | ✅ |
| T16 | Router (endpoints) | integration | integration | ✅ |
| T17 | Router (endpoints) | integration | integration | ✅ |
| T18 | ORM models | unit | unit | ✅ |
| T19 | ORM models | unit | unit | ✅ |
| T20 | ORM models | unit | unit | ✅ |
| T21 | Integration module | unit | unit | ✅ |
| T22 | Router (endpoints) | integration | integration | ✅ |
| T23 | Router (endpoints) | integration | integration | ✅ |
| T24 | Router (endpoints) | integration | integration | ✅ |
| T25 | Pure logic service | unit | unit | ✅ |
| T26 | ORM models | unit | unit | ✅ |
| T27 | Parser function | unit | unit | ✅ |
| T28 | Parser function | unit | unit | ✅ |
| T29 | Parser functions | unit | unit | ✅ |
| T30 | Router + Celery task | integration | integration | ✅ |
| T31 | Router (endpoints) | integration | integration | ✅ |
| T32 | Router (endpoints) | integration | integration | ✅ |
| T33 | Model + router | integration | integration | ✅ |
| T34 | ORM models | unit | unit | ✅ |
| T35 | Router (endpoints) | integration | integration | ✅ |
| T36 | Router (endpoints) | integration | integration | ✅ |
| T37 | Router (endpoints) | integration | integration | ✅ |
| T38 | Integration module | unit | unit | ✅ |
| T39 | Integration module | unit | unit | ✅ |
| T40 | Celery task + endpoint | integration | integration | ✅ |
| T41 | Integration + Celery task | unit | unit | ✅ |
| T42 | Model + router | integration | integration | ✅ |
| T43 | Model + routers | integration | integration | ✅ |
| T44 | WebSocket handler | integration | integration | ✅ |
| T45 | ORM models | unit | unit | ✅ |
| T46 | Business logic service | unit | unit | ✅ |
| T47 | Business logic service | unit | unit | ✅ |
| T48 | Business logic service | unit | unit | ✅ |
| T49 | Celery tasks | integration | integration | ✅ |
| T50 | Router (endpoints) | integration | integration | ✅ |
| T51 | ORM models | unit | unit | ✅ |
| T52 | Router (endpoints) | integration | integration | ✅ |
| T53 | Router + Celery task | integration | integration | ✅ |
| T54 | Service + endpoint | integration | integration | ✅ |
| T55 | ORM models | unit | unit | ✅ |
| T56 | Router (endpoints) | integration | integration | ✅ |
| T57 | WebSocket handler | integration | integration | ✅ |
| T58 | ORM models | unit | unit | ✅ |
| T59 | Router + WS handler | integration | integration | ✅ |
| T60 | Service + model + endpoints | integration | integration | ✅ |
| T61 | Integration + router | integration | integration | ✅ |
| T62 | Model + router | integration | integration | ✅ |
| T63 | Routers (endpoints) | integration | integration | ✅ |
| T64 | Router (endpoints) | integration | integration | ✅ |
| T65 | Test infrastructure | none | none | ✅ |
| T66 | Test file | integration | integration | ✅ |
| T67 | Model + service + endpoint | integration | integration | ✅ |

All checks: ✅ — no violations.

---

## Parallel Execution Map (Summary)

```
PHASE 0 (Sequential):
  T01 → T02 → T03 → T04 → T05 → T06

PHASE 1 (Foundation):
  T05 → T07 → T08 → T09
  T09 → [T10, T11, T12] parallel → T13 → T14

PHASE 2 (Auth):
  T14 → T15 → T16 → T17

PHASE 3 (Courses parallel):
  T17 → [T18, T19, T20, T21] parallel → T22 → T23

PHASE 4 (Webhooks parallel):
  T17 → [T24, T25, T26] parallel
  T26+T27 → [T27, T28, T29] parallel → T30 → T31

PHASE 5 (Admin):
  T23+T31 → [T32, T33] parallel

PHASE 6 (B2B):
  T17 → T34 → T35 → T36 → T37

PHASE 7 (Intelligence):
  T18 → [T38, T39, T40] parallel → T41 → T42

PHASE 8 (Email):
  T03 → T41 → T42

PHASE 9 (Presence + Landing):
  T17 → [T43, T44] parallel

PHASE 10 (Gamification):
  T17 → T45 → T46 → T47 → T48 → T49 → T50

PHASE 11 (Community):
  T17 → T51 → T52 → T53 → T54

PHASE 12 (Messaging + Notifications):
  T16 → [T55, T58] parallel
  T55 → [T56, T59] parallel → T57+T60 → T61

PHASE 13 (Catalog + Superadmin):
  T23+T37 → [T62, T63, T64] parallel

PHASE 14 (Tests + Audit):
  T64 → T65 → T66 → T67
```

---

## Commit Message Format

Each task produces one commit:
```
feat(auth): implement JWT + bcrypt security module
feat(tenant): add tenant ORM model and migration
feat(courses): add admin course CRUD endpoints
fix(webhooks): handle Hotmart refund event correctly
test(isolation): add multi-tenancy isolation integration tests
```
