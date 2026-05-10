'''Idempotent script for creating all entities'''
from __future__ import annotations

from bootstrap.admin_api import KeycloakAdminApi
from bootstrap.config import BootstrapConfig
from bootstrap.spec import (
    SYSTEM_CLIENTS,
    build_clients,
    build_realm_settings,
    build_roles,
)


class KeycloakReconciler:
    def __init__(self, api: KeycloakAdminApi, config: BootstrapConfig) -> None:
        self.api = api
        self.config = config

    def apply(self) -> None:
        self._ensure_realm()
        self._verify_system_clients()
        self._ensure_roles()
        self._ensure_clients()
        self._ensure_service_account_roles()

    def _ensure_realm(self) -> None:
        desired_realm = build_realm_settings(self.config)
        existing_realm = self.api.get_realm(self.config.realm_name)
        if existing_realm is None:
            print(f"[keycloak-bootstrap] Creating realm {self.config.realm_name}")
            self.api.create_realm(desired_realm)
            return

        updated_realm = dict(existing_realm)
        changed = False
        for key, value in desired_realm.items():
            if updated_realm.get(key) != value:
                updated_realm[key] = value
                changed = True

        if changed:
            print(f"[keycloak-bootstrap] Updating realm settings for {self.config.realm_name}")
            self.api.update_realm(self.config.realm_name, updated_realm)

    def _verify_system_clients(self) -> None:
        for client_id in SYSTEM_CLIENTS:
            client = self.api.get_client_by_client_id(self.config.realm_name, client_id)
            if client is None:
                print(
                    f"[keycloak-bootstrap] Warning: built-in client {client_id!r} "
                    "is missing in Keycloak realm"
                )

    def _ensure_roles(self) -> None:
        for role in build_roles(self.config):
            existing_role = self.api.get_role(self.config.realm_name, role["name"])
            if existing_role is None:
                print(f"[keycloak-bootstrap] Creating realm role {role['name']}")
                self.api.create_role(self.config.realm_name, role)
                continue

            updated_role = dict(existing_role)
            changed = False
            for key, value in role.items():
                if updated_role.get(key) != value:
                    updated_role[key] = value
                    changed = True

            if changed:
                print(f"[keycloak-bootstrap] Updating realm role {role['name']}")
                self.api.update_role(self.config.realm_name, role["name"], updated_role)

    def _ensure_clients(self) -> None:
        for desired_client in build_clients(self.config):
            existing_client = self.api.get_client_by_client_id(
                self.config.realm_name,
                desired_client["clientId"],
            )
            if existing_client is None:
                print(f"[keycloak-bootstrap] Creating client {desired_client['clientId']}")
                self.api.create_client(self.config.realm_name, desired_client)
                continue

            updated_client = dict(existing_client)
            changed = False
            for key, value in desired_client.items():
                if updated_client.get(key) != value:
                    updated_client[key] = value
                    changed = True

            if changed:
                print(f"[keycloak-bootstrap] Updating client {desired_client['clientId']}")
                self.api.update_client(self.config.realm_name, existing_client["id"], updated_client)

    def _ensure_service_account_roles(self) -> None:
        """Назначает роль service-account сервисному аккаунту internal-service клиента."""
        client = self.api.get_client_by_client_id(
            self.config.realm_name,
            self.config.service_client_id,
        )
        if client is None:
            print(
                f"[keycloak-bootstrap] Warning: client {self.config.service_client_id!r} "
                "not found, skipping service account role assignment"
            )
            return

        service_account_user = self.api.get_service_account_user(
            self.config.realm_name,
            client["id"],
        )
        self._assign_missing_user_roles(
            service_account_user["id"],
            ["service-account"],
        )

    def _assign_missing_user_roles(self, user_id: str, desired_role_names: list[str]) -> None:
        current_roles = self.api.list_user_realm_roles(self.config.realm_name, user_id)
        current_role_names = {role["name"] for role in current_roles}

        missing_roles = [
            self.api.get_role(self.config.realm_name, role_name)
            for role_name in desired_role_names
            if role_name not in current_role_names
        ]
        role_representations = [role for role in missing_roles if role is not None]
        if role_representations:
            print(f"[keycloak-bootstrap] Assigning {len(role_representations)} realm roles to user {user_id}")
            self.api.add_user_realm_roles(self.config.realm_name, user_id, role_representations)