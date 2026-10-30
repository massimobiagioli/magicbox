# MagicBox

Ansible-managed infrastructure for MagicBox, a GMKtec Intel Mini PC (`x86_64`)
on the LAN running Docker Engine and Portainer CE, reachable from other LAN
computers at **https://magicbox.local:9443/**.

## Rules

- Write everything in English: code, comments, docs, manuals, commit messages.
- **Tools rule:** whenever a task needs a helper (e.g. converting Markdown/HTML
  to PDF, checking links, parsing output), create it as a script in
  [`tools/`](tools/), run it with `uv run tools/<name>`, and add it to the
  "Tools" list below. Do not rely on unrecorded one-off commands or
  system-installed converters.
- MagicBox has no fixed IP: always address it as `magicbox.local` (SSH,
  inventory, docs, clients). Avahi provides the name (ADR-0003).
- Never invent environment details (users, interfaces, subnets, OS) or
  credentials. Ask, or fail with a clear message. Real values live only in the
  git-ignored `inventory/hosts.yml` and the vault-encrypted
  `inventory/group_vars/magicbox/vault.yml`.
- Never commit secrets; never expose the Docker API over TCP; keep management
  access restricted to `magicbox_lan_cidr`.
- Destructive changes require `-e magicbox_confirm_destructive=true` (ADR-0008)
  and explicit confirmation from the owner before running them.
- Keep roles simple and idempotent; pin versions (`pyproject.toml`, `uv.lock`,
  `requirements.yml`, `docker_major_version`, `portainer_version`).
- When a role, variable, tag or playbook changes: update
  `manuals/src/magicbox-playbook.md` (and the installation guide if steps
  change), run `make manuals`, and commit sources with the rebuilt PDFs.
- The installation manual is an operational checklist: "Manual Steps" (Mini PC
  initialisation) first, then commands and checkboxes only. No long
  explanations; rationale belongs in ADRs and the playbook reference.
- Significant decisions get a new sequential ADR in `.docs/adr/`, listed in the
  registry and here.
- Every service with a web UI or HTTP API gets a route in the API gateway
  (`stacks_kong_routes`, or the apps registry for apps) and its URL (gateway and direct port) in the
  `README.md` "Addresses" table and the installation guide services table.
- Report honestly: separate "verified on MagicBox", "verified in the test
  container" and "not executed". Never claim a remote deployment without access.

## Commands

```text
make setup           # uv sync --locked + pinned Ansible collections
make check           # syntax, yamllint, ansible-lint, secrets, manuals, docs checks
make test-container  # converge + idempotency in a disposable systemd container
make manuals         # build manuals/*.pdf from manuals/src/*.md
make deploy EXTRA="-e magicbox_confirm_destructive=true"   # first deployment
make deploy          # later runs (asks the vault password; sudo password is in the vault)
make verify
make stacks          # default Portainer stacks
make ci-cd           # CI/CD stack: Jenkins controller + SSH build agent
make api-gateway     # API gateway stack: Kong, https://magicbox.local/<service>/
uv run tools/new_app.py <name> [--create-repo]          # new app from the template + registry entry
make apps            # apps registry -> Kong routes + Jenkins jobs (https://magicbox.local/<app>)
make status          # read-only: stack images pulled, containers running/healthy
make vault-edit      # edit the encrypted vault (creates it if missing)
make update          # apt update + upgrade (EXTRA="-e os_update_reboot=true" reboots if needed)
make test-container ARGS="--with-stacks"                   # includes stacks (~4 GB pulls)
make test-container ARGS="--with-ci-cd"                    # includes the Jenkins stack
make test-container ARGS="--with-api-gateway"              # includes the Kong stack
make test-container ARGS="--with-ci-cd --with-api-gateway --with-apps"  # includes app routes and jobs
```

## Layout

- `playbooks/site.yml` - host + Portainer (roles + controller verification play)
- `playbooks/stacks.yml` - default Portainer stacks (RabbitMQ, PostgreSQL, Ollama, Grafana/Loki/Alloy)
- `playbooks/ci-cd.yml` - CI/CD stack (Jenkins) via the `stacks` role
- `playbooks/api-gateway.yml` - API gateway stack (Kong) via the `stacks` role
- `playbooks/apps.yml` - apps registry -> Kong routes, Jenkins jobs (Job DSL), `/opt/magicbox/apps/apps.json`
- `playbooks/status.yml` - read-only stack status (images, containers)
- `playbooks/update.yml` - OS package update (apt update + upgrade), optional reboot
- `roles/` - `preflight`, `mdns`, `firewall`, `docker`, `portainer`, `portainer_init`, `stacks`, `os_update`
- `inventory/` - `hosts.example.yml`, `vault.example.yml`, `apps.example.yml`, `group_vars/magicbox/main.yml`;
  git-ignored: `hosts.yml`, `group_vars/magicbox/vault.yml`, `group_vars/magicbox/apps.yml` (apps registry)
