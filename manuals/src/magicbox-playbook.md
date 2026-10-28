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
| Playbooks | `playbooks/site.yml` (host + Portainer), `playbooks/stacks.yml` (default stacks), `playbooks/update.yml` (OS packages) |
| Inventory | `inventory/hosts.yml` (git-ignored; template `inventory/hosts.example.yml`) |
| Group | `magicbox` |
| Project policy | `inventory/group_vars/magicbox/main.yml` |
| Secrets | `inventory/group_vars/magicbox/vault.yml` (ansible-vault, git-ignored) |
| Collections | `requirements.yml`, installed to `.ansible/collections` |
| Result | Portainer CE at `https://magicbox.local:9443/` with environment `homelab`; default stacks; LAN only |

Play 1, *Configure MagicBox*, runs on group `magicbox` with `become: true` and
applies the roles in this order: `preflight`, `mdns`, `firewall`, `docker`,
`portainer`, `portainer_init`. Play 2, *Verify Portainer from the Ansible
controller*, queries Portainer from the controller over the LAN.

`playbooks/stacks.yml` has one play, *Deploy default stacks through
Portainer*, that runs the `stacks` role on group `magicbox`. Run it after
`site.yml`.

`playbooks/update.yml` has one play, *Update MagicBox packages*, that runs the
`os_update` role. It needs the vault password only for `vault_become_password`.

## 2. Commands

| Goal | Command |
|------|---------|
| Create the environment | `make setup` |
| All local checks | `make check` |
| Container converge + idempotency test | `make test-container` |
| First deployment | `make deploy EXTRA="-e magicbox_confirm_destructive=true"` |
| Routine deployment | `make deploy` |
| Only one area | `uv run ansible-playbook playbooks/site.yml --ask-vault-pass --tags docker` |
| Dry run with diff | `uv run ansible-playbook playbooks/site.yml --ask-vault-pass --check --diff` |
| Verification only | `make verify` |
| Default stacks | `make stacks` |
| Selected stacks only | `uv run ansible-playbook playbooks/stacks.yml --ask-vault-pass -e '{"stacks_enabled": ["postgresql"]}'` |
| Stacks: verification only | `uv run ansible-playbook playbooks/stacks.yml --ask-vault-pass --tags verify` |
| Stack status (read-only) | `make status` |
| Edit the vault | `make vault-edit` |
| OS package update | `make update` |
| OS update + reboot if required | `make update EXTRA="-e os_update_reboot=true"` |
| Idempotency on MagicBox | `make idempotency VAULT_PASSWORD_FILE=<file>` |
| List tasks / tags | `uv run ansible-playbook playbooks/site.yml --list-tasks` / `--list-tags` |

`make deploy`, `verify`, `stacks` and `update` ask for the vault password;
the sudo password is `vault_become_password` (`ansible_become_password` in
`inventory/hosts.yml`). `BECOME=-K` prompts for it instead.

A `--check` run cannot complete the `docker` and `portainer` roles on a
fresh host because the packages they verify are not installed yet.

## 3. Tags

| Tag | Selects |
|-----|---------|
| `preflight` | The `preflight` role |
| `always` | Also on `preflight`: it runs with any `--tags` selection, so checks and facts are always present |
| `mdns` | The `mdns` role |
| `firewall` | The `firewall` role |
| `docker` | The `docker` role |
| `portainer` | The `portainer` and `portainer_init` roles, including TLS tasks |
| `portainer-init` | Only the `portainer_init` role (site environment) |
| `stacks` | The `stacks` role (in `playbooks/stacks.yml`) |
| `status` | The read-only status report (in `playbooks/status.yml`) |
| `update` | The `os_update` role (in `playbooks/update.yml`) |
| `tls` | Only TLS provisioning inside `portainer` (certificate renewal, CA fetch) |
| `verify` | Verification tasks in all roles plus the controller play; in `stacks.yml`, login, lookups and stack checks |
| `controller-verify` | Only the controller play; skipped by the container test |

`--tags verify` runs `preflight` (tagged `always`) and every `verify` task. It
changes nothing on a converged host.

## 4. Shared variables

Defined in `inventory/hosts.yml` (environment facts) or
`inventory/group_vars/magicbox/main.yml` (project policy).

