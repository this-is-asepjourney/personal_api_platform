"""Service for business integration registry and Stock UMKM / POS Cashier adapter operations."""

from typing import Any, Optional
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import Principal
from app.integrations.mqtt import MqttAdapter
from app.integrations.prometheus import PrometheusAdapter
from app.integrations.stock_umkm import StockUmkmAdapter
from app.modules.audit.service import AuditService
from app.modules.integrations.models import Integration, IntegrationEvent
from app.modules.integrations.repository import IntegrationRepository
from app.modules.integrations.schemas import IntegrationCreate, StockUmkmEventInput
from app.modules.projects.repository import ProjectRepository
from app.modules.webhooks.service import WebhookService


class IntegrationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = IntegrationRepository(db)
        self.project_repo = ProjectRepository(db)
        self.webhook_service = WebhookService(db)
        self.audit = AuditService(db)
        self.stock_adapter = StockUmkmAdapter()

    def list_integrations(self, principal: Principal) -> list[Integration]:
        allowed = None if principal.is_admin else principal.allowed_project_ids
        return self.repo.list_integrations(allowed_project_ids=allowed)

    def create_integration(
        self, payload: IntegrationCreate, principal: Principal
    ) -> Integration:
        project = self.project_repo.get_by_id(payload.project_id)
        if not project:
            raise NotFoundError(message="Project not found", code="PROJECT_NOT_FOUND")
        principal.require_project_access(project.id)

        if self.repo.get_by_name(payload.name):
            raise ConflictError(
                message=f"Integration '{payload.name}' already exists",
                code="INTEGRATION_EXISTS",
            )

        integration = Integration(
            project_id=project.id,
            name=payload.name,
            integration_type=payload.integration_type,
            configuration=payload.configuration,
            secret_reference=payload.secret_reference,
            is_active=True,
        )
        created = self.repo.create(integration)
        self.audit.record(
            action="integration.created",
            resource="integrations",
            resource_id=str(created.id),
            project_id=project.id,
            principal=principal,
            details={"name": created.name, "type": created.integration_type},
        )
        return created

    def check_integration_health(
        self, integration_id: uuid.UUID, principal: Principal
    ) -> dict[str, Any]:
        integration = self.repo.get_by_id(integration_id)
        if not integration:
            raise NotFoundError(message="Integration not found", code="INTEGRATION_NOT_FOUND")
        principal.require_project_access(integration.project_id)

        if integration.integration_type == "prometheus":
            status_info = PrometheusAdapter().check_health()
        elif integration.integration_type == "mqtt":
            status_info = MqttAdapter().check_health()
        else:
            status_info = self.stock_adapter.check_health()

        return {
            "integration_id": str(integration.id),
            "name": integration.name,
            "integration_type": integration.integration_type,
            "is_active": integration.is_active,
            "upstream": status_info,
        }

    def get_stock_umkm_products(
        self,
        search: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        return self.stock_adapter.list_products(search=search, product_id=product_id)

    def get_stock_umkm_inventory(
        self, product_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        items = self.stock_adapter.list_inventory(product_id=product_id)
        by_product = {item["product_id"]: item for item in items}

        # Apply committed inventory.updated events idempotently
        events = self.repo.list_events_by_type("inventory.updated")
        for ev in events:
            pid = str(ev.data.get("product_id", ""))
            qty = ev.data.get("quantity")
            if pid and isinstance(qty, (int, float)):
                if pid in by_product:
                    by_product[pid]["quantity"] = int(qty)
                    by_product[pid]["available"] = max(
                        0, int(qty) - int(by_product[pid].get("reserved", 0))
                    )
                elif not product_id or product_id == pid:
                    by_product[pid] = {
                        "product_id": pid,
                        "sku": f"UMKM-PROD-{pid}",
                        "warehouse": "main",
                        "quantity": int(qty),
                        "reserved": 0,
                        "available": int(qty),
                    }

        return list(by_product.values())

    def ingest_stock_umkm_event(
        self, payload: StockUmkmEventInput, principal: Principal
    ) -> dict[str, Any]:
        existing = self.repo.get_event_by_event_id(payload.event_id)
        if existing:
            return {
                "id": str(existing.id),
                "event_id": existing.event_id,
                "event_type": existing.event_type,
                "source": existing.source,
                "status": existing.status,
                "idempotent_replay": True,
                "webhook_deliveries": 0,
            }

        event_record = self.repo.create_event(
            IntegrationEvent(
                event_id=payload.event_id,
                event_type=payload.event_type,
                source=payload.source,
                occurred_at=payload.occurred_at,
                data=payload.data,
                status="processed",
            )
        )
        deliveries = self.webhook_service.dispatch_event(
            event_id=payload.event_id,
            event_type=payload.event_type,
            payload=payload.model_dump(mode="json"),
        )
        self.audit.record(
            action="integration.event_received",
            resource="integration_events",
            resource_id=str(event_record.id),
            principal=principal,
            details={
                "event_id": payload.event_id,
                "event_type": payload.event_type,
                "source": payload.source,
                "webhook_deliveries": len(deliveries),
            },
        )
        return {
            "id": str(event_record.id),
            "event_id": event_record.event_id,
            "event_type": event_record.event_type,
            "source": event_record.source,
            "status": event_record.status,
            "idempotent_replay": False,
            "webhook_deliveries": len(deliveries),
        }

