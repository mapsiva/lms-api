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

## TODO
- Remove HTTPException handler from main.py after all routers migrated (to prevent accidental reintroduction).
- Audit error_codes.py completeness after migration.

## Preferences
- Use Portuguese for user-facing error messages (already established).
- Prefer dataclasses/frozen ErrorDefinition for error registry.
