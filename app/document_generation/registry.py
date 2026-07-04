from typing import Dict, Type
from app.document_generation.generators.base import BaseGenerator


class GeneratorRegistry:
    _generators: Dict[str, Type[BaseGenerator]] = {}

    @classmethod
    def register(cls, format: str, generator_cls: Type[BaseGenerator]):
        cls._generators[format.lower()] = generator_cls

    @classmethod
    def get(cls, format: str) -> BaseGenerator:
        fmt = format.lower()
        if fmt not in cls._generators:
            raise ValueError(f"Unsupported format: {format}. Supported: {list(cls._generators.keys())}")
        return cls._generators[fmt]()

    @classmethod
    def list_supported(cls) -> list:
        return list(cls._generators.keys())

    @classmethod
    def get_all(cls) -> Dict[str, Type[BaseGenerator]]:
        return dict(cls._generators)
