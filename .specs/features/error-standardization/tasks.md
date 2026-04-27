# Tasks: Error Standardization & Router Refactor

## Phase 1: Foundation
- [x] **T1** — Create missing error codes in error_codes.py for uncovered scenarios
- [x] **T2** — Create service stubs for domains without services

## Phase 2: Router migration (by domain)
- [x] **T3** — Refactor routers/auth.py (HTTPException → AppError, move logic to services/auth.py)
- [x] **T4** — Refactor routers/courses.py + routers/admin/courses.py (biggest files, extract services/courses.py)
- [x] **T5** — Refactor routers/quiz.py (extract services/quiz.py)
- [x] **T6** — Refactor routers/community.py + routers/admin/community.py (extract services/community.py)
- [x] **T7** — Refactor routers/messages.py + websockets/messages.py (extract services/messages.py)
- [x] **T8** — Refactor routers/notifications.py + websockets/notifications.py (extract services/notifications.py)
- [x] **T9** — Refactor routers/admin/enrollments.py (extract services/enrollment.py)
- [x] **T10** — Refactor routers/admin/companies.py (extract services/company.py)
- [x] **T11** — Refactor routers/admin/tenant.py (extract services/tenant.py)
- [x] **T12** — Refactor routers/admin/dashboard.py + routers/manager/dashboard.py (extract services/dashboard.py)
- [x] **T13** — Refactor routers/admin/email.py (extract services/email.py)
- [x] **T14** — Refactor routers/admin/menu.py + routers/menu.py (extract services/menu.py)
- [x] **T15** — Refactor routers/admin/webhooks.py + routers/webhooks.py (extract services/webhook.py)
- [x] **T16** — Refactor routers/gamification.py (extract services/gamification.py)
- [x] **T17** — Refactor routers/notes.py (extract services/note.py)
- [x] **T18** — Refactor routers/catalog.py (extract services/catalog.py)
- [x] **T19** — Refactor routers/public.py + routers/admin/landing_pages.py (extract services/public.py)
- [x] **T20** — Refactor routers/uploads.py (extract services/upload.py)
- [x] **T21** — Refactor routers/superadmin.py (extract services/superadmin.py)
- [x] **T22** — Refactor routers/internal.py (extract services/internal.py)
- [x] **T23** — Refactor routers/presence.py + websockets/presence.py (extract services/presence.py)

## Phase 3: Cleanup
- [x] **T24** — Remove HTTPException handler from main.py
- [x] **T25** — Run full test suite and fix regressions
- [x] **T26** — Final audit: grep for remaining HTTPException, inline schemas, heavy routers

## Done when
- [x] Zero `HTTPException` in app/routers/ and app/services/
- [x] All routers <150 lines (where feasible)
- [x] Services exist for every domain
- [x] All tests pass
