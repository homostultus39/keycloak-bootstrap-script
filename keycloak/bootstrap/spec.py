'''Fully editable Keycloak realm configuration specification.'''

from __future__ import annotations

from typing import Any

from bootstrap.config import BootstrapConfig


SYSTEM_CLIENTS = (
    "account",
    "account-console",
    "admin-cli",
    "broker",
    "realm-management",
    "security-admin-console",
)

def build_realm_settings(config: BootstrapConfig) -> dict[str, Any]:
    return {
        "realm": config.realm_name,
        "enabled": True,
        "displayName": config.realm_display_name,
        "registrationAllowed": False,
        "resetPasswordAllowed": True,
        "rememberMe": True,
        "verifyEmail": True,
        "loginWithEmailAllowed": True,
        "duplicateEmailsAllowed": False,
        "accessTokenLifespan": config.keycloak_access_token_lifespan_seconds,
        "ssoSessionIdleTimeout": config.keycloak_sso_session_idle_seconds,
        "ssoSessionMaxLifespan": config.keycloak_sso_session_max_seconds,
        "clientSessionIdleTimeout": config.keycloak_client_session_idle_seconds,
        "clientSessionMaxLifespan": config.keycloak_client_session_max_seconds,
    }


def build_roles() -> list[dict[str, Any]]:
    return [
        {"name": "admin", "description": "Administrator with full access"},
        {"name": "user", "description": "Regular platform user"},
        {"name": "service-account", "description": "Role for machine-to-machine auth"},
    ]


def build_clients(config: BootstrapConfig) -> list[dict[str, Any]]:
    default_client_scopes = ["profile", "email", "roles", "web-origins"]

    return [
        {
            "clientId": config.django_client_id,
            "name": "Django Application",
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "secret": config.django_client_secret,
            "serviceAccountsEnabled": True,
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": False,
            "frontchannelLogout": False,
            "redirectUris": [
                f"{config.django_base_url.rstrip('/')}/oidc/callback/",
                f"{config.django_base_url.rstrip('/')}/accounts/keycloak/login/callback/"
            ],
            "webOrigins": [
                config.django_base_url.rstrip("/"),
            ],
            "attributes": {
                "pkce.code.challenge.method": "S256",
                "post.logout.redirect.uris": f"{config.django_base_url.rstrip('/')}/",
                "backchannel.logout.session.required": "true",
                "backchannel.logout.revoke.offline.tokens": "false",
            },
            "defaultClientScopes": default_client_scopes,
        },
        {
            "clientId": config.internal_service_client_id,
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "secret": config.service_client_secret,
            "serviceAccountsEnabled": True,
            "standardFlowEnabled": False,
            "directAccessGrantsEnabled": False,
            "frontchannelLogout": False,
            "attributes": {},
            "defaultClientScopes": ["roles"],
        }
    ]