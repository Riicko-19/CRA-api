---
phase: 5
plan: 3
wave: 2
gap_closure: true
---

# Plan 5.3: Test Suite Updates & Phase 5 Gate

## Objective

Surgically update the four existing test suites to match the new contracts, write a new `test_phase5_mip003.py` covering all Phase 5 requirements, and run the full combined gate. Runs AFTER Plans 5.1 and 5.2.

## Context

- `tests/test_phase1_models.py` — must update `_make_valid_job`, TC-1.1, TC-1.2, TC-1.4, TC-1.5
- `tests/test_phase2_repository.py` — must update TC-2.1; optionally extend TC-2.4
- `tests/test_phase3_endpoints.py` — must update TC-3.3, TC-3.5; remove/update TC-3.8 (queue_depth gone)
- `tests/test_phase4_full_flow.py` — no changes needed
- `tests/test_phase5_mip003.py` — NEW, 8 TCs

## Tasks

<task type="auto">
  <name>Update tests/test_phase1_models.py</name>
  <files>tests/test_phase1_models.py</files>
  <action>
    Replace `tests/test_phase1_models.py` with:

    ```python
    import time
    import pytest
    from datetime import datetime
    from pydantic import ValidationError

    from app.domain.models import Job, JobStatus, validate_transition
    from app.domain.exceptions import InvalidStateTransitionError


    # --- Helpers ---

    def _make_valid_job(**overrides) -> Job:
        """Factory for a valid Job instance."""
        now_ts = int(time.time())
        defaults = dict(
            job_id="test-job-id-0001",
            status=JobStatus.AWAITING_PAYMENT,
            input_hash="a" * 64,
            blockchain_identifier="mock_bc_test",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            pay_by_time=now_ts + 3600,
            seller_vkey="mock_vkey_test",
            submit_result_time=now_ts + 7200,
            unlock_time=now_ts + 86400,
        )
        defaults.update(overrides)
        return Job(**defaults)


    # TC-1.1: JobStatus has exactly 5 members
    def test_job_status_members():
        assert set(JobStatus) == {
            JobStatus.AWAITING_PAYMENT,
            JobStatus.AWAITING_INPUT,
            JobStatus.RUNNING,
            JobStatus.COMPLETED,
            JobStatus.FAILED,
        }


    # TC-1.2: Job model rejects extra fields
    def test_job_rejects_extra_fields():
        now_ts = int(time.time())
        with pytest.raises(ValidationError):
            Job(
                job_id="abc",
                status=JobStatus.AWAITING_PAYMENT,
                input_hash="x" * 64,
                blockchain_identifier="mock_bc_abc",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                pay_by_time=now_ts + 3600,
                seller_vkey="vk_test",
                submit_result_time=now_ts + 7200,
                unlock_time=now_ts + 86400,
                EXTRA_FIELD="should_fail",
            )


    # TC-1.3: Job model is frozen (immutable)
    def test_job_is_frozen():
        job = _make_valid_job()
        with pytest.raises(ValidationError):
            job.status = JobStatus.RUNNING


    # TC-1.4: Legal transitions do not raise
    @pytest.mark.parametrize("from_s,to_s", [
        (JobStatus.AWAITING_PAYMENT, JobStatus.RUNNING),
        (JobStatus.RUNNING, JobStatus.COMPLETED),
        (JobStatus.RUNNING, JobStatus.FAILED),
        (JobStatus.RUNNING, JobStatus.AWAITING_INPUT),
        (JobStatus.AWAITING_INPUT, JobStatus.RUNNING),
    ])
    def test_legal_transitions(from_s, to_s):
        validate_transition(from_s, to_s)  # must NOT raise


    # TC-1.5: Illegal transitions raise InvalidStateTransitionError
    @pytest.mark.parametrize("from_s,to_s", [
        (JobStatus.AWAITING_PAYMENT, JobStatus.COMPLETED),
        (JobStatus.AWAITING_PAYMENT, JobStatus.FAILED),
        (JobStatus.COMPLETED, JobStatus.RUNNING),
        (JobStatus.FAILED, JobStatus.RUNNING),
        (JobStatus.COMPLETED, JobStatus.AWAITING_PAYMENT),
        (JobStatus.RUNNING, JobStatus.AWAITING_PAYMENT),
        (JobStatus.AWAITING_INPUT, JobStatus.COMPLETED),
        (JobStatus.AWAITING_INPUT, JobStatus.FAILED),
    ])
    def test_illegal_transitions(from_s, to_s):
        with pytest.raises(InvalidStateTransitionError):
            validate_transition(from_s, to_s)


    # TC-1.6: InvalidStateTransitionError carries state info
    def test_invalid_transition_error_attributes():
        try:
            validate_transition(JobStatus.COMPLETED, JobStatus.RUNNING)
            pytest.fail("Expected InvalidStateTransitionError")
        except InvalidStateTransitionError as e:
            assert e.from_state == "completed"
            assert e.to_state == "running"
    ```

    AVOID: Do NOT remove or weaken any existing TC. Only extend.
  </action>
  <verify>pytest tests/test_phase1_models.py -v --tb=short</verify>
  <done>
    - All TC-1.x pass (count increases from 13 to 15 due to 2 new parametrize entries in TC-1.4 and 2 more in TC-1.5).
    - `_make_valid_job()` works with no overrides.
  </done>
