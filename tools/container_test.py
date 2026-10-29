#!/usr/bin/env python3
"""End-to-end test of playbooks/site.yml against a disposable systemd container.

Usage:
    uv run tools/container_test.py [--keep] [--with-stacks] [--with-ci-cd] [--with-api-gateway]

Builds tests/container/Dockerfile, starts a privileged systemd container named
`magicbox-test`, runs the playbook twice through tools/idempotency_check.py
(confirming destructive steps, which only affect the container), and removes
the container unless --keep is given. With --with-stacks it then runs
playbooks/stacks.yml twice as well (pulls about 4 GB of images); with
--with-ci-cd it runs playbooks/ci-cd.yml twice (builds the Jenkins images);
with --with-api-gateway it runs playbooks/api-gateway.yml twice (Kong).
Requires a local Docker daemon.

The container differs from MagicBox (architecture, nested Docker, no real LAN),
so a pass proves the roles converge and are idempotent, not that the LAN setup
on the real host works.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "magicbox-test"
IMAGE = "magicbox-test:local"


def sh(*cmd: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=check, text=True)


def main() -> None:
    keep = "--keep" in sys.argv[1:]
    with_stacks = "--with-stacks" in sys.argv[1:]
    with_ci_cd = "--with-ci-cd" in sys.argv[1:]
    with_api_gateway = "--with-api-gateway" in sys.argv[1:]
    sh("docker", "build", "-q", "-t", IMAGE, str(ROOT / "tests/container"))
    sh("docker", "rm", "-f", NAME, check=False)
    sh("docker", "volume", "rm", "-f", f"{NAME}-docker", f"{NAME}-containerd", check=False)
    sh(
        "docker", "run", "-d", "--name", NAME, "--hostname", NAME,
        "--privileged", "--cgroupns=host",
        "-v", "/sys/fs/cgroup:/sys/fs/cgroup:rw",
        "--tmpfs", "/run", "--tmpfs", "/run/lock",
        # Nested overlayfs needs real (volume-backed) storage directories.
        "-v", f"{NAME}-docker:/var/lib/docker",
        "-v", f"{NAME}-containerd:/var/lib/containerd",
        IMAGE,
    )
    try:
        sh(
            sys.executable, str(ROOT / "tools/idempotency_check.py"),
            "-i", str(ROOT / "tests/container/hosts.yml"),
            str(ROOT / "playbooks/site.yml"),
            "-e", "magicbox_confirm_destructive=true",
            # The controller cannot resolve the container's mDNS name.
            "--skip-tags", "controller-verify",
        )
        if with_stacks:
            sh(
                sys.executable, str(ROOT / "tools/idempotency_check.py"),
                "-i", str(ROOT / "tests/container/hosts.yml"),
                str(ROOT / "playbooks/stacks.yml"),
            )
        if with_ci_cd:
            sh(
                sys.executable, str(ROOT / "tools/idempotency_check.py"),
                "-i", str(ROOT / "tests/container/hosts.yml"),
                str(ROOT / "playbooks/ci-cd.yml"),
            )
        if with_api_gateway:
            sh(
                sys.executable, str(ROOT / "tools/idempotency_check.py"),
                "-i", str(ROOT / "tests/container/hosts.yml"),
                str(ROOT / "playbooks/api-gateway.yml"),
            )
    finally:
        if not keep:
            sh("docker", "rm", "-f", NAME, check=False)
            sh("docker", "volume", "rm", "-f", f"{NAME}-docker", f"{NAME}-containerd", check=False)


if __name__ == "__main__":
    main()