- `tests/container/` - Dockerfile and inventory for the container test
- `tools/` - project tools (below)
- `templates/python-fastapi-app/` - FastAPI app template (Python 3.15, uv, `/health`, Dockerfile, generic Jenkinsfile + `deploy/`); see its [README](templates/python-fastapi-app/README.md)
- `samples/` - one app per subfolder, built from the template, using the default stacks; see [samples/README.md](samples/README.md)
- `manuals/src/` - Markdown manual sources; `manuals/*.pdf` - generated PDFs
- `.docs/` - constitution, principles, stack, ADRs

## Documentation

- [README](README.md) - short project entry point

- [Constitution](.docs/CONSTITUTION.md) - purpose, scope, requirements, governance, constraints, acceptance criteria
- [Principles](.docs/PRINCIPLES.md) - maintainability, clean code, architecture, security, testing, documentation standards
- [Stack](.docs/STACK.md) - technologies, versions, dependencies, rationale
- [ADR registry](.docs/adr/registry.md)
  - [ADR-0001](.docs/adr/adr-0001.md) - Ansible from a uv-managed .venv
  - [ADR-0002](.docs/adr/adr-0002.md) - Supported target OS and Docker Engine source
  - [ADR-0003](.docs/adr/adr-0003.md) - magicbox.local via Avahi mDNS
  - [ADR-0004](.docs/adr/adr-0004.md) - ufw and host networking for Portainer
  - [ADR-0005](.docs/adr/adr-0005.md) - Name-constrained local CA for HTTPS
  - [ADR-0006](.docs/adr/adr-0006.md) - Portainer bootstrap credentials and Docker socket access
  - [ADR-0007](.docs/adr/adr-0007.md) - PDF manuals from Markdown (pure Python)
  - [ADR-0008](.docs/adr/adr-0008.md) - Confirmation for destructive changes
  - [ADR-0009](.docs/adr/adr-0009.md) - Tools in tools/ and container tests
  - [ADR-0010](.docs/adr/adr-0010.md) - Portainer initialisation and the "homelab" site
  - [ADR-0011](.docs/adr/adr-0011.md) - Default stacks as Portainer stacks
  - [ADR-0012](.docs/adr/adr-0012.md) - DOCKER-USER filter for published ports
  - [ADR-0013](.docs/adr/adr-0013.md) - Grafana Alloy instead of Promtail (EOL)
  - [ADR-0014](.docs/adr/adr-0014.md) - Jenkins on MagicBox for CI/CD, polling GitHub
  - [ADR-0015](.docs/adr/adr-0015.md) - Kong API gateway with path-based routes
  - [ADR-0016](.docs/adr/adr-0016.md) - Apps deployed by Jenkins and registered in the API gateway
  - [ADR-0017](.docs/adr/adr-0017.md) - App jobs and ports from a git-ignored apps registry

## Manuals

- [Installation guide (PDF)](manuals/installation.pdf) - source: [manuals/src/installation.md](manuals/src/installation.md)
- [Playbook reference (PDF)](manuals/magicbox-playbook.pdf) - source: [manuals/src/magicbox-playbook.md](manuals/src/magicbox-playbook.md)
- [How to create a new app (PDF)](manuals/how-to-create-new-app.pdf) - source: [manuals/src/how-to-create-new-app.md](manuals/src/how-to-create-new-app.md)

Build dependencies: `uv` only. `make setup` installs `markdown==3.11.2` and
`fpdf2==2.8.9` into `.venv`; `make manuals` (`uv run tools/build_manuals.py`)
produces deterministic PDFs.

## Tools

- [tools/build_manuals.py](tools/build_manuals.py) - Markdown -> PDF for `manuals/src/*.md`; `--check` fails on stale PDFs
- [tools/check_docs.py](tools/check_docs.py) - broken links, this index, ADR numbering/sections/registry, playbook-reference coverage, PDFs present
- [tools/check_secrets.py](tools/check_secrets.py) - vault file encrypted; no plaintext `vault_*` values or private keys tracked
- [tools/idempotency_check.py](tools/idempotency_check.py) - runs `ansible-playbook` twice, fails if the second run changes anything
- [tools/new_app.py](tools/new_app.py) - new app from the template: rename, `uv lock`, first commit, apps registry entry (first free port), optional private GitHub repo (`--create-repo`)
- [tools/container_test.py](tools/container_test.py) - disposable systemd container: full converge + idempotency check (`--with-stacks` adds the stacks playbook, `--with-ci-cd` the Jenkins playbook, `--with-api-gateway` the Kong playbook, `--with-apps` the apps playbook, needs the previous two)