</task>

<task type="auto">
  <name>Update tests/test_phase2_repository.py</name>
  <files>tests/test_phase2_repository.py</files>
  <action>
    Update `TC-2.1` only — add assertions for the 4 new MIP-003 fields.

    FIND in TC-2.1:
    ```python
    def test_create_job_initial_state():
        repo = InMemoryJobRepository()
        job = repo.create(input_hash="a" * 64)
        assert job.status == JobStatus.AWAITING_PAYMENT
        assert job.input_hash == "a" * 64
        assert job.blockchain_identifier.startswith("mock_bc_")
        assert job.result is None
        assert job.error is None
    ```

    REPLACE WITH:
    ```python
    def test_create_job_initial_state():
        import time
        repo = InMemoryJobRepository()
        job = repo.create(input_hash="a" * 64)
        assert job.status == JobStatus.AWAITING_PAYMENT
        assert job.input_hash == "a" * 64
        assert job.blockchain_identifier.startswith("mock_bc_")
        assert job.result is None
        assert job.error is None
        # MIP-003 fields
        assert job.pay_by_time > int(time.time())
        assert job.seller_vkey.startswith("mock_vkey_")
        assert job.submit_result_time > int(time.time())
        assert job.unlock_time > int(time.time())
    ```

    All other TCs (TC-2.2 through TC-2.8) remain unchanged.
    AVOID: Do NOT rewrite the entire file.
  </action>
  <verify>pytest tests/test_phase2_repository.py -v --tb=short</verify>
  <done>
    - All 8 Phase 2 tests pass.
    - TC-2.1 now validates MIP-003 fields.
  </done>
</task>

