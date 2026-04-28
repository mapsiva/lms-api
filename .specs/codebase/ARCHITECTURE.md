# Architecture

## Multi-tenancy
Domain/subdomain extraction via TenantMiddleware. Every tenant-scoped table has `tenant_id NOT NULL`.

## Role hierarchy
super_admin → all tenants
  admin → all resources within own tenant
    manager → own company only (company_id from JWT claims)
      student → own data only

## Error handling
Global exception handlers in main.py:
- AppError → structured JSON with code/message/path/timestamp
- HTTPException → legacy handler (to be removed)
- RequestValidationError → 422 with sanitized Pydantic errors
- Exception → 500 generic

## Async pattern
All I/O async. Heavy tasks go to Celery.
