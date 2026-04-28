# Concerns

## High risk
- **HTTPException in 124 places** — inconsistent error responses, bypasses structured error framework
- **Business logic in routers** — 28 router files with CRUD, validation, orchestration inline. Hard to test, violates separation of concerns
- **Missing services** — most domains have no service layer at all

## Medium risk
- **Schemas incomplete** — some endpoints use primitive params instead of Pydantic schemas (e.g. `body: str` in community)
- **main.py still has HTTPException handler** — enables accidental usage; should be removed after migration
