#!/usr/bin/env python3
"""Render content.md into index.html, using template.html as the shell.

    python3 render.py

Stdlib only — no dependencies, nothing to install. Run it after editing
content.md and commit both content.md and the regenerated index.html.

The markdown conventions, all of which fall out of how the page is styled:

    # Title              the <h1>, and the <title> in the template
    <first paragraph>    the subtitle; line one is .lead, "· …" becomes .loc
    <next paragraphs>    the intro section (no heading)
    ## name              a section with an <h2>
    - **Name** _(…)_ — … an experience entry; bold is the company (.co) and
                         emphasis is the date (.when, muted + italic)
    - label: [text](url) a contact entry; the label renders as .lbl

    Links wrap emphasis, never the other way round: [**Name**](url), not
    **[Name](url)**. render.py warns if it finds markdown it did not render.

A list is treated as contacts when its first item starts with `label:`, and as
experience otherwise, so new sections of either shape need no code changes.
"""

import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent

# Accent class per name. Everything but a-yellow currently resolves to --emph
# in the stylesheet; the separate classes are kept so that going back to a more
# colourful theme stays a CSS-only change.
ACCENTS = {
    "Biene Club": "a-yellow",
    "Entropy Cryptography": "a-blue",
    "Parity Technologies": "a-green",
    "Zeitgeist PM": "a-purple",
    "ink!ubator": "a-orange",
    "Earlier": "a-teal",
    "bioinformatics": "a-teal",
    "embedded systems": "a-teal",
    "compilers": "a-green",
    "security auditor": "a-red",
}

# Phrases that should never wrap mid-way. Kept here rather than as literal
# &nbsp; in content.md, so the copy stays readable as plain markdown.
NO_WRAP = ("Biene Club", "Entropy Cryptography", "Rust → Wasm", "VP Eng")

RULE_WIDTH = 127


def sub_text(pattern, repl, s):
    """re.sub, but skipping anything inside an HTML tag, so that an underscore
    or asterisk in a URL is never mistaken for emphasis."""
    parts = re.split(r"(<[^>]*>)", s)
    return "".join(p if p.startswith("<") else re.sub(pattern, repl, p) for p in parts)


def inline(text, bold_class=None, em_class=None, link_rel=None):
    """Escape a run of markdown, then expand links, strong and emphasis.

    Both markdown spellings work: **strong** or __strong__, *em* or _em_.
    """
    out = html.escape(text, quote=False)

    def link(m):
        rel = f' rel="{link_rel}"' if link_rel and not m[2].startswith("mailto:") else ""
        return f'<a href="{m[2]}"{rel}>{m[1]}</a>'

    # Emphasis always produces the semantic element, so **bold** is bold
    # everywhere; a class is only ever added on top, to colour it.
    def strong(m):
        name = m[1] if m[1] is not None else m[2]
        classes = " ".join(c for c in (bold_class, ACCENTS.get(name)) if c)
        return f'<strong class="{classes}">{name}</strong>' if classes else f"<strong>{name}</strong>"

    def em(m):
        body = m[1] if m[1] is not None else m[2]
        return f'<em class="{em_class}">{body}</em>' if em_class else f"<em>{body}</em>"

    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, out)
    out = sub_text(r"\*\*(.+?)\*\*|__(.+?)__", strong, out)
    out = sub_text(r"\*(.+?)\*|_(.+?)_", em, out)

    for phrase in NO_WRAP:
        out = out.replace(phrase, phrase.replace(" ", "&nbsp;"))
    return out


def rule(kind, glyph, indent):
    """One of the decorative divider rows. Presentation, so not in content.md."""
    return f'{" " * indent}<div class="rule {kind}" aria-hidden="true">{glyph * RULE_WIDTH}</div>'


def render_list(items):
    contacts = bool(re.match(r"[\w ]+:\s", items[0]))
    out = [f'      <ul class="{"links" if contacts else "exp"}">']
    for item in items:
        if contacts:
            label, _, rest = item.partition(":")
            body = f'<span class="lbl">{label}</span> {inline(rest.strip(), link_rel="me")}'
        else:
            body = inline(item, bold_class="co", em_class="when")
        out.append(f"        <li>{body}</li>")
    out.append("      </ul>")
    return out


def warn_unrendered(body):
    """Markdown surviving into the output means a convention was missed — most
    likely **[Name](url)**, which has to be written [**Name**](url). Say so,
    rather than quietly shipping literal asterisks to the page."""
    text = re.sub(r"<[^>]*>", "", "\n".join(body))
    text = re.sub(r"[═─]+", "", text)
    stray = sorted(set(re.findall(r"\*\*|__|\[[^\]]*\]\(", text)))
    if stray:
        print(f"warning: unrendered markdown in output: {' '.join(stray)}", file=sys.stderr)


def render_section(label, blocks, heading=None):
    out = [f'    <section aria-label="{label}">']
    if heading:
        out.append(f"      <h2>{heading}</h2>")
    for block in blocks:
        if block.lstrip().startswith("- "):
            out += render_list([ln.strip()[2:] for ln in block.splitlines()])
        else:
            out.append(f"      <p>{inline(' '.join(block.split()))}</p>")
    out.append("    </section>")
    return out


def main():
    blocks = re.split(r"\n\s*\n", (HERE / "content.md").read_text(encoding="utf-8").strip())

    title = blocks.pop(0).lstrip("#").strip()
    lead, _, tail = blocks.pop(0).partition("\n")
    tail = re.sub(r"(·.*)$", r'<span class="loc">\1</span>', inline(tail))

    intro, sections = [], []
    for block in blocks:
        if block.startswith("## "):
            sections.append((block[3:].strip(), []))
        elif sections:
            sections[-1][1].append(block)
        else:
            intro.append(block)

    body = [
        "    <header>",
        f"      <h1>{inline(title)}</h1>",
        f'      <p class="subtitle"><span class="lead">{inline(lead)}</span><br>{tail}</p>',
        rule("eq", "═", 6),
        "    </header>",
        "",
    ]
    body += render_section("About", intro)
    for name, section_blocks in sections:
        body += ["", rule("dash", "─", 4), ""]
        body += render_section(name.capitalize(), section_blocks, heading=name)

    warn_unrendered(body)

    page = (HERE / "template.html").read_text(encoding="utf-8")
    page = page.replace(
        "<!DOCTYPE html>",
        "<!DOCTYPE html>\n<!-- Generated by render.py — edit content.md or template.html, not this file. -->",
        1,
    )
    page = page.replace("{{title}}", html.escape(title))
    page = page.replace("{{content}}", "\n".join(body))
    (HERE / "index.html").write_text(page, encoding="utf-8")
    print("wrote index.html")


if __name__ == "__main__":
    main()
