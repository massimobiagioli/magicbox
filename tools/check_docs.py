#!/usr/bin/env python3
"""Check that MagicBox documentation is complete and internally consistent.

Usage:
    uv run tools/check_docs.py

Checks:
  * every relative Markdown link in the repository resolves to an existing file;
  * CLAUDE.md links every .docs/ document, ADR, manual (PDF and source) and tool;
  * ADRs are numbered sequentially (adr-0001.md, adr-0002.md, ...), contain the
    required sections, and are all listed in .docs/adr/registry.md;
  * manuals/src/magicbox-playbook.md mentions every role, tag and role default
    variable, so the playbook reference cannot silently fall behind the code;
  * every manual source has a generated PDF next to it.

Exits non-zero and lists every problem found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".venv", ".ansible", ".serena", ".claude", ".prompt", ".git", "artifacts"}
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
ADR_NAME = re.compile(r"^adr-(\d{4})\.md$")
ADR_SECTIONS = ("## Status", "## Context", "## Decision", "## Alternatives", "## Consequences")


def markdown_files() -> list[Path]:
    return sorted(
        p for p in ROOT.rglob("*.md")
        if not SKIP_DIRS.intersection(p.relative_to(ROOT).parts)
    )


def links_in(path: Path) -> set[Path]:
    targets = set()
    for target in LINK.findall(path.read_text(encoding="utf-8")):
        if re.match(r"^[a-z]+://|^mailto:|^#", target):
            continue
        targets.add((path.parent / target.split("#", 1)[0]).resolve())
    return targets


def check_links(errors: list[str]) -> None:
    for md in markdown_files():
        for target in links_in(md):
            if not target.exists():
                errors.append(f"{md.relative_to(ROOT)}: broken link -> {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}")


def check_claude_index(errors: list[str]) -> None:
    claude = ROOT / "CLAUDE.md"
    if not claude.exists():
        errors.append("CLAUDE.md is missing")
        return
    linked = links_in(claude)
    required = [
        *sorted((ROOT / ".docs").rglob("*.md")),
        *sorted((ROOT / "manuals").glob("*.pdf")),
        *sorted((ROOT / "manuals" / "src").glob("*.md")),
        *sorted(p for p in (ROOT / "tools").iterdir() if p.is_file() and not p.name.startswith(".")),
    ]
    for path in required:
        if path.resolve() not in linked:
            errors.append(f"CLAUDE.md does not link {path.relative_to(ROOT)}")


def check_adrs(errors: list[str]) -> None:
    adr_dir = ROOT / ".docs" / "adr"
    adrs = sorted(p for p in adr_dir.glob("adr-*.md"))
    numbers = []
    for adr in adrs:
        match = ADR_NAME.match(adr.name)
        if not match:
            errors.append(f"{adr.relative_to(ROOT)}: name must be adr-<nnnn>.md")
            continue
        numbers.append(int(match.group(1)))
        text = adr.read_text(encoding="utf-8")
        for section in ADR_SECTIONS:
            if section not in text:
                errors.append(f"{adr.relative_to(ROOT)}: missing section '{section}'")
    if numbers != list(range(1, len(numbers) + 1)):
        errors.append(f"ADR numbers are not sequential from 0001: {numbers}")
    registry = adr_dir / "registry.md"
    if not registry.exists():
        errors.append(".docs/adr/registry.md is missing")
        return
    linked = links_in(registry)
    for adr in adrs:
        if adr.resolve() not in linked:
            errors.append(f"registry.md does not link {adr.name}")


def role_facts() -> tuple[set[str], set[str], set[str]]:
    roles = {p.name for p in (ROOT / "roles").iterdir() if p.is_dir()}
    variables: set[str] = set()
    for defaults in (ROOT / "roles").glob("*/defaults/main.yml"):
        variables.update(re.findall(r"^([a-z][a-z0-9_]*):", defaults.read_text(encoding="utf-8"), flags=re.MULTILINE))
    group_vars = ROOT / "inventory" / "group_vars" / "magicbox" / "main.yml"
    variables.update(re.findall(r"^([a-z][a-z0-9_]*):", group_vars.read_text(encoding="utf-8"), flags=re.MULTILINE))
    tags: set[str] = set()
    for yml in [*(ROOT / "playbooks").glob("*.yml"), *(ROOT / "roles").glob("*/tasks/*.yml")]:
        for group in re.findall(r"tags:\s*\[([^\]]*)\]", yml.read_text(encoding="utf-8")):
            tags.update(t.strip() for t in group.split(",") if t.strip())
    return roles, variables, tags


def check_playbook_reference(errors: list[str]) -> None:
    reference = ROOT / "manuals" / "src" / "magicbox-playbook.md"
    if not reference.exists():
        errors.append("manuals/src/magicbox-playbook.md is missing")
        return
    text = reference.read_text(encoding="utf-8")
    roles, variables, tags = role_facts()
    for kind, names in (("role", roles), ("variable", variables), ("tag", tags)):
        for name in sorted(names):
            if f"`{name}`" not in text:
                errors.append(f"magicbox-playbook.md does not document {kind} `{name}`")


def check_pdfs(errors: list[str]) -> None:
    for source in sorted((ROOT / "manuals" / "src").glob("*.md")):
        pdf = ROOT / "manuals" / f"{source.stem}.pdf"
        if not pdf.exists() or not pdf.read_bytes().startswith(b"%PDF-"):
            errors.append(f"{pdf.relative_to(ROOT)} is missing or not a PDF; run `make manuals`")


def main() -> None:
    errors: list[str] = []
    check_links(errors)
    check_claude_index(errors)
    check_adrs(errors)
    check_playbook_reference(errors)
    check_pdfs(errors)
    if errors:
        print("\n".join(f"ERROR {e}" for e in errors))
        sys.exit(f"{len(errors)} documentation problem(s) found")
    print("Documentation checks passed.")


if __name__ == "__main__":
    main()
