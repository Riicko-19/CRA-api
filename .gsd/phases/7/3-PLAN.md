---
phase: 7
plan: 3
wave: 3
gap_closure: false
---

# Plan 7.3: Failure-Proof Exception Handlers

## Objective

Register two new `@app.exception_handler` decorators inside `create_app()` in `app/main.py` that intercept Qdrant connection failures and return a clean `503 Service Unavailable` instead of a raw `500`.

## Context

- `app/main.py` — `create_app()` currently has 4 exception handlers (422, 404, 409, 403)
- Target exception classes from `qdrant_client.http.exceptions`:
  - `ResponseHandlingException` — raised when the HTTP response cannot be parsed
  - `UnexpectedResponse` — raised when Qdrant returns an unexpected HTTP status
- Both handlers must return identical `JSONResponse(status_code=503, ...)` responses

## Tasks

<task type="auto">
  <name>Add Qdrant exception handlers to app/main.py</name>
  <files>app/main.py</files>
  <action>
    1. Add to the import block at the top of the file:

    ```python
    from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
    ```

    2. Inside `create_app()`, after the existing `invalid_signature_handler`, add:

    ```python
    @app.exception_handler(ResponseHandlingException)
    async def qdrant_response_handling_handler(
        request: Request, exc: ResponseHandlingException
    ):
        return JSONResponse(
            status_code=503,
            content={"detail": "Vector database temporarily unavailable. Please try again later."},
        )

    @app.exception_handler(UnexpectedResponse)
    async def qdrant_unexpected_response_handler(
        request: Request, exc: UnexpectedResponse
    ):
        return JSONResponse(
            status_code=503,
            content={"detail": "Vector database temporarily unavailable. Please try again later."},
        )
    ```

    KEY POINTS:
    - Import path is `qdrant_client.http.exceptions` (not `qdrant_client.exceptions`).
    - Both handlers return the EXACT same 503 body — identical `detail` string required.
    - No other lines in `create_app()` change; existing handlers untouched.
  </action>
  <verify>python -c "from app.main import create_app; app = create_app(); print([r for r in app.exception_handlers])"</verify>
</task>

## Must-Haves

- [ ] `ResponseHandlingException` and `UnexpectedResponse` imported from `qdrant_client.http.exceptions`
- [ ] Both handlers registered inside `create_app()`
- [ ] Both return `JSONResponse(status_code=503, content={"detail": "Vector database temporarily unavailable. Please try again later."})`
- [ ] Existing 4 handlers (422, 404, 409, 403) untouched

## Success Criteria

- `python -c "from app.main import create_app; app = create_app(); print(len(app.exception_handlers))"` → `6` (4 existing + 2 new)
- `pytest tests/ -v` — still 50/50
