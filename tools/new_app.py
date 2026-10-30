#!/usr/bin/env python3
"""Create a new MagicBox app from templates/python-fastapi-app and register it.

Usage:
    uv run tools/new_app.py <name> [--dest DIR] [--repo URL] [--port N] [--create-repo]

Steps:
  1. copy the template to DIR (default: <parent of this repository>/<name>),
     rename the project, run `uv lock`, `git init -b main` and a first commit;
  2. add the app to the apps registry inventory/group_vars/magicbox/apps.yml
     (git-ignored; created if missing): name, the first free port from 18001,
     repo https://github.com/<stacks_jenkins_github_user>/<name> unless --repo;
  3. with --create-repo, create the private GitHub repository and push
     (`gh repo create`, needs an authenticated GitHub CLI).

Then run `make apps`: Kong route https://magicbox.local/<name> and Jenkins
job <name>, whose first scan builds and deploys `main` (ADR-0017).
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "python-fastapi-app"
REGISTRY = ROOT / "inventory" / "group_vars" / "magicbox" / "apps.yml"
HOSTS = ROOT / "inventory" / "hosts.yml"
NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# Paths already routed by Kong (roles/stacks/vars/main.yml: stacks_kong_routes,
# stacks_kong_port_redirects).
BUILT_IN = {"portainer", "jenkins", "grafana", "rabbitmq", "ollama", "rustfs"}
FIRST_PORT, LAST_PORT = 18001, 18999
REGISTRY_HEADER = """---
# MagicBox apps registry (git-ignored; template: inventory/apps.example.yml).
# Maintained by `uv run tools/new_app.py`; applied by `make apps`.
magicbox_apps:
"""


def fail(message: str) -> None:
    sys.exit(f"ERROR {message}")


def run(*cmd: str, cwd: Path) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def load_registry() -> list[dict]:
    if not REGISTRY.exists():
        return []
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8")) or {}
    return data.get("magicbox_apps") or []


def github_user() -> str | None:
    if not HOSTS.exists():
        return None
    group = (yaml.safe_load(HOSTS.read_text(encoding="utf-8")) or {}).get("all", {})
    magicbox = group.get("children", {}).get("magicbox", {})
    candidates = [magicbox.get("vars") or {}, *(magicbox.get("hosts") or {}).values()]
    for scope in candidates:
        if (scope or {}).get("stacks_jenkins_github_user"):
            return scope["stacks_jenkins_github_user"]
    return None


def register(name: str, port: int, repo: str) -> None:
    entry = f"  - name: {name}\n    port: {port}\n    repo: {repo}\n"
    original = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else None
    text = original if original is not None else REGISTRY_HEADER
    # An empty registry may be written as "magicbox_apps: []".
    text = re.sub(r"^magicbox_apps:\s*\[\]\s*$", "magicbox_apps:", text, flags=re.MULTILINE)
    REGISTRY.write_text(text.rstrip("\n") + "\n" + entry, encoding="utf-8")
    # Entries are appended at the end of the file: refuse if magicbox_apps is not last.
    if not any(app.get("name") == name for app in load_registry()):
        if original is None:
            REGISTRY.unlink()
        else:
            REGISTRY.write_text(original, encoding="utf-8")
        fail(f"could not append to {REGISTRY.relative_to(ROOT)}: magicbox_apps must be the last key")


def create_project(name: str, dest: Path) -> None:
    shutil.copytree(
        TEMPLATE, dest,
        ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache", ".ruff_cache"),
    )
    replacements = {
        "pyproject.toml": [
            ('name = "python-fastapi-app"', f'name = "{name}"'),
            ('description = "FastAPI application template (uv, Docker)"',
             f'description = "MagicBox app {name} (FastAPI, uv, Docker)"'),
        ],
        "app/main.py": [('title="python-fastapi-app"', f'title="{name}"')],
        "compose.yaml": [("python-fastapi-app:local", f"{name}:local")],
        "README.md": [("# python-fastapi-app\n", f"# {name}\n\nURL: `https://magicbox.local/{name}`\n")],
    }
    for relative, pairs in replacements.items():
        path = dest / relative
        text = path.read_text(encoding="utf-8")
        for old, new in pairs:
            if old not in text:
                fail(f"template changed: '{old}' not found in {relative}")
            text = text.replace(old, new, 1)
        path.write_text(text, encoding="utf-8")
    run("uv", "lock", cwd=dest)
    run("git", "init", "-q", "-b", "main", cwd=dest)
    run("git", "add", "-A", cwd=dest)
    run("git", "commit", "-q", "-m", f"feat: {name} from the MagicBox python-fastapi-app template", cwd=dest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("name", help="app name: Jenkins job, stack, container and URL path")
    parser.add_argument("--dest", type=Path, help="project directory (default: ../<name>)")
    parser.add_argument("--repo", help="GitHub HTTPS URL (default: from stacks_jenkins_github_user)")
    parser.add_argument("--port", type=int, help=f"host port ({FIRST_PORT}-{LAST_PORT}; default: first free)")
    parser.add_argument("--create-repo", action="store_true", help="create the private GitHub repo and push (gh)")
    args = parser.parse_args()

    name = args.name
    if not NAME.match(name) or name in BUILT_IN:
        fail(f"invalid name '{name}': lowercase letters, digits, hyphens; not {sorted(BUILT_IN)}")
    apps = load_registry()
    if any(app.get("name") == name for app in apps):
        fail(f"'{name}' is already in {REGISTRY.relative_to(ROOT)}")
    used = {int(app["port"]) for app in apps if "port" in app}
    port = args.port or next((p for p in range(FIRST_PORT, LAST_PORT + 1) if p not in used), None)
    if port is None or port in used or not FIRST_PORT <= port <= LAST_PORT:
        fail(f"port {port} is used or outside {FIRST_PORT}-{LAST_PORT}")
    repo = args.repo
    if not repo:
        user = github_user()
        if not user:
            fail("pass --repo https://github.com/<owner>/<name> or set stacks_jenkins_github_user in inventory/hosts.yml")
        repo = f"https://github.com/{user}/{name}"
    match = re.match(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$", repo)
    if not match:
        fail(f"repo must be https://github.com/<owner>/<repository>, got {repo}")
    dest = (args.dest or ROOT.parent / name).expanduser().resolve()
    if dest.exists():
        fail(f"{dest} already exists")

    create_project(name, dest)
    register(name, port, repo)
    print(f"Registered {name}: port {port}, repo {repo} ({REGISTRY.relative_to(ROOT)})")
    if args.create_repo:
        run("gh", "repo", "create", f"{match[1]}/{match[2]}", "--private",
            "--source", str(dest), "--remote", "origin", "--push", cwd=dest)
    else:
        run("git", "remote", "add", "origin", f"{repo}.git", cwd=dest)

    print(f"""
Next steps:
  {"" if args.create_repo else f"- create the private GitHub repository {repo}, then: git -C {dest} push -u origin main"}
  - the GitHub token of Jenkins (credential `github`) must be able to read it
  - make apps    # Kong route https://magicbox.local/{name} + Jenkins job {name} (first build starts)""")


if __name__ == "__main__":
    main()
