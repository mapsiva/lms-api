# LMS API

Backend FastAPI da plataforma LMS white-label B2B2C.

## Estado do MVP

Implementado no backend atual:

- Multi-tenancy por domínio/subdomínio com isolamento por `tenant_id`.
- Auth com JWT, refresh token em Redis, magic link e reset de senha.
- Admin: tenant settings, cursos/módulos/aulas, produtos, empresas/membros, matrículas, dashboard, analytics, menu, landing pages, webhooks, email marketing, comunidade, gamificação, auditoria, uploads e notificações.
- Manager: dashboard, membros, metas, lembretes e relatório CSV escopado à empresa do JWT.
- Aluno/público: catálogo, cursos, progresso, notas, comunidade, quiz battle, gamificação, mensagens, notificações, landing pages, captura de leads e aceite público de convite de empresa.
- WebSockets: presence, mensagens e notificações.

Rotas MVP adicionadas na última atualização:

- `GET /admin/products`
- `POST /admin/products`
- `PATCH /admin/products/{product_id}`
- `PATCH /admin/products/{product_id}/status`
- `PATCH /admin/companies/{company_id}/members/{user_id}`
- `GET /admin/companies/{company_id}/dashboard`
- `GET /admin/analytics/engagement`
- `GET /admin/analytics/courses`
- `GET /admin/analytics/community`
- `GET /admin/analytics/revenue`
- `POST /admin/landing-pages/{page_id}/links`
- `POST /invites/{token}/accept`
- `GET /manager/report` com `text/csv`

## Desenvolvimento

Use o virtualenv local:

```bash
source appenv/bin/activate
docker-compose up -d
alembic upgrade head
uvicorn app.main:app --reload
```

## Testes

Os testes de integração usam PostgreSQL e Redis reais, definidos por `DATABASE_URL` e `REDIS_URL`.

```bash
./appenv/bin/ruff check app/
./appenv/bin/pytest tests/integration/
./appenv/bin/pytest tests/unit/
```

Nesta sessão, a execução dos testes de integração ficou bloqueada na fixture `db_engine` ao tentar inicializar serviços locais, porque o sandbox atual não tem acesso de rede. A validação local concluída foi:

```bash
./appenv/bin/ruff check <arquivos alterados>
./appenv/bin/python -m compileall -q app tests/integration/test_admin_products.py tests/integration/test_admin_companies.py tests/integration/test_dashboard.py tests/integration/test_landing_pages.py tests/integration/test_manager.py
./appenv/bin/pytest tests/integration/test_admin_products.py --collect-only -q
```
