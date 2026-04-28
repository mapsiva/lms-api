# State

## Decisions
- AppError + ErrorCode are the canonical error pattern. HTTPException is legacy.
- Routers must not contain business logic. CRUD and orchestration belong in services.
- Schemas belong in app/schemas/ exclusively.

## Blockers
- None

## Lessons
- Services exist but are underused (only 3 files, 350 lines total). Need to create more.
- Schemas already separated, but some endpoints still use primitive params inline.
- `result` variable reuse across different SQLAlchemy query types causes mypy failures — use descriptive names (`user_result`, `member_result`).

## TODO
- None

## Preferences
- Use Portuguese for user-facing error messages (already established).
- Prefer dataclasses/frozen ErrorDefinition for error registry.
