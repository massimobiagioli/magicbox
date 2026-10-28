#!/usr/bin/env python3
"""Build the MagicBox PDF manuals from their Markdown sources.

Usage:
    uv run tools/build_manuals.py            # build every manual
    uv run tools/build_manuals.py --check    # also fail if a committed PDF is stale

Sources live in manuals/src/<name>.md and are rendered to manuals/<name>.pdf
with pure-Python dependencies (markdown + fpdf2, pinned in pyproject.toml), so
no system packages are needed. Output is deterministic: the PDF creation date
comes from SOURCE_DATE_EPOCH when set, otherwise from a fixed epoch, which
makes rebuilt PDFs byte-identical when the sources have not changed.

Supported Markdown: headings, paragraphs, bold/italic, inline code, fenced
code blocks, bullet/numbered lists, tables (cells rendered as plain text),
block quotes, links and rules.
Text must be representable in Latin-1 after the substitutions below; the build
fails with the offending character otherwise.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import os
import re
import sys
from pathlib import Path

import markdown
from fpdf import FPDF, TextStyle

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "manuals" / "src"
OUT_DIR = ROOT / "manuals"

# Typographic characters mapped to Latin-1 equivalents (core PDF fonts).
SUBSTITUTIONS = {
    "—": "--", "–": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "…": "...", "→": "->",
    "←": "<-", "≥": ">=", "≤": "<=", "✓": "[x]",
    " ": " ",
}

# Text styles per HTML tag; headings use a dark blue accent.
ACCENT = (20, 60, 110)
TAG_STYLES = {
    "h1": TextStyle(font_family="Helvetica", font_style="B", font_size_pt=20, color=ACCENT, t_margin=0, b_margin=0.6),
    "h2": TextStyle(font_family="Helvetica", font_style="B", font_size_pt=14, color=ACCENT, t_margin=1.2, b_margin=0.4),
    "h3": TextStyle(font_family="Helvetica", font_style="B", font_size_pt=11.5, color=ACCENT, t_margin=1, b_margin=0.3),
    "h4": TextStyle(font_family="Helvetica", font_style="B", font_size_pt=10.5, color=(0, 0, 0), t_margin=0.8, b_margin=0.2),
    "code": TextStyle(font_family="Courier", font_size_pt=9.5, color=(120, 30, 30)),
    "pre": TextStyle(font_family="Courier", font_size_pt=8.5, color=(30, 30, 30), fill_color=(242, 242, 242), t_margin=0.6, b_margin=0.6),
    "blockquote": TextStyle(font_family="Helvetica", font_style="I", color=(70, 70, 70), l_margin=6, t_margin=0.5, b_margin=0.5),
    "a": TextStyle(font_family="Helvetica", color=ACCENT, font_style="U"),
}

# A fixed default keeps builds reproducible without SOURCE_DATE_EPOCH.
DEFAULT_EPOCH = 1767225600  # 2026-01-01T00:00:00Z


class Manual(FPDF):
    """A4 PDF with a running title header and page-number footer."""

    def __init__(self, title: str) -> None:
        super().__init__(format="A4")
        self.manual_title = title
        self.set_margins(18, 18, 18)
        self.set_auto_page_break(auto=True, margin=18)
        self.set_title(title)
        self.set_author("MagicBox infrastructure")
        self.set_creator("tools/build_manuals.py")

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 6, self.manual_title, align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 6, f"Page {self.page_no()}/{{nb}}", align="C")
        self.set_text_color(0, 0, 0)


def to_latin1(text: str, source: Path) -> str:
    for char, replacement in SUBSTITUTIONS.items():
        text = text.replace(char, replacement)
    for lineno, line in enumerate(text.splitlines(), start=1):
        for char in line:
            if ord(char) > 0xFF:
                sys.exit(f"{source}:{lineno}: unsupported character {char!r} (U+{ord(char):04X})")
    return text


def render_html(md_text: str) -> str:
    html = markdown.markdown(md_text, extensions=["tables", "fenced_code", "sane_lists"])
    # fpdf2 renders <pre> without wrapping; keep code blocks readable.
    html = re.sub(r"<pre><code[^>]*>", "<pre>", html).replace("</code></pre>", "</pre>")
    # Drop inter-tag newlines (fpdf2 renders them as blank lines) outside <pre>.
    parts = re.split(r"(<pre>.*?</pre>)", html, flags=re.DOTALL)
    html = "".join(p if p.startswith("<pre>") else re.sub(r">\s*\n\s*<", "><", p) for p in parts)
    # fpdf2 table cells cannot mix text and inline tags; flatten cells to text.
    html = re.sub(
        r"(<t[dh][^>]*>)(.*?)(</t[dh]>)",
        lambda m: m.group(1) + re.sub(r"</?(code|strong|em|a)[^>]*>", "", m.group(2)) + m.group(3),
        html,
        flags=re.DOTALL,
    )
    # Give tables visible borders and a header style.
    return html.replace("<table>", '<table border="1" width="100%">')


def build(source: Path) -> Path:
    raw = source.read_text(encoding="utf-8")
    text = to_latin1(raw, source)
    title_match = re.search(r"^# (.+)$", text, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else source.stem

    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", DEFAULT_EPOCH))
    pdf = Manual(title)
    pdf.set_creation_date(dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc))
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.write_html(
        render_html(text),
        tag_styles=TAG_STYLES,
        table_line_separators=True,
        li_prefix_color=ACCENT,
    )
    out = OUT_DIR / f"{source.stem}.pdf"
    pdf.output(str(out))
    return out


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def main() -> None:
    check = "--check" in sys.argv[1:]
    sources = sorted(SRC_DIR.glob("*.md"))
    if not sources:
        sys.exit(f"No Markdown sources in {SRC_DIR}")
    stale = []
    for source in sources:
        before = digest(OUT_DIR / f"{source.stem}.pdf")
        out = build(source)
        after = digest(out)
        status = "unchanged" if before == after else "rebuilt"
        if before != after:
            stale.append(out)
        print(f"{status:9} {out.relative_to(ROOT)} ({out.stat().st_size} bytes, sha256 {after[:12]})")
    if check and stale:
        sys.exit("Committed PDFs were stale; commit the rebuilt files: " + ", ".join(str(p.relative_to(ROOT)) for p in stale))


if __name__ == "__main__":
    main()
