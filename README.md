# MagicBox

Ansible setup for a GMKtec Intel Mini PC: Docker and Portainer CE, served on
the LAN at **https://magicbox.local:9443/**, plus default stacks: RabbitMQ,
PostgreSQL, Ollama, and Grafana + Loki + Alloy.

## Quick start

```bash
make setup && make check
cp inventory/hosts.example.yml inventory/hosts.yml   # fill in your values
make vault-edit                                      # passwords (encrypted)
make deploy EXTRA="-e magicbox_confirm_destructive=true"
make stacks
```

## Docs

- [Installation guide](manuals/installation.pdf), which starts with the Mini PC checklist
- [Playbook reference](manuals/magicbox-playbook.pdf)
- [Project instructions and full index](CLAUDE.md)
