import json

import httpx

from app.core.config import settings
from app.ports.orchestrator_port import OrchestratorPort


class OrchestratorAdapter(OrchestratorPort):

    async def execute(self, job_id: str, normalised_input: dict) -> str:
        if settings.orchestrator_url.startswith("mock://"):
            return json.dumps({"job_id": job_id, "result": normalised_input}, sort_keys=True)

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                settings.orchestrator_url,
                json={"job_id": job_id, "input": normalised_input},
            )
            response.raise_for_status()
            data = response.json()
        return str(data.get("result", data))