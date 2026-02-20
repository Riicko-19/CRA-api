from typing import Any

from pydantic import BaseModel, ConfigDict


class StartJobRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    inputs: dict[str, Any]


class ProvideInputRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    job_id: str
    signature: str
    data: dict[str, Any]
