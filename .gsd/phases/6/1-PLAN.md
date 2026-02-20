---
phase: 6
plan: 1
wave: 1
gap_closure: false
---

# Plan 6.1: Dependencies & Configuration

## Objective

Add masumi SDK + python-dotenv to `requirements.txt` and create `app/core/config.py` with Pydantic `BaseSettings` that loads four env vars and initialises the masumi `Config` object.

## Context

- `requirements.txt` — currently 6 deps, no masumi or dotenv
- `app/core/` — does not exist; must be created with `__init__.py`
- masumi `Config` signature: `Config(payment_service_url=..., payment_api_key=...)`

## Tasks

<task type="auto">
  <name>Update requirements.txt</name>
  <files>requirements.txt</files>
  <action>
    Add two lines to `requirements.txt`:

    ```
    masumi>=0.1.0
    python-dotenv>=1.0.0
    pydantic-settings>=2.0.0
    ```

    `pydantic-settings` is required for `BaseSettings` in Pydantic v2.
  </action>
  <verify>pip install -r requirements.txt --dry-run</verify>
</task>

<task type="auto">
  <name>Create app/core/__init__.py</name>
  <files>app/core/__init__.py</files>
  <action>Empty file.</action>
</task>

<task type="auto">
  <name>Create app/core/config.py</name>
  <files>app/core/config.py</files>
  <action>
    ```python
    from __future__ import annotations

    from pydantic_settings import BaseSettings
    from masumi import Config as MasumiConfig


    class Settings(BaseSettings):
        agent_identifier: str = "mock_agent_id"
        seller_vkey: str = "mock_seller_vkey"
        payment_service_url: str = "https://payment.masumi.network/api/v1"
        payment_api_key: str = "mock_api_key"
        masumi_network: str = "Preprod"

        model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


    settings = Settings()

    masumi_config = MasumiConfig(
        payment_service_url=settings.payment_service_url,
        payment_api_key=settings.payment_api_key,
    )
    ```

    KEY POINTS:
    - All fields have sensible mock defaults so the app starts without a .env file.
    - `masumi_config` is a module-level singleton — imported by job_service.py.
    - `seller_vkey` is loaded here so the service layer can use the real wallet key.
    - `masumi_network` defaults to "Preprod" (testnet) — set to "Mainnet" in production.
  </action>
  <verify>python -c "from app.core.config import settings, masumi_config; print(settings.payment_service_url)"</verify>
</task>

## Must-Haves

- [ ] `masumi`, `python-dotenv`, `pydantic-settings` in requirements.txt
- [ ] `app/core/__init__.py` exists
- [ ] `app/core/config.py` exports `settings` and `masumi_config`
- [ ] App starts without a `.env` file (all defaults present)

## Success Criteria

- [ ] `python -c "from app.core.config import masumi_config; print(type(masumi_config))"` — no import error
- [ ] `pytest tests/ -v` — still 50/50 (no regressions from config module)
