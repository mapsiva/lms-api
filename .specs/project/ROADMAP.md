# Roadmap

## In Progress
- None

## Next
- [ ] Full-text transcript search via pgvector (semantic, upgrade from tsvector)
- [ ] Community spaces per company (add company_id to spaces model)

## Done
- [x] Initial FastAPI backend with multi-tenant auth
- [x] Admin dashboard, manager dashboard, catalog, community, quiz
- [x] MVP admin products CRUD/status/gateway IDs
- [x] MVP company member update and company dashboard
- [x] MVP admin analytics aliases including community analytics
- [x] MVP landing page UTM link generator
- [x] MVP public company invite acceptance
- [x] MVP manager CSV report
- [x] Error codes registry (error_codes.py) + AppError framework (errors.py)
- [x] Video provider adapter expansion (Mux, Vimeo, Panda)
- [x] Gamification badge engine
- [x] Full-text transcript search (tsvector + GIN index)
- [x] Email marketing system with system email templates
- [x] Community spaces gated behind product enrollment (product_spaces table)
- [x] Pinned posts in community (is_pinned column + migration)
- [x] Seed expanded to full 10x dataset (21 users, 4 companies, 7 spaces, 19 channels)
