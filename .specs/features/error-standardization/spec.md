# Spec: Error Standardization & Router Refactor

## Requirements

### ERR-001: No HTTPException in routers
Replace every `raise HTTPException(...)` in `app/routers/` with `raise AppError(ErrorCode.SOME_CODE)`.

### ERR-002: Business logic in services
Move CRUD, validation, and orchestration from routers to `app/services/`. Routers only wire dependencies and return responses.

### ERR-003: Schemas centralized
Extract inline primitive params and inline BaseModel definitions from routers into `app/schemas/`. Routers import schemas only.

### ERR-004: Error codes complete
Ensure `error_codes.py` covers all error scenarios found during migration. Add missing codes when needed.

### ERR-005: Remove legacy handler
After all routers migrated, remove `HTTPException` exception handler from `main.py`.

### ERR-006: Verify no regression
All existing tests pass after refactor.
