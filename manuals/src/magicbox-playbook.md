# MagicBox Playbook Reference

Reference for every Ansible recipe in this repository: purpose, variables,
commands, tags, prerequisites, verification and operational risks. It matches
the code at the time of the build; `tools/check_docs.py` fails if a role,
variable or tag is missing from this document.

Pinned toolchain: ansible-core 2.21.5 (Python 3.14 `.venv` managed by uv),
community.general 13.5.0, community.docker 5.4.0, community.crypto 3.5.1.

## 1. Overview

| Item | Value |
|------|-------|
| Playbook | `playbooks/site.yml` |
| Inventory | `inventory/hosts.yml` (git-ignored; template `inventory/hosts.example.yml`) |
| Group | `magicbox` |
| Project policy | `inventory/group_vars/magicbox/main.yml` |
| Secrets | `inventory/group_vars/magicbox/vault.yml` (ansible-vault, git-ignored) |
| Collections | `requirements.yml`, installed to `.ansible/collections` |
| Result | Portainer CE at `https://magicbox.local:9443/`, LAN only |

Play 1, *Configure MagicBox*, runs on group `magicbox` with `become: true` and
applies the roles in this order: `preflight`, `mdns`, `firewall`, `docker`,
`portainer`. Play 2, *Verify Portainer from the Ansible controller*, queries
Portainer from the controller over the LAN.

## 2. Commands

| Goal | Command |
|------|---------|
| Create the environment | `make setup` |
| All local checks | `make check` |
| Container converge + idempotency test | `make test-container` |
| First deployment | `make deploy EXTRA="-K -e magicbox_confirm_destructive=true"` |
| Routine deployment | `make deploy EXTRA="-K"` |
| Only one area | `uv run ansible-playbook playbooks/site.yml --ask-vault-pass -K --tags docker` |
| Dry run with diff | `uv run ansible-playbook playbooks/site.yml --ask-vault-pass -K --check --diff` |
| Verification only | `make verify EXTRA="-K"` |
| Idempotency on MagicBox | `make idempotency VAULT_PASSWORD_FILE=<file> EXTRA="--become-password-file=<file>"` |
| List tasks / tags | `uv run ansible-playbook playbooks/site.yml --list-tasks` / `--list-tags` |

`-K` asks for the sudo password; omit it if `<admin-user>` has passwordless
sudo. A `--check` run cannot complete the `docker` and `portainer` roles on a
fresh host because the packages they verify are not installed yet.

## 3. Tags

| Tag | Selects |
|-----|---------|
| `preflight` | The `preflight` role |
| `always` | Also on `preflight`: it runs with any `--tags` selection, so checks and facts are always present |
| `mdns` | The `mdns` role |
| `firewall` | The `firewall` role |
| `docker` | The `docker` role |
| `portainer` | The `portainer` role, including TLS tasks |
| `tls` | Only TLS provisioning inside `portainer` (certificate renewal, CA fetch) |
| `verify` | Verification tasks in all roles plus the controller play |
| `controller-verify` | Only the controller play; skipped by the container test |

`--tags verify` runs `preflight` (tagged `always`) and every `verify` task. It
changes nothing on a converged host.

## 4. Shared variables

Defined in `inventory/hosts.yml` (environment facts) or
`inventory/group_vars/magicbox/main.yml` (project policy).

| Variable | Default | Description |
|----------|---------|-------------|
| `magicbox_lan_interface` | required | LAN interface on MagicBox (`ip -br link`). Avahi publishes only here. |
| `magicbox_lan_cidr` | required | Private LAN subnet allowed to reach SSH, Portainer and mDNS. |
| `magicbox_hostname` | `magicbox` | Hostname and mDNS name (`<name>.local`); single DNS label. |
| `magicbox_expected_architecture` | `x86_64` | Asserted CPU architecture. |
| `magicbox_supported_os` | Ubuntu 24.04/26.04, Debian 12/13 | Asserted OS/version map (ADR-0002). |
| `magicbox_confirm_destructive` | `false` | Allows destructive steps for one run (ADR-0008). Pass with `-e`. |
| `portainer_admin_password` | `{{ vault_portainer_admin_password }}` | Bootstrap admin password, from the vault. |
| `vault_portainer_admin_password` | required (vault) | At least 12 characters; in `vault.yml` only. |

## 5. Role `preflight`

**Purpose.** Fail fast on unsupported or misconfigured hosts and prepare the
baseline: OS/architecture/inventory/vault assertions, LAN CIDR validation,
detection of where the SSH controller connects from, hostname, base packages.

**Prerequisites.** SSH key login as a sudo-capable user; Python 3 on the host
(present on Ubuntu/Debian server installs).