<task type="auto">
  <name>Update tests/test_phase3_endpoints.py</name>
  <files>tests/test_phase3_endpoints.py</files>
  <action>
    Three targeted changes:

    1. UPDATE TC-3.3 (`test_availability`):

    FIND:
    ```python
    # TC-3.3: GET /availability returns 200 with correct shape
    @pytest.mark.asyncio
    async def test_availability(client):
        async with client as c:
            r = await c.get("/availability")
        assert r.status_code == 200
        data = r.json()
        assert data["available"] is True
        assert isinstance(data["queue_depth"], int)
    ```

    REPLACE WITH:
    ```python
    # TC-3.3: GET /availability returns MIP-003 contract shape
    @pytest.mark.asyncio
    async def test_availability(client):
        async with client as c:
            r = await c.get("/availability")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "available"
        assert data["service_type"] == "masumi-agent"
    ```

    2. UPDATE TC-3.5 (`test_start_job_creates_job`) — add MIP-003 field assertions:

    FIND:
    ```python
    # TC-3.5: POST /start_job creates a job and returns 201
    @pytest.mark.asyncio
    async def test_start_job_creates_job(client):
        async with client as c:
            r = await c.post("/start_job", json={"inputs": {"task": "do_work"}})
        assert r.status_code == 201
        job = r.json()
        assert job["status"] == "awaiting_payment"
        assert len(job["input_hash"]) == 64
        assert job["blockchain_identifier"].startswith("mock_bc_")
    ```

    REPLACE WITH:
    ```python
    # TC-3.5: POST /start_job creates a job and returns 201 with MIP-003 fields
    @pytest.mark.asyncio
    async def test_start_job_creates_job(client):
        async with client as c:
            r = await c.post("/start_job", json={"inputs": {"task": "do_work"}})
        assert r.status_code == 201
        job = r.json()
        assert job["status"] == "awaiting_payment"
        assert len(job["input_hash"]) == 64
        assert job["blockchainIdentifier"].startswith("mock_bc_")
        assert isinstance(job["payByTime"], int)
        assert job["sellerVKey"].startswith("mock_vkey_")
    ```

    3. UPDATE TC-3.8 (`test_queue_depth_increases`) — `queue_depth` is no longer in `/availability`:

    FIND:
    ```python
    # TC-3.8: queue_depth increases after job creation
    @pytest.mark.asyncio
    async def test_queue_depth_increases(client):
        async with client as c:
            before = (await c.get("/availability")).json()["queue_depth"]
            await c.post("/start_job", json={"inputs": {"task": "x"}})
            after = (await c.get("/availability")).json()["queue_depth"]
        assert after == before + 1
    ```

    REPLACE WITH:
    ```python
    # TC-3.8: Multiple /start_job calls each return a unique job_id
    @pytest.mark.asyncio
    async def test_multiple_jobs_have_unique_ids(client):
        async with client as c:
            r1 = await c.post("/start_job", json={"inputs": {"task": "x"}})
            r2 = await c.post("/start_job", json={"inputs": {"task": "x"}})
        assert r1.json()["job_id"] != r2.json()["job_id"]
    ```

    AVOID: Do NOT change TC-3.1, TC-3.2, TC-3.4, TC-3.6, TC-3.7 — they are unaffected.
  </action>
  <verify>pytest tests/test_phase3_endpoints.py -v --tb=short</verify>
  <done>
    - All 8 Phase 3 tests pass with updated assertions.
    - TC-3.3 checks `status`/`service_type` instead of `available`/`queue_depth`.
    - TC-3.5 checks `blockchainIdentifier` (camelCase) and `payByTime`.
    - TC-3.8 checks unique job IDs instead of `queue_depth`.
  </done>
</task>

<task type="auto">
  <name>Create tests/test_phase5_mip003.py</name>
  <files>tests/test_phase5_mip003.py</files>
  <action>
    Create `tests/test_phase5_mip003.py` with 8 test cases:

    ```python
    import time
    import pytest
    import httpx

    from app.domain.models import JobStatus, validate_transition
    from app.domain.exceptions import InvalidStateTransitionError
    from app.main import create_app


    @pytest.fixture
    def client():
        app = create_app()
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        )


    async def _create_job(c: httpx.AsyncClient) -> dict:
        r = await c.post("/start_job", json={"inputs": {"task": "mip003_test"}})
        assert r.status_code == 201
        return r.json()


    # TC-5.1: JobStatus has 5 members including awaiting_input
    def test_job_status_has_awaiting_input():
        assert len(JobStatus) == 5
        assert JobStatus.AWAITING_INPUT.value == "awaiting_input"


    # TC-5.2: RUNNING -> AWAITING_INPUT and AWAITING_INPUT -> RUNNING are legal
    def test_running_awaiting_input_roundtrip():
        validate_transition(JobStatus.RUNNING, JobStatus.AWAITING_INPUT)   # no raise
        validate_transition(JobStatus.AWAITING_INPUT, JobStatus.RUNNING)   # no raise


    # TC-5.3: AWAITING_INPUT -> COMPLETED and AWAITING_INPUT -> FAILED are illegal
    @pytest.mark.parametrize("target", [JobStatus.COMPLETED, JobStatus.FAILED])
    def test_awaiting_input_cannot_skip_to_terminal(target):
        with pytest.raises(InvalidStateTransitionError):
            validate_transition(JobStatus.AWAITING_INPUT, target)


    # TC-5.4: GET /availability returns MIP-003 contract
    @pytest.mark.asyncio
    async def test_availability_mip003_shape(client):
        async with client as c:
            r = await c.get("/availability")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "available"
        assert body["service_type"] == "masumi-agent"


    # TC-5.5: POST /start_job response has blockchainIdentifier (camelCase)
    @pytest.mark.asyncio
    async def test_start_job_has_blockchain_identifier_camel(client):
        async with client as c:
            job = await _create_job(c)
        assert "blockchainIdentifier" in job
        assert job["blockchainIdentifier"].startswith("mock_bc_")


    # TC-5.6: POST /start_job response has all four MIP-003 fields
    @pytest.mark.asyncio
    async def test_start_job_has_mip003_fields(client):
        async with client as c:
            job = await _create_job(c)
        assert "payByTime" in job
        assert "sellerVKey" in job
        assert "submitResultTime" in job
        assert "unlockTime" in job
        assert isinstance(job["payByTime"], int)
        assert isinstance(job["submitResultTime"], int)
        assert isinstance(job["unlockTime"], int)
        assert isinstance(job["sellerVKey"], str)


    # TC-5.7: payByTime is a future Unix timestamp
    @pytest.mark.asyncio
    async def test_pay_by_time_is_future(client):
        now = int(time.time())
        async with client as c:
            job = await _create_job(c)
        assert job["payByTime"] > now
        assert job["submitResultTime"] > job["payByTime"]
        assert job["unlockTime"] > job["submitResultTime"]


    # TC-5.8: Full regression — all previous tests still pass
    # (run via: pytest tests/ -v)
    def test_phase5_imports_cleanly():
        from app.domain.models import Job, JobStatus, LEGAL_TRANSITIONS
        from app.repository.job_repo import InMemoryJobRepository
        from app.routers.jobs import router
        from app.main import create_app
        assert len(JobStatus) == 5
        assert JobStatus.AWAITING_INPUT in LEGAL_TRANSITIONS
    ```

    AVOID:
    - Do NOT use `TestClient`.
    - Each async test gets its own fresh `create_app()` via the fixture.
  </action>
  <verify>pytest tests/test_phase5_mip003.py -v --tb=short</verify>
  <done>
    - All TC-5.x pass.
    - TC-5.3 parametrize produces 2 test cases.
    - TC-5.7 timestamp ordering verified.
  </done>
