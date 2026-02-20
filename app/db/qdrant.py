from __future__ import annotations

from typing import Optional
from qdrant_client import AsyncQdrantClient

from app.core.config import settings

_client: Optional[AsyncQdrantClient] = None


def get_qdrant() -> AsyncQdrantClient:
    """FastAPI dependency — returns the shared async Qdrant client.

    Lazy-initialised on first call so that:
    - Tests can mock qdrant_client.AsyncQdrantClient via conftest.py BEFORE
      the client is ever constructed (import-time construction is skipped).
    - No TCP socket is opened during module import.

    Routers inject this via Depends(get_qdrant).
    """
    global _client
    if _client is None:
        _client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
    return _client