| Variable | Default | Description |
|----------|---------|-------------|
| `magicbox_lan_interface` | required | LAN interface on MagicBox (`ip -br link`). Avahi publishes only here. |
| `magicbox_lan_cidr` | required | Private IPv4 LAN subnet allowed to reach SSH, Portainer and mDNS. |
| `ansible_ssh_extra_args` | `"-4"` | SSH over IPv4: ufw allows only the IPv4 `magicbox_lan_cidr`; an IPv6 link-local connection is refused by preflight. |
| `ansible_become_password` | `{{ vault_become_password }}` | sudo password of `ansible_user`, set in `inventory/hosts.yml`; remove with passwordless sudo. |
| `vault_become_password` | required (vault) | sudo password; anyone with the vault password can become root on MagicBox. |
| `ansible_become_exe` | `sudo` | Ubuntu 26.04: `sudo.ws` (classic sudo; sudo-rs prompts time out, ADR-0002). |
| `magicbox_hostname` | `magicbox` | Hostname and mDNS name (`<name>.local`); single DNS label. |
| `magicbox_expected_architecture` | `x86_64` | Asserted CPU architecture. |
| `magicbox_supported_os` | Ubuntu 24.04/26.04, Debian 12/13 | Asserted OS/version map (ADR-0002). |
| `magicbox_confirm_destructive` | `false` | Allows destructive steps for one run (ADR-0008). Pass with `-e`. |
| `magicbox_site_name` | `homelab` | Name of the Portainer environment (site) for the local Docker engine (ADR-0010). |
| `magicbox_portainer_api_url` | `https://magicbox.local:9443` | Portainer API used by `portainer_init` and `stacks`; keep in sync with `portainer_https_port`. |
| `magicbox_portainer_ca_cert` | `/opt/magicbox/portainer/certs/ca.crt` | CA used to validate the API; keep in sync with `portainer_cert_dir`. |
| `portainer_admin_password` | `{{ vault_portainer_admin_password }}` | Bootstrap admin password, from the vault. |
| `vault_portainer_admin_password` | required (vault) | At least 12 characters; in `vault.yml` only. |
| `vault_postgresql_password`, `vault_rabbitmq_password`, `vault_grafana_admin_password` | required for the matching stack (vault) | At least 12 characters each. |

## 5. Role `preflight`

**Purpose.** Fail fast on unsupported or misconfigured hosts and prepare the
baseline: OS/architecture/inventory/vault assertions, LAN CIDR validation,
detection of where the SSH controller connects from, hostname, base packages.

**Prerequisites.** `magicbox.local` resolves from the controller (Avahi
installed during the manual steps); SSH key login as a sudo-capable user;
Python 3 on the host (present on Ubuntu/Debian server installs).

| Variable | Default | Description |
|----------|---------|-------------|
| `preflight_base_packages` | ca-certificates, curl, gnupg, iproute2, python3-cryptography, python3-debian, python3-requests | Packages needed by later roles and modules. |
| `preflight_manage_hostname` | `true` | Set the static hostname and `127.0.1.1` entry. `false` only in the test container. |

**Facts set.** `preflight_controller_location`: `inside`, `outside` or
`unknown` (no `SSH_CLIENT`, e.g. the container test), consumed by `firewall`.

**Verification.** All assertions run on every play (tag `always`).

