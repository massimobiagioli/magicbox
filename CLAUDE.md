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
- Report honestly: separate "verified on MagicBox", "verified in the test
  container" and "not executed". Never claim a remote deployment without access.

## Commands

```text
make setup           # uv sync --locked + pinned Ansible collections
make check           # syntax, yamllint, ansible-lint, secrets, manuals, docs checks
make test-container  # converge + idempotency in a disposable systemd container
make manuals         # build manuals/*.pdf from manuals/src/*.md
make deploy EXTRA="-K -e magicbox_confirm_destructive=true"   # first deployment
make deploy EXTRA="-K"                                        # later runs
make verify EXTRA="-K"
```

## Layout

- `playbooks/site.yml` - main playbook (roles + controller verification play)
- `roles/` - `preflight`, `mdns`, `firewall`, `docker`, `portainer`
- `inventory/` - `hosts.example.yml`, `vault.example.yml`, `group_vars/magicbox/main.yml`
- `tests/container/` - Dockerfile and inventory for the container test
- `tools/` - project tools (below)
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

## Manuals

- [Installation guide (PDF)](manuals/installation.pdf) - source: [manuals/src/installation.md](manuals/src/installation.md)
- [Playbook reference (PDF)](manuals/magicbox-playbook.pdf) - source: [manuals/src/magicbox-playbook.md](manuals/src/magicbox-playbook.md)

Build dependencies: `uv` only. `make setup` installs `markdown==3.11.2` and
`fpdf2==2.8.9` into `.venv`; `make manuals` (`uv run tools/build_manuals.py`)
produces deterministic PDFs.

## Tools

- [tools/build_manuals.py](tools/build_manuals.py) - Markdown -> PDF for `manuals/src/*.md`; `--check` fails on stale PDFs
- [tools/check_docs.py](tools/check_docs.py) - broken links, this index, ADR numbering/sections/registry, playbook-reference coverage, PDFs present
- [tools/check_secrets.py](tools/check_secrets.py) - vault file encrypted; no plaintext `vault_*` values or private keys tracked
- [tools/idempotency_check.py](tools/idempotency_check.py) - runs `ansible-playbook` twice, fails if the second run changes anything
- [tools/container_test.py](tools/container_test.py) - disposable systemd container: full converge + idempotency check
