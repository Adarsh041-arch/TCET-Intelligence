from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseGenerator(ABC):
    @abstractmethod
    def generate(self, html: str, template: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None) -> bytes:
        pass

    @abstractmethod
    def generate_preview(self, html: str, template: Optional[Dict[str, Any]] = None) -> bytes:
        pass

    @property
    @abstractmethod
    def format(self) -> str:
        pass

    @property
    @abstractmethod
    def mime_type(self) -> str:
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        pass
