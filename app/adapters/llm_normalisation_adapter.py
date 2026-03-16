import json

import httpx

from app.core.config import settings
from app.ports.normalisation_port import NormalisationPort


class LLMNormalisationAdapter(NormalisationPort):

    async def normalise(self, raw_input: dict) -> dict:
        if not settings.openrouter_api_key:
            return raw_input

        prompt = (
            "Normalise this input into strict JSON with keys target_domain, "
            "my_product_usp, ideal_customer_profile. Return JSON only. Input: "
            f"{json.dumps(raw_input)}"
        )
        payload = {
            "model": "anthropic/claude-sonnet-4-5",
            "messages": [
                {"role": "system", "content": "You output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(settings.openrouter_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        return json.loads(content)

    async def health_check(self) -> bool:
        if not settings.openrouter_api_key:
            return True
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
                return response.status_code == 200
        except Exception:
            return False