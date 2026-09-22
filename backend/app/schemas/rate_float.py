from pydantic import BaseModel, Field


class FloatEventCreate(BaseModel):
    effective_period: int = Field(gt=1)
    new_annual_rate: float = Field(ge=0)
    note: str = ""


class FloatEventUpdate(BaseModel):
    effective_period: int | None = Field(default=None, gt=1)
    new_annual_rate: float | None = Field(default=None, ge=0)
    note: str | None = None
