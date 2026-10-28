#!/usr/bin/env python3
"""Run an Ansible playbook twice and fail if the second run changes anything.

Usage:
    uv run tools/idempotency_check.py [ansible-playbook arguments...]

Example:
    uv run tools/idempotency_check.py playbooks/site.yml --ask-vault-pass

All arguments are passed unchanged to both `ansible-playbook` runs. The script
exits non-zero when either run fails or the second run reports changed > 0.
"""

from __future__ import annotations

import re
import subprocess
import sys

RECAP_LINE = re.compile(r"^(?P<host>\S+)\s*:\s*ok=\d+\s+changed=(?P<changed>\d+)\s+unreachable=(?P<unreachable>\d+)\s+failed=(?P<failed>\d+)")


def run_playbook(args: list[str], label: str) -> dict[str, int]:
    """Run ansible-playbook, stream its output and return changed counts per host."""
    print(f"==> {label}: ansible-playbook {' '.join(args)}", flush=True)
    proc = subprocess.Popen(
        ["ansible-playbook", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    changed: dict[str, int] = {}
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        match = RECAP_LINE.match(line.strip())
        if match:
            changed[match["host"]] = int(match["changed"])
    if proc.wait() != 0:
        sys.exit(f"{label} failed with exit code {proc.returncode}")
    if not changed:
        sys.exit(f"{label}: no PLAY RECAP found")
    return changed


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    run_playbook(args, "first run")
    second = run_playbook(args, "second run")
    drift = {host: count for host, count in second.items() if count}
    if drift:
        sys.exit(f"NOT idempotent, second run changed tasks: {drift}")
    print("Idempotency check passed: second run reported changed=0 on all hosts.")


if __name__ == "__main__":
    main()
