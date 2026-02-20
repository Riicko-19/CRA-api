from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.domain.models import Job, JobStatus
from app.repository.job_repo import InMemoryJobRepository
from app.schemas.requests import StartJobRequest, ProvideInputRequest
from app.services import job_service
from app.utils.hashing import hash_inputs
from app.utils.signatures import verify_signature

router = APIRouter()


def get_repo(request: Request) -> InMemoryJobRepository:
    return request.app.state.repo


@router.get("/availability")
def availability():
    return {"status": "available", "service_type": "masumi-agent"}


@router.get("/input_schema")
def input_schema():
    return StartJobRequest.model_json_schema()


@router.post("/start_job", status_code=201, response_model=Job, response_model_by_alias=True)
def start_job(
    body: StartJobRequest,
    repo: InMemoryJobRepository = Depends(get_repo),
) -> Job:
    input_hash = hash_inputs(body.inputs)
    job = job_service.create_job(repo, input_hash)
    return job


@router.get("/status/{job_id}", response_model=Job, response_model_by_alias=True)
def get_status(
    job_id: str,
    repo: InMemoryJobRepository = Depends(get_repo),
) -> Job:
    return repo.get(job_id)


@router.post("/provide_input", response_model=Job, response_model_by_alias=True)
def provide_input(
    body: ProvideInputRequest,
    repo: InMemoryJobRepository = Depends(get_repo),
) -> Job:
    repo.get(body.job_id)  # raises JobNotFoundError if missing
    verify_signature(body.job_id, body.signature)  # raises InvalidSignatureError if invalid
    job_service.advance_job_state(repo, body.job_id, JobStatus.RUNNING)
    updated = job_service.advance_job_state(
        repo, body.job_id, JobStatus.COMPLETED, result="Task executed successfully"
    )
    return updated
