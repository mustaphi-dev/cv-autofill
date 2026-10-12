from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class Base(BaseModel):
    """Base of the generated profile models, for what JSON Schema cannot say:
    Zod trims text before checking it, never converts types ("5" is not a
    number), and treats a missing field and `null` differently."""

    model_config = ConfigDict(str_strip_whitespace=True, strict=True)

    @model_validator(mode="before")
    @classmethod
    def no_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict) and None in data.values():
            raise ValueError("null is not allowed; leave the field out")
        return data
