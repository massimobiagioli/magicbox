"""Create or update the app's Portainer stack from deploy/stack.yml (standard library only).

Run by the Jenkinsfile inside the CI image, on the MagicBox host network:

    docker run --rm --network host --add-host magicbox.local:127.0.0.1 \
      -v /opt/magicbox/portainer/certs/ca.crt:/run/magicbox-ca.crt:ro \
      -v /opt/magicbox/apps:/run/magicbox-apps:ro \
      -e PORTAINER_TOKEN -e APP_NAME -e IMAGE_TAG <ci-image> python deploy/portainer_deploy.py

The Jenkins agent cannot reach Portainer itself: ufw admits port 9443 only from
the LAN, not from Docker networks. A container on the host network reaches it on
the loopback interface, and the MagicBox CA validates its certificate. The host
port of the app comes from the MagicBox apps registry (apps.json, `make apps`).

Environment:
    PORTAINER_TOKEN     API token (Jenkins credential "portainer-api-token"), required
    APP_NAME            app name = Jenkins job = Portainer stack, required
    IMAGE_TAG           image tag to deploy, required
    PORTAINER_URL       default: https://magicbox.local:9443
    PORTAINER_ENDPOINT  Portainer environment name (default: homelab)
    PORTAINER_CA        default: /run/magicbox-ca.crt
    APPS_REGISTRY       default: /run/magicbox-apps/apps.json
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

STACK_FILE = Path(__file__).with_name("stack.yml")


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        sys.exit(f"{name} is not set")
    return value


def app_port(registry_file: str, app_name: str) -> int:
    try:
        registry = json.loads(Path(registry_file).read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"{registry_file} not found: run `make apps` in the magicbox repository")
    if app_name not in registry:
        sys.exit(
            f"App '{app_name}' is not in the MagicBox apps registry: add it to "
            "inventory/group_vars/magicbox/apps.yml and run `make apps`"
        )
    return int(registry[app_name])


class Portainer:
    def __init__(self, url: str, token: str, ca_file: str) -> None:
        self.url = url.rstrip("/")
        self.token = token
        self.context = ssl.create_default_context(cafile=ca_file)

    def call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        request = urllib.request.Request(
            self.url + path,
            method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers={"X-API-Key": self.token, "Content-Type": "application/json"},
        )
        try:
            # Image is already built on MagicBox, but the stack update can take a while.
            with urllib.request.urlopen(request, context=self.context, timeout=300) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            sys.exit(f"{method} {path}: HTTP {error.code} {error.read().decode(errors='replace')}")


def main() -> None:
    app_name = env("APP_NAME")
    endpoint_name = env("PORTAINER_ENDPOINT", "homelab")
    port = app_port(env("APPS_REGISTRY", "/run/magicbox-apps/apps.json"), app_name)
    stack_env = [
        {"name": "APP_NAME", "value": app_name},
        {"name": "APP_PORT", "value": str(port)},
        {"name": "IMAGE_TAG", "value": env("IMAGE_TAG")},
    ]
    portainer = Portainer(
        env("PORTAINER_URL", "https://magicbox.local:9443"),
        env("PORTAINER_TOKEN"),
        env("PORTAINER_CA", "/run/magicbox-ca.crt"),
    )

    query = urllib.parse.urlencode({"name": endpoint_name})
    endpoints = [
        e for e in portainer.call("GET", f"/api/endpoints?{query}") if e["Name"] == endpoint_name
    ]
    if len(endpoints) != 1:
        sys.exit(f"Portainer environment '{endpoint_name}' not found")
    endpoint_id = endpoints[0]["Id"]

    stacks = [
        s
        for s in portainer.call("GET", "/api/stacks")
        if s["Name"] == app_name and s["EndpointId"] == endpoint_id
    ]
    compose = STACK_FILE.read_text(encoding="utf-8")
    if stacks:
        portainer.call(
            "PUT",
            f"/api/stacks/{stacks[0]['Id']}?endpointId={endpoint_id}",
            {"stackFileContent": compose, "env": stack_env, "prune": True, "pullImage": False},
        )
        action = "Updated"
    else:
        portainer.call(
            "POST",
            f"/api/stacks/create/standalone/string?endpointId={endpoint_id}",
            {"name": app_name, "stackFileContent": compose, "env": stack_env},
        )
        action = "Created"
    print(f"{action} stack '{app_name}' (image tag {env('IMAGE_TAG')}, 127.0.0.1:{port})")


if __name__ == "__main__":
    main()
