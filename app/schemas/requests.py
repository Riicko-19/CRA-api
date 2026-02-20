from typing import Any

from pydantic import BaseModel, ConfigDict


class StartJobRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    inputs: dict[str, Any]
