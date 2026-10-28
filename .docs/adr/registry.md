# ADR Registry

Architecture Decision Records for MagicBox. Numbers are sequential and never
reused; superseded ADRs stay in place with an updated status. Add a new ADR as
`adr-<nnnn>.md` with the sections Status, Context, Decision, Alternatives and
Consequences, then list it here and in [CLAUDE.md](../../CLAUDE.md).

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-0001](adr-0001.md) | Ansible from a uv-managed .venv as the only provisioning path | Accepted |
| [ADR-0002](adr-0002.md) | Supported target OS and Docker Engine source | Accepted (OS to be confirmed) |
| [ADR-0003](adr-0003.md) | Name resolution for magicbox.local via Avahi mDNS | Accepted |
| [ADR-0004](adr-0004.md) | Host firewall with ufw and host networking for Portainer | Accepted |
| [ADR-0005](adr-0005.md) | HTTPS with a name-constrained local CA generated on MagicBox | Accepted |
| [ADR-0006](adr-0006.md) | Portainer bootstrap credentials and Docker socket access | Accepted |
| [ADR-0007](adr-0007.md) | PDF manuals built from Markdown with a pure-Python toolchain | Accepted |
| [ADR-0008](adr-0008.md) | Explicit confirmation for destructive changes | Accepted |
| [ADR-0009](adr-0009.md) | Project tools in tools/ and container-based convergence tests | Accepted |
