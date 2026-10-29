# MagicBox

Ansible setup for a GMKtec Intel Mini PC: Docker and Portainer CE, served on
the LAN at **https://magicbox.local:9443/**, plus default stacks: RabbitMQ,
PostgreSQL, Ollama, and Grafana + Loki + Alloy. Optional: Jenkins (CI/CD) and
a Kong API gateway at **https://magicbox.local/**.

## Quick start

```bash
make setup && make check
cp inventory/hosts.example.yml inventory/hosts.yml   # fill in your values
make vault-edit                                      # passwords (encrypted)
make deploy EXTRA="-e magicbox_confirm_destructive=true"
make stacks
make ci-cd          # optional: Jenkins
make api-gateway    # optional: Kong, https://magicbox.local/<service>/
make apps           # register apps/registry.yml in Kong
```

## Addresses

From a LAN computer that trusts the MagicBox CA (installation guide, section 6).
Gateway URLs need `make api-gateway`; Jenkins needs `make ci-cd`; apps
(`apps/registry.yml`) need `make apps` and their Jenkins pipeline.

| Service | Via the gateway (Kong) | Direct | Login |
|---------|------------------------|--------|-------|
| Portainer | `https://magicbox.local/portainer/` | `https://magicbox.local:9443/` | `admin` / `vault_portainer_admin_password` |
| Jenkins | `https://magicbox.local/jenkins/` | `https://magicbox.local:8443/jenkins/` | `admin` / `vault_jenkins_admin_password` |
| Grafana | `https://magicbox.local/grafana/` | `https://magicbox.local:3000/grafana/` | `admin` / `vault_grafana_admin_password` |
| RabbitMQ UI | `https://magicbox.local/rabbitmq/` | `http://magicbox.local:15672/rabbitmq/` | `magicbox` / `vault_rabbitmq_password` |
| Ollama API (no UI) | `https://magicbox.local/ollama/` | `http://magicbox.local:11434/` | gateway: header `apikey: <vault_kong_ollama_api_key>`; direct: none |
| Tester App | `https://magicbox.local/tester-app` | - (loopback `127.0.0.1:18001`) | none |
| RabbitMQ AMQP | - | `amqp://magicbox.local:5672` | as RabbitMQ UI |
| PostgreSQL | - | `magicbox.local:5432`, database `magicbox` | `magicbox` / `vault_postgresql_password` |

`https://magicbox.local/` redirects to Portainer. Example:
`curl -H "apikey: <key>" https://magicbox.local/ollama/api/tags`.

## Docs

- [Installation guide](manuals/installation.pdf), which starts with the Mini PC checklist
- [Playbook reference](manuals/magicbox-playbook.pdf)
- [Project instructions and full index](CLAUDE.md)
