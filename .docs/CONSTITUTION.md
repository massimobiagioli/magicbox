# MagicBox Constitution

## Purpose

MagicBox is a GMKtec Intel Mini PC on a home/office LAN that runs containers
managed through Portainer CE. This repository is the single source of truth
for turning a freshly installed MagicBox into that host, reproducibly and
securely, and for documenting how to operate it.

## Scope

In scope:

- Host baseline: OS checks, hostname, base packages (`preflight` role).
- LAN name resolution as `magicbox.local` via mDNS (`mdns` role).
- Host firewall restricting management access to the LAN (`firewall` role).
- Docker Engine from Docker's official repository (`docker` role).
- Portainer CE with persistent storage, HTTPS and a bootstrap admin
  (`portainer` role).
- Controller tooling (uv, `.venv`, Ansible), project tools, tests,
  documentation, ADRs and PDF manuals.

Out of scope (until an ADR says otherwise): the workloads deployed through
Portainer, router/DNS configuration, remote access from outside the LAN,
backups of workload data, monitoring, multi-host clusters.

## Requirements

1. Portainer is reachable from other LAN computers at
   `https://magicbox.local:9443/` with a certificate that validates once the
   MagicBox CA is trusted.
2. `magicbox.local` resolves on the LAN via mDNS from macOS, Windows 10/11 and
   Linux clients with nss-mdns; fallbacks are documented.
3. Portainer data lives in the named Docker volume `portainer_data` and
   survives container recreation, upgrades and reboots.
4. Docker and Portainer start automatically after reboot.
5. SSH, Portainer and mDNS are reachable only from `magicbox_lan_cidr`; all
   other inbound traffic is denied.
6. The Docker API is never exposed over TCP, and no unauthenticated Portainer
   setup window exists.
7. No secrets are committed; secrets live in an ansible-vault encrypted file.
8. Destructive operations require explicit per-run confirmation
   (`magicbox_confirm_destructive=true`).
9. Dependencies are pinned: Python packages (`pyproject.toml`, `uv.lock`),
   Ansible collections (`requirements.yml`), Docker major version, Portainer
   image tag.
10. Everything is written in English: code, comments, docs, manuals, commit
    messages.

## Governance

- Changes go through version control with a descriptive English commit
  message. Significant decisions (new component, security posture, network
  exposure, supported versions, data handling) require a new ADR in
  `.docs/adr/` listed in `.docs/adr/registry.md` and `CLAUDE.md`.
- ADRs are immutable once accepted, except for their status; reversing a
  decision means a new ADR that supersedes the old one.
- Any change to a role, variable, tag or playbook updates
  `manuals/src/magicbox-playbook.md` and rebuilds the PDFs in the same change.
  `tools/check_docs.py` enforces coverage of roles, variables and tags.
- `make check` must pass before merging. Role changes should also pass
  `make test-container`.
- Helper programs are added to `tools/` and listed in `CLAUDE.md` (ADR-0009).

## Constraints

- Hardware: one GMKtec Intel Mini PC, `x86_64`.
- OS: Ubuntu Server 24.04/26.04 LTS or Debian 12/13 (ADR-0002). The concrete
  OS on MagicBox must be confirmed by the owner before the first deployment.
- Addressing: MagicBox has a dynamic (DHCP) IP and is always addressed as
  `magicbox.local`, including by Ansible and SSH (ADR-0003). No fixed IP.
- Access: SSH with key authentication from a controller inside the LAN, as a
  sudo-capable user. Environment facts (user, interface, subnet) are never
  guessed; they are provided in the git-ignored `inventory/hosts.yml`.
- `.local` names cannot get public certificates; trust relies on the local CA
  (ADR-0005).
- mDNS is link-local: it does not cross routed subnets or VLANs (ADR-0003).

## Acceptance Criteria

The infrastructure is accepted when all of the following hold:

| # | Criterion | How it is verified |
|---|-----------|--------------------|
| 1 | `make check` passes (syntax, yamllint, ansible-lint production profile, secret check, manual build, documentation checks) | Controller |
| 2 | `make test-container` passes: full converge and second run with `changed=0` | Controller with Docker |
| 3 | `make deploy` completes on MagicBox and its `verify` tasks pass (self-resolution of `magicbox.local`, no `dockerd` TCP listener, Portainer status over HTTPS with CA validation, version match) | MagicBox |
| 4 | `make idempotency` against MagicBox reports `changed=0` on the second run | MagicBox |
| 5 | From another LAN computer with the CA trusted, `https://magicbox.local:9443/` loads without a certificate warning and the admin can log in | LAN client |
| 6 | After `sudo reboot`, criterion 5 holds again without manual action and Portainer settings are preserved | LAN client |
| 7 | From outside `magicbox_lan_cidr`, ports 22 and 9443 are unreachable; port 9000 is closed everywhere | Network test |
