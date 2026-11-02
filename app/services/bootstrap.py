"""Bootstrap service for seeding canonical PAP scopes, roles, and Phase 3 connected projects."""

from sqlalchemy.orm import Session

from app.modules.clients.models import ApiClient
from app.modules.clients.repository import ClientRepository
from app.modules.database_registry.models import DatabaseConnection
from app.modules.database_registry.repository import DatabaseRegistryRepository
from app.modules.integrations.models import Integration
from app.modules.integrations.repository import IntegrationRepository
from app.modules.permissions.repository import PermissionsRepository
from app.modules.permissions.service import PermissionsService
from app.modules.projects.models import Project
from app.modules.projects.repository import ProjectRepository

CONNECTED_PROJECTS_SEED = [
    {
        "slug": "stock-umkm",
        "name": "Stock UMKM",
        "description": "Laravel product, inventory, and business event backend",
        "client_id": "stock-umkm-service",
        "client_name": "Stock UMKM Laravel Client",
        "client_type": "backend",
        "scopes": [
            "inventory:read",
            "inventory:write",
            "transactions:read",
            "transactions:write",
        ],
    },
    {
        "slug": "pos-cashier",
        "name": "POS Cashier",
        "description": "Next.js POS cashier backend for product lookup and sales integration",
        "client_id": "pos-cashier-backend",
        "client_name": "POS Cashier Backend Client",
        "client_type": "backend",
        "scopes": [
            "inventory:read",
            "inventory:write",
            "transactions:read",
            "transactions:write",
        ],
    },
    {
        "slug": "iot-dashboard",
        "name": "IoT Dashboard",
        "description": "Next.js IoT dashboard for ESP32 device registry, status, and telemetry",
        "client_id": "iot-dashboard-backend",
        "client_name": "IoT Dashboard Backend Client",
        "client_type": "backend",
        "scopes": [
            "iot:read",
            "iot:manage",
            "metrics:read",
        ],
    },
]


def seed_platform_registry(db: Session) -> dict[str, int]:
    """Idempotently seed canonical scopes, roles, and the initial homelab projects & clients."""
    perm_service = PermissionsService(db)
    perm_service.seed_defaults()

    perm_repo = PermissionsRepository(db)
    project_repo = ProjectRepository(db)
    client_repo = ClientRepository(db)
    db_reg_repo = DatabaseRegistryRepository(db)
    integration_repo = IntegrationRepository(db)

    projects_created = 0
    clients_created = 0

    for item in CONNECTED_PROJECTS_SEED:
        project = project_repo.get_by_slug(item["slug"])
        if not project:
            project = project_repo.create(
                Project(
                    slug=item["slug"],
                    name=item["name"],
                    description=item["description"],
                    status="active",
                )
            )
            projects_created += 1

        client = client_repo.get_by_client_id(item["client_id"])
        scopes = [
            s
            for s_name in item["scopes"]
            if (s := perm_repo.get_scope_by_name(s_name)) is not None
        ]
        if not client:
            client_repo.create_client(
                ApiClient(
                    project_id=project.id,
                    client_id=item["client_id"],
                    name=item["client_name"],
                    client_type=item["client_type"],
                    is_active=True,
                    scopes=scopes,
                )
            )
            clients_created += 1

        if item["slug"] == "stock-umkm":
            if not db_reg_repo.get_by_name("stock-umkm-mysql"):
                db_reg_repo.create(
                    DatabaseConnection(
                        project_id=project.id,
                        name="stock-umkm-mysql",
                        engine="mysql",
                        host="100.106.63.90",
                        port=3306,
                        database_name="stock_umkm",
                        username="pap_stock_reader",
                        secret_reference="STOCK_DB_PASSWORD",
                        allowed_tables=["products", "inventories", "categories"],
                        read_only=True,
                        is_active=True,
                    )
                )
            if not integration_repo.get_by_name("stock-umkm-laravel-api"):
                integration_repo.create(
                    Integration(
                        project_id=project.id,
                        name="stock-umkm-laravel-api",
                        integration_type="laravel_api",
                        configuration={"base_url": "http://192.168.25.101:8080/api"},
                        secret_reference="STOCK_UMKM_API_KEY",
                        is_active=True,
                    )
                )

    return {
        "projects_created": projects_created,
        "clients_created": clients_created,
    }

