# MagicBox developer entry points. Every target runs inside the uv-managed .venv.
UV ?= uv
RUN := $(UV) run
COLLECTIONS := .ansible/collections
LINT_INVENTORY := inventory/hosts.example.yml
VAULT_FILE := inventory/group_vars/magicbox/vault.yml
# The sudo password comes from the vault (vault_become_password); BECOME=-K
# prompts for it instead.
BECOME ?=

.PHONY: help setup check manuals test-container deploy status update vault-edit

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "%-16s %s\n", $$1, $$2}'

setup: ## Create .venv from uv.lock and install pinned Ansible collections
	$(UV) sync --locked
	$(RUN) ansible-galaxy collection install -r requirements.yml -p $(COLLECTIONS)

manuals: ## Build manuals/*.pdf from manuals/src/*.md
	$(RUN) tools/build_manuals.py

check: manuals ## All local checks: syntax, yamllint, ansible-lint, secrets, manuals, docs (no target host needed)
	$(RUN) ansible-playbook -i $(LINT_INVENTORY) playbooks/site.yml playbooks/status.yml playbooks/update.yml --syntax-check
	$(RUN) yamllint .
	$(RUN) ansible-lint
	$(RUN) tools/check_secrets.py
	$(RUN) tools/check_docs.py

test-container: ## Converge + idempotency test in a disposable systemd container (ARGS="--stacks all" or "--stacks jenkins,kong")
	$(RUN) tools/container_test.py $(ARGS)

deploy: ## Whole infrastructure, idempotent: host, Portainer, all stacks, apps (first run: EXTRA="-e magicbox_confirm_destructive=true")
	$(RUN) ansible-playbook playbooks/site.yml --ask-vault-pass $(BECOME) $(EXTRA)

status: ## Read-only: are stack images pulled and containers running/healthy on MagicBox?
	$(RUN) ansible-playbook playbooks/status.yml --ask-vault-pass $(BECOME) $(EXTRA)

update: ## apt update + upgrade on MagicBox (EXTRA="-e os_update_reboot=true" to reboot if needed)
	$(RUN) ansible-playbook playbooks/update.yml --ask-vault-pass $(BECOME) $(EXTRA)

vault-edit: ## Edit the encrypted vault (creates it from inventory/vault.example.yml if missing)
	@test -f $(VAULT_FILE) || { cp inventory/vault.example.yml $(VAULT_FILE) && $(RUN) ansible-vault encrypt $(VAULT_FILE) \
		|| { rm -f $(VAULT_FILE); exit 1; }; }
	$(RUN) ansible-vault edit $(VAULT_FILE)
