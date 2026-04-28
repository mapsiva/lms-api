# Structure

```
app/
├── main.py
├── core/
│   ├── config.py
│   ├── security.py
│   ├── dependencies.py
│   ├── database.py
│   ├── errors.py           # AppError, build_error_response
│   ├── error_codes.py      # ErrorCode registry
│   ├── middleware.py
│   ├── rate_limit.py
│   └── redis_client.py
├── models/                 # SQLAlchemy ORM
├── schemas/                # Pydantic v2 (auth, course, note, notification, quiz, tenant)
├── routers/                # 28 files (heavy, need refactor)
│   ├── admin/
│   └── manager/
├── services/               # Only 3 files (auth, drip, push) — need expansion
├── tasks/                  # Celery tasks
├── integrations/
├── websockets/
```

## Current stats
- Routers: 28 files, most contain business logic
- Services: 3 files, 350 lines total
- Schemas: 6 files
- HTTPException occurrences: 124 in 21 router files
