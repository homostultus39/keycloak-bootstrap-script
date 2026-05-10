'''Entrypoint for Keycloak bootstrap script'''

from __future__ import annotations

import argparse
import sys
import time
from urllib.error import HTTPError, URLError

from bootstrap.admin_api import KeycloakAdminApi
from bootstrap.config import BootstrapConfig
from bootstrap.reconciler import KeycloakReconciler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap Keycloak realm and project-owned IAM objects.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate bootstrap config and Keycloak readiness without applying changes.",
    )
    return parser.parse_args()


def wait_until_ready(api: KeycloakAdminApi, config: BootstrapConfig) -> None:
    deadline = time.monotonic() + config.readiness_timeout_seconds
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            api.authenticate()
            return
        except (HTTPError, URLError, RuntimeError) as exc:
            last_error = exc
            time.sleep(config.readiness_poll_interval_seconds)

    raise RuntimeError("Keycloak admin API did not become ready in time") from last_error


def main() -> int:
    args = parse_args()
    config = BootstrapConfig.from_env()

    if not config.enabled:
        print("[keycloak-bootstrap] Bootstrap is disabled, skipping")
        return 0

    api = KeycloakAdminApi(config)
    wait_until_ready(api, config)

    if args.dry_run:
        print("[keycloak-bootstrap] Dry run completed: Keycloak is reachable and admin auth works")
        return 0

    reconciler = KeycloakReconciler(api, config)
    reconciler.apply()
    print("[keycloak-bootstrap] Bootstrap completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
