"""Pydantic schemas for project integrations and Stock UMKM business events."""

from datetime import datetime
from typing import Any, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class IntegrationCreate(BaseModel):
    project_id: uuid.UUID
    name: str = Field(..., min_length=2, max_length=128)
    integration_type: str = Field(
        ...,
        pattern=r"^(laravel_api|mysql_readonly|pos_backend|prometheus|mqtt|custom)$",
    )
    configuration: dict[str, Any] = Field(default_factory=dict)
    secret_reference: Optional[str] = Field(default=None, max_length=128)


class IntegrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    integration_type: str
    configuration: dict[str, Any]
    secret_reference: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StockUmkmEventInput(BaseModel):
    event_id: str = Field(..., min_length=3, max_length=128)
    event_type: str = Field(
        ...,
        pattern=r"^(inventory\.updated|product\.updated|sale\.recorded|stock\.adjusted)$",
    )
    source: str = Field(default="stock_umkm", min_length=2, max_length=128)
    occurred_at: datetime
    data: dict[str, Any] = Field(..., min_length=1)

