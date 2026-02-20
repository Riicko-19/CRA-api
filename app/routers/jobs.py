from fastapi import APIRouter, Depends, Request

from app.domain.models import Job
from app.repository.job_repo import InMemoryJobRepository
from app.schemas.requests import StartJobRequest
from app.services import job_service
from app.utils.hashing import hash_inputs

router = APIRouter()


def get_repo(request: Request) -> InMemoryJobRepository:
    return request.app.state.repo


@router.get("/availability")
def availability(repo: InMemoryJobRepository = Depends(get_repo)):
    return {"available": True, "queue_depth": repo.count()}


@router.get("/input_schema")
def input_schema():
    return StartJobRequest.model_json_schema()


@router.post("/start_job", status_code=201)
def start_job(
    body: StartJobRequest,
    repo: InMemoryJobRepository = Depends(get_repo),
) -> Job:
    input_hash = hash_inputs(body.inputs)
    job = job_service.create_job(repo, input_hash)
    return job
