# MagicBox developer entry points. Every target runs inside the uv-managed .venv.
UV ?= uv
RUN := $(UV) run
COLLECTIONS := .ansible/collections
LINT_INVENTORY := inventory/hosts.example.yml

.PHONY: help setup lint syntax docs-check secrets-check manuals manuals-check check \
        test-container deploy verify idempotency

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "%-16s %s\n", $$1, $$2}'

setup: ## Create .venv from uv.lock and install pinned Ansible collections
	$(UV) sync --locked
	$(RUN) ansible-galaxy collection install -r requirements.yml -p $(COLLECTIONS)

syntax: ## Ansible syntax check
	$(RUN) ansible-playbook -i $(LINT_INVENTORY) playbooks/site.yml --syntax-check

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

test-container: ## Converge + idempotency test in a disposable systemd container
	$(RUN) tools/container_test.py

deploy: ## Apply the playbook to MagicBox (pass EXTRA="-e magicbox_confirm_destructive=true" on first run)
	$(RUN) ansible-playbook playbooks/site.yml --ask-vault-pass $(EXTRA)

verify: ## Run only verify-tagged tasks against MagicBox (EXTRA="-K" for a sudo password)
	$(RUN) ansible-playbook playbooks/site.yml --ask-vault-pass --tags verify $(EXTRA)

idempotency: ## Run twice against MagicBox; second run must change nothing (needs VAULT_PASSWORD_FILE)
	$(RUN) tools/idempotency_check.py playbooks/site.yml --vault-password-file $(VAULT_PASSWORD_FILE) $(EXTRA)
