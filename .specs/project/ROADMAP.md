# Roadmap

## In Progress
- [ ] **Error Standardization & Router Refactor** — migrate 124 HTTPExceptions to AppError, move business logic from routers to services, extract inline schemas

## Next
- [ ] Video provider adapter expansion (Mux, Vimeo, Panda)
- [ ] Gamification badge engine
- [ ] Full-text transcript search via pgvector

## Done
- [x] Initial FastAPI backend with multi-tenant auth
- [x] Admin dashboard, manager dashboard, catalog, community, quiz
- [x] Error codes registry (error_codes.py) + AppError framework (errors.py)
