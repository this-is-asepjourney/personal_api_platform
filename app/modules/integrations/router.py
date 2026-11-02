"""HTTP router for project integrations and Stock UMKM adapter endpoints."""

from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import Principal
from app.dependencies import require_any_scope, require_scopes
from app.modules.integrations.schemas import (
    IntegrationCreate,
    IntegrationRead,
    StockUmkmEventInput,
)
from app.modules.integrations.service import IntegrationService
from app.schemas import success_response

router = APIRouter(prefix="/integrations", tags=["Business Integrations"])


@router.get("")
def list_integrations(
    principal: Principal = Depends(require_any_scope("integrations:read", "projects:read")),
    db: Session = Depends(get_db),
):
    service = IntegrationService(db)
    items = service.list_integrations(principal)
    data = [IntegrationRead.model_validate(i).model_dump(mode="json") for i in items]
    return success_response(data=data, message="Integrations retrieved successfully")


@router.post("", status_code=status.HTTP_201_CREATED)
def create_integration(
    payload: IntegrationCreate,
    principal: Principal = Depends(require_any_scope("integrations:manage", "projects:manage")),
    db: Session = Depends(get_db),
):
    service = IntegrationService(db)
    item = service.create_integration(payload, principal)
    return success_response(
        data=IntegrationRead.model_validate(item).model_dump(mode="json"),
        message="Integration configured successfully",
    )


@router.get("/stock-umkm/products")
def list_stock_umkm_products(
    search: Optional[str] = Query(default=None),
    product_id: Optional[str] = Query(default=None),
    principal: Principal = Depends(require_scopes("inventory:read")),
    db: Session = Depends(get_db),
):
    service = IntegrationService(db)
    products = service.get_stock_umkm_products(search=search, product_id=product_id)
    return success_response(
        data=products,
        message="Approved Stock UMKM products retrieved successfully",
    )


@router.get("/stock-umkm/inventory")
def list_stock_umkm_inventory(
    product_id: Optional[str] = Query(default=None),
    principal: Principal = Depends(require_scopes("inventory:read")),
    db: Session = Depends(get_db),
):
    service = IntegrationService(db)
    inventory = service.get_stock_umkm_inventory(product_id=product_id)
    return success_response(
        data=inventory,
        message="Approved Stock UMKM inventory retrieved successfully",
    )


@router.post("/stock-umkm/events", status_code=status.HTTP_202_ACCEPTED)
def receive_stock_umkm_event(
    payload: StockUmkmEventInput,
    principal: Principal = Depends(require_any_scope("inventory:write", "transactions:write")),
    db: Session = Depends(get_db),
):
    service = IntegrationService(db)
    result = service.ingest_stock_umkm_event(payload, principal)
    return success_response(
        data=result,
        message="Integration event processed successfully",
    )


@router.get("/{integration_id}/health")
def check_integration_health(
    integration_id: uuid.UUID,
    principal: Principal = Depends(require_any_scope("integrations:read", "projects:read")),
    db: Session = Depends(get_db),
):
    service = IntegrationService(db)
    health = service.check_integration_health(integration_id, principal)
    return success_response(data=health, message="Integration health checked")

