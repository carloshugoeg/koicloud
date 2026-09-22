from __future__ import annotations

from typing import Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict


class SchemaModel(BaseModel):
    """Base schema with a stable config and example helpers."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    _example_key: ClassVar[str] = "example"

    @classmethod
    def example_data(cls) -> Any:
        extra = cls.model_config.get("json_schema_extra", {})
        if cls._example_key not in extra:
            raise ValueError(f"{cls.__name__} is missing json_schema_extra.example")
        return extra[cls._example_key]

    @classmethod
    def example(cls) -> Self:
        return cls.model_validate(cls.example_data())