</task>

<task type="auto">
  <name>Run combined gate</name>
  <files>(no new files)</files>
  <action>
    Run: `pytest tests/ -v --tb=short`

    Common failure guides:
    - `blockchain_identifier` key missing in JSON → `Job.model_config` missing `populate_by_name=True` OR serialisation uses snake_case. Fix: `model_config = ConfigDict(..., populate_by_name=True)` and ensure FastAPI serialises with aliases (add `response_model_by_alias=True` to route or configure FastAPI app with `default_response_class`).
    - `payByTime` missing in JSON → same alias issue; `Job` needs `model_config` with `populate_by_name=True`.
    - TC-1.1 fails with "5 != 4" → `AWAITING_INPUT` not added to `JobStatus`.
    - TC-2.1 `pay_by_time` assertion fails → `repo.create()` not setting the new fields.
    - TC-3.3 `KeyError: 'status'` → `/availability` still returning old shape.
    - TC-3.8 `KeyError: 'queue_depth'` → old test still referencing removed key.

    > [!IMPORTANT]
    > FastAPI by default serialises Pydantic models using **field names**, not aliases. To make `blockchainIdentifier` appear in the JSON response, routes returning `Job` must use `response_model=Job` and the app or route must be configured with `response_model_by_alias=True`. The cleanest fix is to set this on each route that returns a `Job`:
    > ```python
    > @router.post("/start_job", status_code=201, response_model=Job, response_model_by_alias=True)
    > ```
    > Apply to `/start_job`, `/status/{job_id}`, and `/provide_input`.

    AVOID: Do NOT modify test files. Fix implementation only.
  </action>
  <verify>pytest tests/ -v --tb=short</verify>
  <done>
    - `pytest tests/` → all tests pass, 0 failed.
    - `blockchainIdentifier`, `payByTime`, `sellerVKey`, `submitResultTime`, `unlockTime` all present in API responses.
  </done>
</task>

## Must-Haves

- [ ] `test_phase1_models.py` — 5-member check + 2 new legal + 2 new illegal parametrize entries
- [ ] `test_phase2_repository.py` — TC-2.1 asserts 4 new MIP-003 fields
- [ ] `test_phase3_endpoints.py` — TC-3.3 checks `status`/`service_type`; TC-3.5 checks `blockchainIdentifier`; TC-3.8 updated
- [ ] `test_phase5_mip003.py` — 8 TCs (TC-5.3 produces 2 from parametrize = 9 runs total)

## Success Criteria

- [ ] `pytest tests/test_phase5_mip003.py -v` → all pass
- [ ] `pytest tests/` → **all pass, 0 failed**
- [ ] JSON responses contain `blockchainIdentifier`, `payByTime`, `sellerVKey`, `submitResultTime`, `unlockTime`
