from abc import ABC, abstractmethod


class AuthPort(ABC):

    @abstractmethod
    def is_authorized(self, provided_api_key: str | None) -> bool: ...
