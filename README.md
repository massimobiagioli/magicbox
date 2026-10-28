# MagicBox

Ansible setup for a GMKtec Intel Mini PC: Docker and Portainer CE, served on
the LAN at **https://magicbox.local:9443/**.

## Quick start

```bash
make setup && make check
cp inventory/hosts.example.yml inventory/hosts.yml   # fill in your values
uv run ansible-vault create inventory/group_vars/magicbox/vault.yml
make deploy EXTRA="-K -e magicbox_confirm_destructive=true"
```

## Docs

- [Installation guide](manuals/installation.pdf), which starts with the Mini PC checklist
- [Playbook reference](manuals/magicbox-playbook.pdf)
- [Project instructions and full index](CLAUDE.md)
