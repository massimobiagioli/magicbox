# MagicBox developer entry points. Every target runs inside the uv-managed .venv.
UV ?= uv
RUN := $(UV) run
COLLECTIONS := .ansible/collections
LINT_INVENTORY := inventory/hosts.example.yml
VAULT_FILE := inventory/group_vars/magicbox/vault.yml
# The sudo password comes from the vault (vault_become_password); BECOME=-K
# prompts for it instead.
BECOME ?=

.PHONY: help setup lint syntax docs-check secrets-check manuals manuals-check check \
        test-container deploy verify idempotency stacks ci-cd api-gateway apps status update vault-edit

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "%-16s %s\n", $$1, $$2}'

setup: ## Create .venv from uv.lock and install pinned Ansible collections
	$(UV) sync --locked
	$(RUN) ansible-galaxy collection install -r requirements.yml -p $(COLLECTIONS)

syntax: ## Ansible syntax check
	$(RUN) ansible-playbook -i $(LINT_INVENTORY) playbooks/site.yml playbooks/stacks.yml playbooks/ci-cd.yml playbooks/api-gateway.yml playbooks/apps.yml playbooks/status.yml playbooks/update.yml --syntax-check

lint: syntax ## yamllint + ansible-lint (production profile)
	$(RUN) yamllint .
	$(RUN) ansible-lint

docs-check: ## Links, CLAUDE.md index, ADR registry, playbook reference coverage
	$(RUN) tools/check_docs.py

secrets-check: ## Refuse plaintext vault values and private keys
	$(RUN) tools/check_secrets.py

manuals: ## Build manuals/*.pdf from manuals/src/*.md
	$(RUN) tools/build_manuals.py

manuals-check: ## Rebuild manuals and fail if committed PDFs were stale
	$(RUN) tools/build_manuals.py --check

check: lint secrets-check manuals docs-check ## All local checks (no target host needed)

test-container: ## Converge + idempotency test in a disposable systemd container (ARGS="--with-stacks --with-ci-cd --with-api-gateway --with-apps"; --with-apps needs the other two)
	$(RUN) tools/container_test.py $(ARGS)

deploy: ## Apply the playbook to MagicBox (pass EXTRA="-e magicbox_confirm_destructive=true" on first run)
	$(RUN) ansible-playbook playbooks/site.yml --ask-vault-pass $(BECOME) $(EXTRA)

verify: ## Run only verify-tagged tasks against MagicBox
	$(RUN) ansible-playbook playbooks/site.yml --ask-vault-pass --tags verify $(BECOME) $(EXTRA)

idempotency: ## Run twice against MagicBox; second run must change nothing (needs VAULT_PASSWORD_FILE)
	$(RUN) tools/idempotency_check.py playbooks/site.yml --vault-password-file $(VAULT_PASSWORD_FILE) $(EXTRA)

stacks: ## Deploy the default Portainer stacks to MagicBox (run deploy first)
	$(RUN) ansible-playbook playbooks/stacks.yml --ask-vault-pass $(BECOME) $(EXTRA)

ci-cd: ## Deploy the CI/CD stack (Jenkins) to MagicBox (run deploy first)
	$(RUN) ansible-playbook playbooks/ci-cd.yml --ask-vault-pass $(BECOME) $(EXTRA)

api-gateway: ## Deploy the API gateway stack (Kong) to MagicBox (run deploy first)
	$(RUN) ansible-playbook playbooks/api-gateway.yml --ask-vault-pass $(BECOME) $(EXTRA)

apps: ## Apps registry (inventory/group_vars/magicbox/apps.yml) -> Kong routes + Jenkins jobs (run ci-cd, api-gateway first)
	$(RUN) ansible-playbook playbooks/apps.yml --ask-vault-pass $(BECOME) $(EXTRA)

status: ## Read-only: are stack images pulled and containers running/healthy on MagicBox?
	$(RUN) ansible-playbook playbooks/status.yml --ask-vault-pass $(BECOME) $(EXTRA)

update: ## apt update + upgrade on MagicBox (EXTRA="-e os_update_reboot=true" to reboot if needed)
	$(RUN) ansible-playbook playbooks/update.yml --ask-vault-pass $(BECOME) $(EXTRA)

vault-edit: ## Edit the encrypted vault (creates it from inventory/vault.example.yml if missing)
	@test -f $(VAULT_FILE) || { cp inventory/vault.example.yml $(VAULT_FILE) && $(RUN) ansible-vault encrypt $(VAULT_FILE) \
		|| { rm -f $(VAULT_FILE); exit 1; }; }
	$(RUN) ansible-vault edit $(VAULT_FILE)
