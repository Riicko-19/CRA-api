---
phase: 8
title: "BackgroundTasks & Rate Limiting"
status: planning
plans: [8.1, 8.2, 8.3, 8.4]
---

# Phase 8: BackgroundTasks & Rate Limiting

## Goal

Refactor the job execution flow to use FastAPI `BackgroundTasks` so HTTP workers are
never blocked by long-running LLM/Qdrant work, and add IP-based rate limiting on
`/start_job` via `slowapi`.

## Key Design Decisions

| Decision | Rationale |
|---|---|
| `Limiter` singleton in `config.py` | Avoids circular imports; re-used by router and main |
| `@limiter.limit("5/minute")` on `/start_job` only | `/provide_input` is webhook-style and already guarded by signature verification |
| `execute_agent_task` awaits `asyncio.sleep(5)` | Pure mock; real implementation will call LLM + Qdrant here |
| `/provide_input` returns job in RUNNING state | Endpoint returns immediately; COMPLETED is async — callers must poll `/status` |
| Test strategy: direct task invocation | Faster + deterministic vs polling; `mock_agent_sleep` makes it instant |

## Dependency Order

```
8.1 (slowapi dep + limiter) → 8.2 (agent_runner) → 8.3 (router + middleware) → 8.4 (tests)
```

Wave 1: 8.1 + 8.2 (no inter-dependency, can parallelize)
Wave 2: 8.3 (depends on 8.1 + 8.2)
Wave 3: 8.4 (depends on 8.3)

## Files Changed

| File | Change |
|---|---|
| `requirements.txt` | Add `slowapi>=0.1.9` |
| `app/core/config.py` | Add `limiter = Limiter(key_func=get_remote_address)` |
| `app/services/agent_runner.py` | **NEW** — `execute_agent_task(job_id, repo)` |
| `app/routers/jobs.py` | Inject `BackgroundTasks`; add rate limit decorator |
| `app/main.py` | Wire `SlowAPIMiddleware` + `RateLimitExceeded` handler |
| `tests/conftest.py` | Add `mock_agent_sleep` autouse fixture |
| `tests/test_phase4_full_flow.py` | Fix 2 tests + add TC-8.1 rate limit test |

## Final Gate Criteria

- [ ] `pytest tests/ -v` — ≥51 passed, 0 failed
- [ ] `POST /start_job` ×6 rapid-fire → 6th returns 429
- [ ] `POST /provide_input` → response `"status": "running"`
- [ ] `python -c "from app.core.config import limiter; print(type(limiter))"` → `<class 'slowapi.Limiter'>`
- [ ] `python -c "from app.services.agent_runner import execute_agent_task; print('OK')"` → `OK`
- [ ] State committed to `main` branch
