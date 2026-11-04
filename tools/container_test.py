#!/usr/bin/env python3
"""End-to-end test of `make deploy` (playbooks/site.yml) in a disposable systemd container.

Usage:
    uv run tools/container_test.py [--keep] [--stacks all|NAME[,NAME...]]

Builds tests/container/Dockerfile, starts a privileged systemd container named
`magicbox-test`, runs playbooks/site.yml twice through
tools/idempotency_check.py (confirming destructive steps, which only affect
the container), and removes the container unless --keep is given.

Without --stacks only the host and Portainer are converged (tags `stacks` and
`apps` skipped). `--stacks all` runs the whole deployment, as `make deploy`
does (pulls about 6 GB of images and builds the Jenkins images);
`--stacks jenkins,kong` deploys only those stacks (stacks_enabled override;
the app jobs need `jenkins`).
Requires a local Docker daemon.

The container differs from MagicBox (architecture, nested Docker, no real LAN),
so a pass proves the roles converge and are idempotent, not that the LAN setup
on the real host works.
"""

from __future__ import annotations

import json
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
    args = sys.argv[1:]
    keep = "--keep" in args
    stacks: str | None = None
    if "--stacks" in args:
        index = args.index("--stacks")
        if index + 1 >= len(args) or args[index + 1].startswith("--"):
            sys.exit("--stacks needs 'all' or a comma-separated list of stack names")
        stacks = args[index + 1]
    # controller-verify is always skipped: the controller cannot resolve the
    # container's mDNS name.
    if stacks is None:
        selection = ["--skip-tags", "controller-verify,stacks,apps"]
    elif stacks == "all":
        selection = ["--skip-tags", "controller-verify"]
    else:
        names = [name.strip() for name in stacks.split(",") if name.strip()]
        selection = ["--skip-tags", "controller-verify", "-e", json.dumps({"stacks_enabled": names})]
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
            *selection,
        )
    finally:
        if not keep:
            sh("docker", "rm", "-f", NAME, check=False)
            sh("docker", "volume", "rm", "-f", f"{NAME}-docker", f"{NAME}-containerd", check=False)


if __name__ == "__main__":
    main()
