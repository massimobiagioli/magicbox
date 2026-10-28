# MagicBox Technology Stack

Versions are those pinned in the repository on 2026-10-28. Change them only
together with `make check` and `make test-container`.

## Controller (operator workstation)

| Component | Version | Pinned in | Rationale |
|-----------|---------|-----------|-----------|
| uv | 0.13.x or newer (tested 0.13.5) | installed by the operator | Fast, lockfile-based Python environment and dependency manager (ADR-0001) |
| Python | 3.14 (`>=3.12,<3.15` allowed) | `.python-version`, `pyproject.toml` | Supported controller Python for ansible-core 2.21 |
| .venv | project-local, created by `uv sync --locked` | `uv.lock` | Isolates tooling from system Python; reproducible |
| ansible-core | 2.21.5 | `pyproject.toml`, `uv.lock` | Current stable Ansible engine; controller Python 3.12-3.14 |
| ansible-lint | 26.10.1 | `pyproject.toml` (`dev` group) | Lints playbooks and roles (production profile) |
| yamllint | 1.38.0 | `pyproject.toml` (`dev` group) | YAML style and syntax |
| markdown | 3.11.2 | `pyproject.toml` (`docs` group) | Markdown to HTML for manuals (ADR-0007) |
| fpdf2 | 2.8.9 | `pyproject.toml` (`docs` group) | Pure-Python PDF generation, no system libraries (ADR-0007) |
| Docker (Desktop/Engine) | any recent | optional | Only for `make test-container` |
| GNU make | system | - | Entry points in `Makefile` |

## Ansible collections

| Collection | Version | Used for |
|------------|---------|----------|
| community.general | 13.5.0 | `community.general.ufw` |
| community.docker | 5.4.0 | `docker_container`, `docker_volume`, docker connection plugin for tests |
| community.crypto | 3.5.1 | Local CA, keys, CSRs, certificates, certificate info |

Pinned in `requirements.yml`, installed into `.ansible/collections`.

## Target (MagicBox)

| Component | Version | Source | Rationale |
|-----------|---------|--------|-----------|
| Hardware | GMKtec Intel Mini PC, `x86_64` | - | Low-power always-on host |
| OS | Ubuntu Server 24.04/26.04 LTS or Debian 12/13 (Ubuntu 24.04 recommended) | OS installer | Docker CE support, LTS lifecycle (ADR-0002) |
| Python 3 | distribution default (3.11-3.14) | OS | Required by Ansible modules |
| python3-requests, python3-cryptography, python3-debian | distribution | apt | Needed by community.docker, community.crypto and `deb822_repository` |
| Avahi (avahi-daemon, avahi-utils, libnss-mdns) | distribution | apt (avahi-daemon first installed by hand) | mDNS responder for `magicbox.local`; MagicBox has a dynamic IP (ADR-0003) |
| ufw | distribution | apt | Host firewall (ADR-0004) |
| Docker Engine (docker-ce, cli, containerd.io, buildx, compose plugins) | 29.x (apt-pinned major) | download.docker.com, key fingerprint verified | Official, current engine (ADR-0002) |
| Portainer CE | 2.45.3 (LTS) | `portainer/portainer-ce:2.45.3` | Web UI for Docker management; LTS channel for stability |

## Runtime layout on MagicBox

| Path / object | Purpose |
|---------------|---------|
| `portainer_data` (Docker volume) | Portainer database and settings (persistent) |
| `/opt/magicbox/portainer/certs/` | `ca.key`, `ca.crt`, `portainer.key`, `portainer.csr`, `portainer.crt` |
| `/opt/magicbox/portainer/secrets/admin_password` | Bootstrap admin password (root 0600) |
| `/etc/docker/daemon.json` | Log rotation, live-restore |
| `/etc/apt/preferences.d/docker-ce.pref` | Docker major-version pin |
| `/etc/avahi/avahi-daemon.conf` | mDNS publishing on the LAN interface |
| `/etc/systemd/resolved.conf.d/magicbox-mdns.conf` | Disables resolved's mDNS/LLMNR |

## Network

| Port | Protocol | Service | Allowed from |
|------|----------|---------|--------------|
| 22 | TCP | SSH | `magicbox_lan_cidr` |
| 9443 | TCP | Portainer HTTPS | `magicbox_lan_cidr` |
| 5353 | UDP | mDNS (Avahi) | `magicbox_lan_cidr` |
| 9000 | TCP | Portainer HTTP | disabled (`--http-disabled`) |
| 8000 | TCP | Portainer Edge tunnel | blocked (unused) |
| 2375/2376 | TCP | Docker API | never enabled |
