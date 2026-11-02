"""Service for monitoring homelab infrastructure and PAP operational state."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations.mqtt import MqttAdapter
from app.integrations.prometheus import PrometheusAdapter
from app.integrations.stock_umkm import StockUmkmAdapter
from app.modules.monitoring.repository import MonitoringRepository


class MonitoringService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = MonitoringRepository(db)

    def get_services_status(self) -> list[dict[str, Any]]:
        db_ok = False
        try:
            self.db.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            db_ok = False

        prom_status = PrometheusAdapter().check_health()
        mqtt_status = MqttAdapter().check_health()
        stock_status = StockUmkmAdapter().check_health()

        return [
            {
                "name": "pap_core_database",
                "status": "healthy" if db_ok else "unhealthy",
                "reachable": db_ok,
            },
            {
                "name": "prometheus",
                "port": 9001,
                "status": "healthy" if prom_status.get("reachable") else "standby",
                **prom_status,
            },
            {
                "name": "mosquitto_mqtt",
                "port": 1883,
                **mqtt_status,
            },
            {
                "name": "stock_umkm_adapter",
                **stock_status,
            },
        ]

    def get_overview(self) -> dict[str, Any]:
        devices_total, devices_online = self.repo.count_devices()
        return {
            "projects_total": self.repo.count_projects(),
            "active_clients_total": self.repo.count_active_clients(),
            "devices_total": devices_total,
            "devices_online": devices_online,
            "webhooks_active": self.repo.count_active_webhooks(),
            "services": self.get_services_status(),
        }

