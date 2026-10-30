# MagicBox

Ansible setup for a GMKtec Intel Mini PC: Docker and Portainer CE, served on
the LAN at **https://magicbox.local:9443/**, plus default stacks: RabbitMQ,
PostgreSQL, Ollama + Open WebUI, and Grafana + Loki + Alloy. Optional: Jenkins (CI/CD), a
Kong API gateway at **https://magicbox.local/** and RustFS (S3 object storage).

## Quick start

```bash
make setup && make check
cp inventory/hosts.example.yml inventory/hosts.yml   # fill in your values
make vault-edit                                      # passwords (encrypted)
make deploy EXTRA="-e magicbox_confirm_destructive=true"
make stacks
make ci-cd          # optional: Jenkins
make api-gateway    # optional: Kong, https://magicbox.local/<service>/
make storage        # optional: RustFS, S3 API :9100, console :9101
make apps           # apps registry -> Kong routes + Jenkins jobs
```

## Addresses

From a LAN computer that trusts the MagicBox CA (installation guide, section 6).
Gateway URLs need `make api-gateway`; Jenkins needs `make ci-cd`; RustFS
needs `make storage`; apps
(registry `inventory/group_vars/magicbox/apps.yml`, git-ignored) need `make apps`.

| Service | Via the gateway (Kong) | Direct | Login |
|---------|------------------------|--------|-------|
| Portainer | `https://magicbox.local/portainer/` | `https://magicbox.local:9443/` | `admin` / `vault_portainer_admin_password` |
| Jenkins | `https://magicbox.local/jenkins/` | `https://magicbox.local:8443/jenkins/` | `admin` / `vault_jenkins_admin_password` |
| Grafana | `https://magicbox.local/grafana/` | `https://magicbox.local:3000/grafana/` | `admin` / `vault_grafana_admin_password` |
| RabbitMQ UI | `https://magicbox.local/rabbitmq/` | `http://magicbox.local:15672/rabbitmq/` | `magicbox` / `vault_rabbitmq_password` |
| Open WebUI (Ollama chat) | `https://magicbox.local/openwebui` (redirect) | `https://magicbox.local:8444/` | `admin@magicbox.local` / `vault_openwebui_admin_password` |
| Ollama API | `https://magicbox.local/ollama/` | `http://magicbox.local:11434/` | gateway: header `apikey: <vault_kong_ollama_api_key>`; direct: none |
| Tester App | `https://magicbox.local/tester-app` | - (loopback, port from the apps registry) | none |
| RustFS console | `https://magicbox.local/rustfs` (redirect) | `https://magicbox.local:9101/rustfs/console/` | `vault_rustfs_access_key` / `vault_rustfs_secret_key` |
| RustFS S3 API | - (signed paths, ADR-0018) | `https://magicbox.local:9100` (path-style, region `us-east-1`) | same keys as the console |
| RabbitMQ AMQP | - | `amqp://magicbox.local:5672` | as RabbitMQ UI |
| PostgreSQL | - | `magicbox.local:5432`, database `magicbox` | `magicbox` / `vault_postgresql_password` |

`https://magicbox.local/` redirects to Portainer. Example:
`curl -H "apikey: <key>" https://magicbox.local/ollama/api/tags`.

## Docs

- [Installation guide](manuals/installation.pdf), which starts with the Mini PC checklist
- [Playbook reference](manuals/magicbox-playbook.pdf)
- [How to create a new app](manuals/how-to-create-new-app.pdf): `tools/new_app.py` -> `make apps`
- [Project instructions and full index](CLAUDE.md)
