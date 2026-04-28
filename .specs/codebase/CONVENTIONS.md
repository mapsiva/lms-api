# Conventions

## Error handling
- Use `raise AppError(ErrorCode.SOME_CODE)` from `app.core.errors` and `app.core.error_codes`
- Never raise `HTTPException` in routers, services, or anywhere else
- Error handler in `main.py` converts AppError → JSONResponse automatically

## Schemas
- All Pydantic request/response models live in `app/schemas/` (one file per domain)
- No inline `BaseModel` definitions in routers
- Prefer explicit response schemas over raw dicts

## Services
- Business logic belongs in `app/services/` (one file per domain)
- Routers should only: validate request, call service, return response
- Services receive primitives and return models/schemas; no HTTP concerns

## Routers
- One file per domain in `app/routers/`
- Admin routers under `app/routers/admin/`
- Manager routers under `app/routers/manager/`
- Keep routers thin (<100 lines where possible)
