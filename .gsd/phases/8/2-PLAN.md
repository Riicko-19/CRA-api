---
phase: 8
plan: 2
wave: 1
gap_closure: false
---

# Plan 8.2: The Agent Executor

## Objective

Create `app/services/agent_runner.py` — a new module with a single `async` function
`execute_agent_task(job_id, repo)` that simulates LLM/Qdrant work with a 5-second sleep,
then transitions the job from `RUNNING` → `COMPLETED`.

## Context

- `app/services/job_service.py` already has `advance_job_state(repo, job_id, target, ...)`.
- The router will schedule `execute_agent_task` via `BackgroundTasks.add_task()` (Plan 8.3).
- Using `asyncio.sleep(5)` is the agreed mock for real LLM work; the router never awaits it
  directly.
- `InMemoryJobRepository` is the current repo type; accept it as the repo parameter type.

## Tasks

<task type="auto">
  <name>Create app/services/agent_runner.py</name>
  <files>app/services/agent_runner.py</files>
  <action>
    Create a **new** file with this exact content:

    ```python
    from __future__ import annotations

    import asyncio

    from app.domain.models import JobStatus
    from app.repository.job_repo import InMemoryJobRepository
    from app.services import job_service


    async def execute_agent_task(job_id: str, repo: InMemoryJobRepository) -> None:
        """Background task — simulates LLM/Qdrant work then marks the job COMPLETED.

        Called via BackgroundTasks.add_task(); the HTTP response is already sent
        before this coroutine runs, preventing any worker starvation.

        Steps:
          1. await 5 s  — placeholder for real async LLM/Qdrant calls
          2. advance_job_state RUNNING  → COMPLETED
        """
        await asyncio.sleep(5)
        job_service.advance_job_state(
            repo,
            job_id,
            JobStatus.COMPLETED,
            result="Task executed successfully",
        )
    ```

    KEY POINTS:
    - `asyncio.sleep(5)` is the agreed mock; tests will patch it with `AsyncMock(return_value=None)`.
    - The function does **not** transition AWAITING_PAYMENT → RUNNING; the router does that
      synchronously in `provide_input` before enqueuing this task.
    - Return type is `None`; BackgroundTasks ignores the return value.
  </action>
  <verify>python -c "from app.services.agent_runner import execute_agent_task; print('import OK')"</verify>
</task>

## Must-Haves

- [ ] `app/services/agent_runner.py` exists
- [ ] `execute_agent_task` is an `async` function accepting `(job_id: str, repo: InMemoryJobRepository)`
- [ ] It calls `asyncio.sleep(5)` before advancing state
- [ ] It calls `job_service.advance_job_state(repo, job_id, JobStatus.COMPLETED, result=...)`
- [ ] `pytest tests/ -v` — still 50/50 (no behaviour change yet; file is not yet wired in)

## Success Criteria

- `python -c "from app.services.agent_runner import execute_agent_task; print('import OK')"` → `import OK`
- `python -c "import inspect, app.services.agent_runner as m; print(inspect.iscoroutinefunction(m.execute_agent_task))"` → `True`