| Variable | Default | Description |
|----------|---------|-------------|
| `preflight_base_packages` | ca-certificates, curl, gnupg, iproute2, python3-cryptography, python3-debian, python3-requests | Packages needed by later roles and modules. |
| `preflight_manage_hostname` | `true` | Set the static hostname and `127.0.1.1` entry. `false` only in the test container. |

**Facts set.** `preflight_controller_location`: `inside`, `outside` or
`unknown` (no `SSH_CLIENT`, e.g. the container test), consumed by `firewall`.

**Verification.** All assertions run on every play (tag `always`).

**Risks.** Changing `magicbox_hostname` renames the host and the mDNS name;
certificates must match (`portainer_tls_dns_names` follows automatically, the
existing CA's name constraints do not: rotate the CA, installation guide 8.5).

## 6. Role `mdns`

**Purpose.** Publish `magicbox.local` on the LAN with Avahi (ADR-0003).
Installs `mdns_packages`, disables systemd-resolved's mDNS/LLMNR responders
when systemd-resolved is installed, templates `/etc/avahi/avahi-daemon.conf`
(host name, `allow-interfaces`, no HINFO/workstation publishing, no reflector,
no wide-area), and enables `avahi-daemon`.

| Variable | Default | Description |
|----------|---------|-------------|
| `mdns_use_ipv6` | `true` | Publish AAAA records. Set `false` if clients pick unreachable IPv6 addresses. |
| `mdns_packages` | avahi-daemon, avahi-utils, libnss-mdns | Responder, CLI tools, NSS module for local resolution. |

**Handlers.** *Restart systemd-resolved*, *Restart avahi-daemon*.

**Verification.** `avahi-resolve-host-name -4 magicbox.local` must return an
address (retries 5 x 2 s).

**Risks.** Avahi renames the host to `magicbox-2.local` if another device
already claims the name; TLS then fails the name check. Restricting to
`magicbox_lan_interface` means the name is invisible on other interfaces.

## 7. Role `firewall`

**Purpose.** Enable ufw with default deny inbound and allow only SSH,
`firewall_lan_tcp_ports` and `firewall_lan_udp_ports` from
`magicbox_lan_cidr` (ADR-0004). Rules persist across reboots.

| Variable | Default | Description |
|----------|---------|-------------|
| `firewall_ssh_port` | `22` | SSH port allowed from the LAN. |
| `firewall_lan_tcp_ports` | `[9443]` | TCP ports allowed from the LAN (Portainer). |
| `firewall_lan_udp_ports` | `[5353]` | UDP ports allowed from the LAN (mDNS). |
| `firewall_logging` | `low` | ufw logging level. |

**Safety rails.** Refuses first activation unless
`magicbox_confirm_destructive=true`; always refuses when
`preflight_controller_location` is `outside`.

**Verification.** `sudo ufw status verbose` (manual); the controller play
proves 9443 is reachable from the LAN.

**Risks.** A wrong `magicbox_lan_cidr` can lock out SSH from other subnets
(console recovery: installation guide 8.2). Rules for ports no longer listed
are not removed automatically; delete them with `sudo ufw delete <n>`. Ports
published by containers on Docker bridge networks bypass ufw.

## 8. Role `docker`

**Purpose.** Install Docker Engine from Docker's apt repository with a
verified signing key and a major-version pin, configure the daemon, and enable
`containerd` and `docker` at boot (ADR-0002).

| Variable | Default | Description |
|----------|---------|-------------|
| `docker_major_version` | `"29"` | apt preference pin `5:29.*` for docker-ce, cli, rootless-extras. |
| `docker_apt_key_url` | `https://download.docker.com/linux/<distro>/gpg` | Signing key URL. |
| `docker_apt_key_fingerprint` | `9DC858229FC7DD38854AE2D88D81803C0EBFCD88` | Expected key fingerprint; mismatch aborts. |
| `docker_apt_key_path` | `/etc/apt/keyrings/docker.asc` | Keyring path referenced by the deb822 source. |
| `docker_packages` | docker-ce, docker-ce-cli, containerd.io, docker-buildx-plugin, docker-compose-plugin | Installed packages. |
| `docker_conflicting_packages` | docker.io, docker-doc, docker-compose, docker-compose-v2, podman-docker, containerd, runc | Removed only with confirmation. |
| `docker_log_max_size` | `10m` | json-file log rotation size. |
| `docker_log_max_file` | `3` | json-file rotated files kept. |

**Files.** `/etc/apt/sources.list.d/docker.sources`,
`/etc/apt/preferences.d/docker-ce.pref`, `/etc/docker/daemon.json`
(validated with `dockerd --validate` before replacement; `live-restore`
enabled).

**Handlers.** *Restart docker* (containers survive thanks to live-restore).

**Verification.** No `dockerd` TCP listener (`ss -Hltnp`).

**Risks.** Removing conflicting packages stops workloads that used them. A
daemon restart briefly interrupts the Docker API. A major upgrade requires
changing `docker_major_version` deliberately.

## 9. Role `portainer`

**Purpose.** Run Portainer CE with persistent data, HTTPS on 9443 using the
MagicBox CA, plain HTTP disabled, and a pre-set admin password (ADR-0004,
ADR-0005, ADR-0006). Container: `portainer`, image
`portainer/portainer-ce:2.45.3`, restart policy `unless-stopped`,
`network_mode: host`; mounts the Docker socket, the `portainer_data` volume,
the certificate directory (read-only) and the password file (read-only).

| Variable | Default | Description |
|----------|---------|-------------|
| `portainer_image` | `portainer/portainer-ce` | Image repository. |
| `portainer_version` | `"2.45.3"` | Image tag (LTS); also asserted against the API. |
| `portainer_container_name` | `portainer` | Container name. |
| `portainer_https_port` | `9443` | HTTPS port (keep in `firewall_lan_tcp_ports`). |
| `portainer_data_volume` | `portainer_data` | Persistent named volume mounted at `/data`. |
| `portainer_base_dir` | `/opt/magicbox/portainer` | Host base directory. |
| `portainer_cert_dir` | `<base>/certs` | TLS material (0700). |
| `portainer_secret_dir` | `<base>/secrets` | Admin password file (0700). |
| `portainer_tls_mode` | `local_ca` | `local_ca` or `provided`. |
| `portainer_tls_dns_names` | `magicbox.local`, `magicbox` | Certificate SANs and CA name constraints. |
| `portainer_tls_ip_addresses` | `[]` | Optional IP SANs/constraints (e.g. the reserved IP). |
| `portainer_tls_ca_common_name` | `MagicBox Local CA (magicbox)` | CA subject CN. |
| `portainer_tls_ca_valid_for` | `+3650d` | CA lifetime. |
| `portainer_tls_cert_valid_for` | `+397d` | Server certificate lifetime. |
| `portainer_tls_renew_before` | `+30d` | Re-issue window before expiry. |
| `portainer_tls_ca_fetch_dest` | `artifacts/magicbox-local-ca.crt` | Controller copy of the CA for clients. |
| `portainer_tls_provided_cert_src` | empty | `provided` mode: server certificate path on the controller. |
| `portainer_tls_provided_key_src` | empty | `provided` mode: server key path (keep it vaulted). |
| `portainer_tls_provided_ca_src` | empty | `provided` mode: issuing CA path. |

**TLS tasks (`tls_local_ca.yml`).** CA key (ECDSA P-384) and self-signed CA
(`CA:TRUE, pathlen:0`, critical name constraints) created once; server key
(ECDSA P-256), CSR and certificate (EKU `serverAuth`) signed by the CA and
re-issued when within `portainer_tls_renew_before` of expiry or when the SANs
change; CA fetched to the controller.

**Handlers.** *Restart portainer* when TLS material changes.

**Verification.** `GET https://magicbox.local:9443/api/system/status` from
MagicBox with CA validation (retries 20 x 3 s) and an assertion that the
reported version equals `portainer_version`. The controller play repeats the
request over the LAN.

**Risks.** Portainer controls the Docker socket and is root-equivalent:
every Portainer admin is root on MagicBox. Changing the vault password after
first start does not change the admin password. Deleting `portainer_cert_dir`
creates a new CA that clients must trust again. Deleting the
`portainer_data` volume erases all Portainer settings; the playbook never does
this.

## 10. Testing the recipes

| Check | Command | Proves |
|-------|---------|--------|
| Syntax | `make syntax` | Playbook parses with the example inventory |
| Lint | `make lint` | yamllint + ansible-lint `production` profile |
| Secrets | `make secrets-check` | No plaintext vault values or private keys tracked |
| Docs | `make docs-check` | Links, ADR registry, this reference covers all roles/variables/tags |
| Container | `make test-container` | Full converge and `changed=0` second run in an Ubuntu 24.04 systemd container (arm64 or amd64 per workstation) |
| Host | `make deploy`, `make idempotency`, `make verify` | Real behaviour on MagicBox |

The container test overrides `magicbox_expected_architecture`,
`magicbox_lan_interface`, `magicbox_lan_cidr` and sets
`preflight_manage_hostname: false`; it cannot prove LAN mDNS or reachability
from other machines.

## 11. Changing the recipes

1. Edit the role; keep variables prefixed and documented in
   `defaults/main.yml`.
2. Update this reference (roles, variables, tags, risks) and, for significant
   decisions, add an ADR and list it in the registry and `CLAUDE.md`.
3. `make manuals check test-container`.
4. Commit sources and rebuilt PDFs together.
