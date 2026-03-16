import hmac

from app.core.config import settings
from app.ports.auth_port import AuthPort


class ApiKeyAuthAdapter(AuthPort):

    def is_authorized(self, provided_api_key: str | None) -> bool:
        if not provided_api_key:
            return False
        return hmac.compare_digest(provided_api_key, settings.api_key)