**Risks.** Changing `magicbox_hostname` renames the host and the mDNS name;
certificates must match (`portainer_tls_dns_names` follows automatically, the
existing CA's name constraints do not: rotate the CA, installation guide 8.6).

## 6. Role `mdns`

**Purpose.** Publish `magicbox.local` on the LAN with Avahi (ADR-0003). MagicBox
has no fixed IP: Avahi re-announces the name whenever DHCP changes the
address. Avahi is first installed by hand (installation guide 1.5) so Ansible
can connect by name; this role then owns its configuration.
Installs `mdns_packages`, disables systemd-resolved's mDNS/LLMNR responders
when systemd-resolved is installed, templates `/etc/avahi/avahi-daemon.conf`
(host name, `allow-interfaces`, no HINFO/workstation publishing, no reflector,
no wide-area), and enables `avahi-daemon`.

| Variable | Default | Description |
|----------|---------|-------------|
| `mdns_use_ipv6` | `false` | Publish AAAA records. Off because the firewall only allows the IPv4 LAN. |
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
| `firewall_docker_user_filter` | `true` | Manage the DOCKER-USER block in `/etc/ufw/after.rules` that limits Docker-published ports to the LAN (ADR-0012). |

**Safety rails.** Refuses first activation unless
`magicbox_confirm_destructive=true`; always refuses when
`preflight_controller_location` is `outside`.

**Handlers.** *Reload ufw* when the DOCKER-USER block changes.

**Verification.** `iptables -S DOCKER-USER` contains the LAN RETURN rule and
the interface DROP rule. `sudo ufw status verbose` (manual); the controller
play proves 9443 is reachable from the LAN.

**Risks.** A wrong `magicbox_lan_cidr` can lock out SSH from other subnets
(console recovery: installation guide 8.3). Rules for ports no longer listed
are not removed automatically; delete them with `sudo ufw delete <n>`. Ports
published by containers bypass ufw's INPUT rules; the DOCKER-USER block
restricts them to `magicbox_lan_cidr` instead. Setting
`firewall_docker_user_filter: false` exposes them to any source that can
route to MagicBox.

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

`daemon.json` also sets the log option `tag` to the container name, which
Alloy uses as the `container` label (ADR-0013).

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
| `portainer_tls_ip_addresses` | `[]` | Optional IP SANs/constraints. Keep empty: the IP is dynamic (DHCP). |
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

## 10. Role `portainer_init`

**Purpose.** Initialise Portainer through its API: log in as admin with the
vault password and ensure one local Docker environment named
`magicbox_site_name` (`homelab`). It renames an existing local-socket
environment, or creates one (ADR-0010). `tasks/api_login.yml` is reused by
`stacks`.

| Variable | Default | Description |
|----------|---------|-------------|
| `portainer_init_api_user` | `admin` | Portainer user for API calls; password is `portainer_admin_password`. |

**Prerequisites.** The `portainer` role has run (Portainer up, CA present).

**Verification.** The environment exists and its URL is
`unix:///var/run/docker.sock`.

**Risks.** Fails at login if the admin password was changed in the UI and not
in the vault. Changing `magicbox_site_name` after stacks exist creates a new,
empty environment; rename the old one in the UI first.

## 11. Role `stacks` (playbooks/stacks.yml)

**Purpose.** Deploy the default services as Portainer standalone stacks in the
site environment (ADR-0011). For each name in `stacks_enabled` it renders
`roles/stacks/templates/<name>.yml.j2`, passes the secrets as stack
environment variables, and creates the stack, or updates it when the compose
file or environment differs or one of its containers is missing (e.g. an
interrupted first deployment). Config files for `observability` are written to
`stacks_base_dir`; their checksum (`MAGICBOX_CONFIG_REVISION` label) forces a
redeploy when they change.

| Stack | Containers | Published ports | Volumes |
|-------|------------|-----------------|---------|
| `rabbitmq` | rabbitmq | 5672, 15672 | rabbitmq_data |
| `postgresql` | postgresql | 5432 | postgresql_data |
| `ollama` | ollama | 11434 | ollama_data |
| `observability` | grafana, loki, alloy | 3000 (Grafana HTTPS) | grafana_data, loki_data, alloy_data |

| Variable | Default | Description |
|----------|---------|-------------|
| `stacks_enabled` | rabbitmq, postgresql, ollama, observability | Stacks to manage. Removing one does not delete it. |
| `stacks_base_dir` | `/opt/magicbox/stacks` | Host directory for mounted config files. |
| `stacks_rabbitmq_image` | `rabbitmq:4.3.7-management` | RabbitMQ image. |
| `stacks_postgresql_image` | `postgres:18.6` | PostgreSQL image (newest major, supported to 2030). |
| `stacks_ollama_image` | `ollama/ollama:0.40.12` | Ollama image. |
| `stacks_grafana_image` | `grafana/grafana:13.2.5` | Grafana image. |
| `stacks_loki_image` | `grafana/loki:3.7.9` | Loki image. |
| `stacks_alloy_image` | `grafana/alloy:v1.21.2` | Alloy image (Promtail replacement, ADR-0013). |
| `stacks_rabbitmq_amqp_port` | `5672` | Host port for AMQP. |
| `stacks_rabbitmq_management_port` | `15672` | Host port for the RabbitMQ UI/API (HTTP). |
| `stacks_postgresql_port` | `5432` | Host port for PostgreSQL. |
| `stacks_ollama_port` | `11434` | Host port for the Ollama API. |
| `stacks_grafana_port` | `3000` | Host port for Grafana (HTTPS). |
| `stacks_rabbitmq_user` | `magicbox` | RabbitMQ default user. |
| `stacks_rabbitmq_password` | `{{ vault_rabbitmq_password }}` | RabbitMQ password (first start only). |
| `stacks_postgresql_user` | `magicbox` | PostgreSQL superuser. |
| `stacks_postgresql_database` | `magicbox` | Database created at first start. |
| `stacks_postgresql_password` | `{{ vault_postgresql_password }}` | PostgreSQL password (first start only). |
| `stacks_grafana_admin_password` | `{{ vault_grafana_admin_password }}` | Grafana `admin` password (first start only). |
| `stacks_ollama_models` | `[]` | Models to pull after deployment, e.g. `["llama3.2:3b"]`; never deleted. |
| `stacks_loki_retention` | `168h` | Loki log retention. |

Internal data (`roles/stacks/vars/main.yml`, not meant to be overridden):
`stacks_env` (environment per stack), `stacks_required_secrets`,
`stacks_containers`.

**Prerequisites.** `playbooks/site.yml` completed (Portainer, `homelab`
environment, DOCKER-USER filter); the vault contains the stack passwords.

**Verification.** All stack containers running, and healthy where a
healthcheck exists (up to 15 minutes, to cover first image pulls).
PostgreSQL `pg_isready`. RabbitMQ `/api/overview` with the vault credentials.
Ollama `/api/version`. Grafana `/api/health` over HTTPS with the MagicBox CA.
Loki has a `container` label value `loki`, which proves Alloy -> Loki ->
Grafana works.

**Status.** `make status` (`playbooks/status.yml`, `tasks/status.yml`) changes
nothing: it lists each image of the enabled stacks as OK or MISSING and each
container as OK, NOT OK (stopped, restarting, unhealthy) or MISSING, and fails
when anything is not OK.

**Risks.**

- Passwords are applied only on first initialisation of each data volume.
  Changing a vault value later breaks login and verification until the
  service password is changed too.
- Stack environments (including passwords) are stored in Portainer's
  database.
- Edits made to these stacks in the Portainer UI are overwritten by the next
  run.
- RabbitMQ, PostgreSQL and Ollama use plain-text protocols on the LAN; Ollama
  has no authentication. Access is limited to the LAN by DOCKER-USER.
- Grafana uses a copy of the Portainer certificate. After a certificate
  renewal by `site.yml`, run `stacks.yml` to refresh the copy.
- First deployment downloads about 4 GB (Ollama is about 3.4 GB).

## 12. Role `os_update` (playbooks/update.yml)

**Purpose.** Keep the OS current: `apt update`, `apt upgrade` and
`apt autoremove`. Docker CE updates stay within `docker_major_version` (apt
pin); `live-restore` keeps containers running while dockerd restarts.

| Variable | Default | Description |
|----------|---------|-------------|
| `os_update_upgrade` | `safe` | `safe` (apt upgrade, never removes packages) or `full` (apt full-upgrade). |
| `os_update_autoremove` | `true` | Remove packages that are no longer needed. |
| `os_update_reboot` | `false` | Reboot when `/var/run/reboot-required` exists. |
| `os_update_reboot_timeout` | `900` | Seconds to wait for MagicBox to return after the reboot. |
| `os_update_services` | avahi-daemon, docker | Must be running after the update; units not installed yet are skipped. |

**Verification.** Every installed unit in `os_update_services` is running
after the update (and after the reboot, if any). Before the first
`make deploy`, Docker is not installed and is skipped.

**Risks.**

- A reboot stops Portainer and every stack for a few minutes; they restart
  automatically. Hence `os_update_reboot` is off by default and the play only
  reports a pending reboot.
- `full` may remove packages; review `apt list --upgradable` on MagicBox first.

## 13. Testing the recipes

| Check | Command | Proves |
|-------|---------|--------|
| Syntax | `make syntax` | Playbook parses with the example inventory |
| Lint | `make lint` | yamllint + ansible-lint `production` profile |
| Secrets | `make secrets-check` | No plaintext vault values or private keys tracked |
| Docs | `make docs-check` | Links, ADR registry, this reference covers all roles/variables/tags |
| Container | `make test-container` | Full converge and `changed=0` second run in an Ubuntu 24.04 systemd container (arm64 or amd64 per workstation) |
| Container + stacks | `make test-container ARGS="--with-stacks"` | Also runs `stacks.yml` twice (deploy + `changed=0`) |
| Host | `make deploy`, `make idempotency`, `make verify` | Real behaviour on MagicBox |

The container test overrides `magicbox_expected_architecture`,
`magicbox_lan_interface`, `magicbox_lan_cidr` and sets
`preflight_manage_hostname: false`; it cannot prove LAN mDNS or reachability
from other machines.

## 14. Changing the recipes

1. Edit the role; keep variables prefixed and documented in
   `defaults/main.yml`.
2. Update this reference (roles, variables, tags, risks) and, for significant
   decisions, add an ADR and list it in the registry and `CLAUDE.md`.
3. `make manuals check test-container`.
4. Commit sources and rebuilt PDFs together.
