#!/usr/bin/env python3
"""Guard against committing MagicBox secrets.

Usage:
    uv run tools/check_secrets.py

Fails when:
  * inventory/group_vars/magicbox/vault.yml exists but is not ansible-vault
    encrypted;
  * a git-tracked or staged file assigns a non-empty value to a vault_* variable
    (only the git-ignored vault file and the throwaway test inventory may;
    values in angle brackets, e.g. "<password>", are documentation placeholders);
  * a git-tracked or staged file contains a private key block.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "inventory" / "group_vars" / "magicbox" / "vault.yml"
ALLOWED_PLAINTEXT = {"tests/container/hosts.yml"}
VAULT_ASSIGNMENT = re.compile(r"^\s*vault_[a-z0-9_]+:\s*['\"]?[^'\"\s#<]", re.MULTILINE)
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    return [ROOT / line for line in out.splitlines() if line]


def main() -> None:
    errors = []
    if VAULT.exists() and not VAULT.read_text(encoding="utf-8").startswith("$ANSIBLE_VAULT;"):
        errors.append(f"{VAULT.relative_to(ROOT)} is not encrypted; run `uv run ansible-vault encrypt {VAULT.relative_to(ROOT)}`")
    for path in tracked_files():
        rel = path.relative_to(ROOT).as_posix()
        if not path.is_file() or rel in ALLOWED_PLAINTEXT:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if VAULT_ASSIGNMENT.search(text):
            errors.append(f"{rel}: plaintext vault_* value")
        if PRIVATE_KEY.search(text):
            errors.append(f"{rel}: private key material")
    if errors:
        print("\n".join(f"ERROR {e}" for e in errors))
        sys.exit(f"{len(errors)} secret-handling problem(s) found")
    print("Secret checks passed.")


if __name__ == "__main__":
    main()
