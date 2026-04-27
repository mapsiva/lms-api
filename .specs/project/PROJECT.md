# LMS API

## Vision
White-label B2B2C LMS platform. SaaS operator → tenants → corporate client companies → employees. FastAPI backend, multi-tenant, async-first.

## Goals
1. Zero HTTPException in application code — all errors via AppError + ErrorCode
2. Thin routers, fat services — business logic lives in services, routers only wire deps and return responses
3. Schemas centralized in app/schemas/ — no inline BaseModel definitions in routers
4. Maintainable error registry — one source of truth for error codes and messages

## Constraints
- Async-only I/O in request cycle
- Every tenant-scoped query must include WHERE tenant_id = :tenant_id
- Manager company_id locked to JWT claims, never from body
- Signed video URLs only (never raw Bunny/Mux/Panda URLs)
