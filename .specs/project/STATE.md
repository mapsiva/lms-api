# State

## Decisions
- AppError + ErrorCode are the canonical error pattern. HTTPException is legacy.
- Routers must not contain business logic. CRUD and orchestration belong in services.
- Schemas belong in app/schemas/ exclusively.
- Admin products are now first-class MVP endpoints under `/admin/products`.
- Manager report returns CSV, matching admin company report semantics and using company_id from JWT.
- Admin analytics supports both legacy `/admin/dashboard/analytics/*` and MVP `/admin/analytics/*` paths.

## Blockers
- Integration tests require reachable PostgreSQL and Redis. In sandboxed sessions without network access, tests can hang in `db_engine` before the first test executes.

## Lessons
- Services exist but are underused (only 3 files, 350 lines total). Need to create more.
- Schemas already separated, but some endpoints still use primitive params inline.
- `result` variable reuse across different SQLAlchemy query types causes mypy failures — use descriptive names (`user_result`, `member_result`).

## TODO
- Run full `./appenv/bin/pytest tests/` with local PostgreSQL/Redis reachable outside the restricted sandbox.
- Community spaces are tenant-scoped only — no company_id. All companies share same spaces/channels.

## Preferences
- Use Portuguese for user-facing error messages (already established).
- Prefer dataclasses/frozen ErrorDefinition for error registry.
