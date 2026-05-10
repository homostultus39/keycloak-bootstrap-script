'''Configuration file for Keycloak bootstrap script'''


from __future__ import annotations
from dataclasses import dataclass
import os

@dataclass(slots=True)
class BootstrapConfig:
    enabled: bool = True

    internal_url: str
    admin_username: str
    admin_password: str
    admin_realm: str = "master"
    admin_client_id: str = "admin-cli"
    
    realm_name: str = "prod-realm"
    realm_display_name: str = "Production Realm"
    
    django_client_id: str = "django-app"
    django_client_secret: str = "your-secure-secret"
    django_base_url: str = "http://localhost:8000"
    internal_service_client_id: str = "internal-service"
    service_client_secret: str = "some-secure-secret-for-internal-service"

    request_timeout_seconds: float = 10.0
    readiness_timeout_seconds: int = 60
    readiness_poll_interval_seconds: float = 2.0

    keycloak_access_token_lifespan_seconds: int = 300
    keycloak_sso_session_idle_seconds: int = 1800
    keycloak_sso_session_max_seconds: int = 36000
    keycloak_client_session_idle_seconds: int = 0
    keycloak_client_session_max_seconds: int = 0

    request_timeout_seconds: float = 10.0
    readiness_timeout_seconds: int = 60
    readiness_poll_interval_seconds: float = 2.0

    @classmethod
    def from_env(cls) -> BootstrapConfig:
        return cls(
            internal_url=os.getenv("KEYCLOAK_URL", "http://localhost:8080"),
            admin_username=os.getenv("KEYCLOAK_ADMIN_USER", "admin"),
            admin_password=os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin"),
            enabled=os.getenv("KEYCLOAK_BOOTSTRAP_ENABLED", "true").lower() == "true",
            realm_name=os.getenv("TARGET_REALM", "prod-realm"),
            django_client_id=os.getenv("DJANGO_CLIENT_ID", "django-app"),
            django_client_secret=os.getenv("DJANGO_CLIENT_SECRET", "some-secure-secret"),
            django_base_url=os.getenv("DJANGO_BASE_URL", "http://localhost:8000"),
            service_client_id=os.getenv("SERVICE_CLIENT_ID", "internal-service"),
            service_client_secret=os.getenv("SERVICE_CLIENT_SECRET", "some-service-secret"),
        )