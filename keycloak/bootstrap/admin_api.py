'''Main class for keycloak admin API interactions.'''

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

from bootstrap.config import BootstrapConfig


class KeycloakAdminApi:
    def __init__(self, config: BootstrapConfig) -> None:
        self.config = config
        self._access_token: str | None = None

    def authenticate(self) -> None:
        body = self._request_form_json(
            self._openid_token_path(self.config.admin_realm),
            payload={
                "client_id": self.config.admin_client_id,
                "grant_type": "password",
                "username": self.config.admin_username,
                "password": self.config.admin_password,
            },
            include_access_token=False,
        )
        access_token = body.get("access_token")
        if not access_token:
            raise RuntimeError("Keycloak admin authentication did not return access_token")
        self._access_token = access_token

    def get_realm(self, realm_name: str) -> dict[str, Any] | None:
        try:
            return self.request_json("GET", self._realm_admin_path(realm_name))
        except HTTPError as exc:
            if exc.code == 404:
                return None
            raise

    def create_realm(self, payload: dict[str, Any]) -> None:
        self.request_json("POST", "/admin/realms", payload=payload, expected_statuses={201, 204})

    def update_realm(self, realm_name: str, payload: dict[str, Any]) -> None:
        self.request_json("PUT", self._realm_admin_path(realm_name), payload=payload, expected_statuses={204})

    def list_roles(self, realm_name: str) -> list[dict[str, Any]]:
        return self.request_json("GET", self._realm_admin_path(realm_name, "roles"))

    def get_role(self, realm_name: str, role_name: str) -> dict[str, Any] | None:
        try:
            return self.request_json("GET", self._realm_admin_path(realm_name, "roles", role_name))
        except HTTPError as exc:
            if exc.code == 404:
                return None
            raise

    def create_role(self, realm_name: str, payload: dict[str, Any]) -> None:
        self.request_json(
            "POST",
            self._realm_admin_path(realm_name, "roles"),
            payload=payload,
            expected_statuses={201, 204},
        )

    def update_role(self, realm_name: str, role_name: str, payload: dict[str, Any]) -> None:
        self.request_json(
            "PUT",
            self._realm_admin_path(realm_name, "roles", role_name),
            payload=payload,
            expected_statuses={204},
        )

    def get_client_by_client_id(self, realm_name: str, client_id: str) -> dict[str, Any] | None:
        clients = self.request_json(
            "GET",
            f"{self._realm_admin_path(realm_name, 'clients')}?clientId={quote(client_id)}",
        )
        return clients[0] if clients else None

    def create_client(self, realm_name: str, payload: dict[str, Any]) -> None:
        self.request_json(
            "POST",
            self._realm_admin_path(realm_name, "clients"),
            payload=payload,
            expected_statuses={201, 204},
        )

    def update_client(self, realm_name: str, client_uuid: str, payload: dict[str, Any]) -> None:
        self.request_json(
            "PUT",
            self._realm_admin_path(realm_name, "clients", client_uuid),
            payload=payload,
            expected_statuses={204},
        )

    def get_user_by_username(self, realm_name: str, username: str) -> dict[str, Any] | None:
        users = self.request_json(
            "GET",
            f"{self._realm_admin_path(realm_name, 'users')}?username={quote(username)}&exact=true",
        )
        return users[0] if users else None

    def create_user(self, realm_name: str, payload: dict[str, Any]) -> None:
        self.request_json(
            "POST",
            self._realm_admin_path(realm_name, "users"),
            payload=payload,
            expected_statuses={201, 204},
        )

    def update_user(self, realm_name: str, user_id: str, payload: dict[str, Any]) -> None:
        self.request_json(
            "PUT",
            self._realm_admin_path(realm_name, "users", user_id),
            payload=payload,
            expected_statuses={204},
        )

    def reset_user_password(self, realm_name: str, user_id: str, password: str) -> None:
        self.request_json(
            "PUT",
            self._realm_admin_path(realm_name, "users", user_id, "reset-password"),
            payload={
                "type": "password",
                "value": password,
                "temporary": False,
            },
            expected_statuses={204},
        )

    def list_user_realm_roles(self, realm_name: str, user_id: str) -> list[dict[str, Any]]:
        return self.request_json(
            "GET",
            self._realm_admin_path(realm_name, "users", user_id, "role-mappings", "realm"),
        )

    def add_user_realm_roles(
        self,
        realm_name: str,
        user_id: str,
        roles: list[dict[str, Any]],
    ) -> None:
        if not roles:
            return
        self.request_json(
            "POST",
            self._realm_admin_path(realm_name, "users", user_id, "role-mappings", "realm"),
            payload=roles,
            expected_statuses={204},
        )

    def get_service_account_user(self, realm_name: str, client_uuid: str) -> dict[str, Any]:
        return self.request_json(
            "GET",
            self._realm_admin_path(realm_name, "clients", client_uuid, "service-account-user"),
        )

    @staticmethod
    def _realm_admin_path(realm_name: str, *segments: str) -> str:
        encoded_segments = "/".join(quote(segment) for segment in segments)
        base = f"/admin/realms/{quote(realm_name)}"
        return f"{base}/{encoded_segments}" if encoded_segments else base

    @staticmethod
    def _openid_token_path(realm_name: str) -> str:
        return f"/realms/{quote(realm_name)}/protocol/openid-connect/token"

    def _request_form_json(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        include_access_token: bool,
        expected_statuses: set[int] | None = None,
    ) -> Any:
        if expected_statuses is None:
            expected_statuses = {200}

        request = Request(
            f"{self.config.internal_url.rstrip('/')}{path}",
            data=urlencode(payload).encode("utf-8"),
            method="POST",
        )
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
        request.add_header("Accept", "application/json")
        if include_access_token and self._access_token:
            request.add_header("Authorization", f"Bearer {self._access_token}")

        with urlopen(request, timeout=self.config.request_timeout_seconds) as response:
            if response.status not in expected_statuses:
                raise RuntimeError(f"Unexpected Keycloak response status {response.status} for POST {path}")
            body = response.read().decode("utf-8")
            if not body:
                return None
            return json.loads(body)

    def request_json(
        self,
        method: str,
        path: str,
        payload: Any | None = None,
        expected_statuses: set[int] | None = None,
    ) -> Any:
        if expected_statuses is None:
            expected_statuses = {200}

        request = Request(
            f"{self.config.internal_url.rstrip('/')}{path}",
            method=method,
        )
        request.add_header("Accept", "application/json")
        if self._access_token:
            request.add_header("Authorization", f"Bearer {self._access_token}")

        if payload is not None:
            request.add_header("Content-Type", "application/json")
            request.data = json.dumps(payload).encode("utf-8")

        with urlopen(request, timeout=self.config.request_timeout_seconds) as response:
            if response.status not in expected_statuses:
                raise RuntimeError(
                    f"Unexpected Keycloak response status {response.status} for {method} {path}"
                )
            body = response.read().decode("utf-8")
            if not body:
                return None
            return json.loads(body)
