from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class StartJobRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    target_domain: AnyHttpUrl = Field(
        description='Target domain URL for analysis.',
    )
    my_product_usp: str = Field(
        min_length=1,
        max_length=500,
        description='Unique selling proposition of the product.',
    )
    ideal_customer_profile: str = Field(
        min_length=1,
        max_length=500,
        description='Ideal customer profile description.',
    )


class ProvideInputRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    job_id: str
    signature: str
    data: dict[str, Any]
