from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from app.core.config import limiter
from app.domain.models import Job, JobStatus
from app.ports.job_repository_port import JobRepositoryPort
from app.ports.normalisation_port import NormalisationPort
from app.ports.orchestrator_port import OrchestratorPort
from app.ports.payment_port import PaymentPort
from app.repository.job_repo import InMemoryJobRepository
from app.schemas.requests import StartJobRequest, ProvideInputRequest
from app.services import job_service
from app.services.agent_runner import execute_agent_task
from app.utils.hashing import hash_inputs
from app.utils.signatures import verify_signature

router = APIRouter()


def get_repo(request: Request) -> JobRepositoryPort:
    return request.app.state.repo


def get_payment(request: Request) -> PaymentPort:
    return request.app.state.payment


def get_normaliser(request: Request) -> NormalisationPort:
    return request.app.state.normaliser


def get_orchestrator(request: Request) -> OrchestratorPort:
    return request.app.state.orchestrator


@router.get("/availability")
async def availability(
    request: Request,
    repo: JobRepositoryPort = Depends(get_repo),
    payment: PaymentPort = Depends(get_payment),
    normaliser: NormalisationPort = Depends(get_normaliser),
):
    checks = {
        "masumi": await payment.health_check(),
        "openrouter": await normaliser.health_check(),
        "qdrant": bool(getattr(repo, "health_check", lambda: True)()),
    }
    if all(checks.values()):
        return {"status": "available", "service_type": "masumi-agent"}
    return {"status": "degraded", "service_type": "masumi-agent", "details": checks}


@router.get("/input_schema")
def input_schema():
    return StartJobRequest.model_json_schema()


@router.post("/start_job", status_code=201, response_model=Job, response_model_by_alias=True)
@limiter.limit("5/minute")
async def start_job(
    request: Request,
    body: StartJobRequest,
    background_tasks: BackgroundTasks,
    repo: JobRepositoryPort = Depends(get_repo),
    payment: PaymentPort = Depends(get_payment),
) -> Job:
    input_hash = hash_inputs(
        target_domain=str(body.target_domain),
        my_product_usp=body.my_product_usp,
        ideal_customer_profile=body.ideal_customer_profile,
    )
    job = await job_service.create_job(repo, payment, input_hash)
    return job


@router.get("/status/{job_id}", response_model=Job, response_model_by_alias=True)
def get_status(
    job_id: str,
    repo: JobRepositoryPort = Depends(get_repo),
) -> Job:
    return repo.get(job_id)


@router.post("/provide_input", response_model=Job, response_model_by_alias=True)
async def provide_input(
    body: ProvideInputRequest,
    background_tasks: BackgroundTasks,
    repo: JobRepositoryPort = Depends(get_repo),
    payment: PaymentPort = Depends(get_payment),
    normaliser: NormalisationPort = Depends(get_normaliser),
    orchestrator: OrchestratorPort = Depends(get_orchestrator),
) -> Job:
    job = repo.get(body.job_id)
    verify_signature(body.job_id, body.signature)
    paid = await job_service.verify_payment(payment, job.blockchain_identifier)
    if not paid:
        raise HTTPException(status_code=402, detail="Payment is not yet confirmed on-chain.")
    updated = job_service.advance_job_state(repo, body.job_id, JobStatus.RUNNING)
    background_tasks.add_task(
        execute_agent_task,
        body.job_id,
        repo,
        normaliser,
        orchestrator,
        body.data,
    )
    return updated