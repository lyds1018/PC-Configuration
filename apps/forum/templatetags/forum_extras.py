import html
import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def _render_inline(text):
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)

    def _image_repl(match):
        alt = match.group(1)
        src = match.group(2)
        if src.startswith("http://") or src.startswith("https://") or src.startswith("/"):
            return (
                '<img src="{}" alt="{}" loading="lazy" class="md-inline-image" />'.format(
                    src,
                    alt,
                )
            )
        return alt

    def _link_repl(match):
        label = match.group(1)
        href = match.group(2)
        if href.startswith("http://") or href.startswith("https://"):
            return f'<a href="{href}" target="_blank" rel="noopener noreferrer">{label}</a>'
        return label

    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _image_repl, text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link_repl, text)
    return text


@register.filter(name="markdown_safe")
def markdown_safe(value):
    source = str(value or "").replace("\r\n", "\n")
    escaped = html.escape(source)

    blocks = []
    in_list = False
    for raw_line in escaped.split("\n"):
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("### "):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<h3>{_render_inline(stripped[4:])}</h3>")
            continue
        if stripped.startswith("## "):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<h2>{_render_inline(stripped[3:])}</h2>")
            continue
        if stripped.startswith("# "):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<h1>{_render_inline(stripped[2:])}</h1>")
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                blocks.append("<ul>")
                in_list = True
            blocks.append(f"<li>{_render_inline(stripped[2:])}</li>")
            continue

        if in_list:
            blocks.append("</ul>")
            in_list = False

        if stripped:
            blocks.append(f"<p>{_render_inline(stripped)}</p>")
        else:
            blocks.append("")

    if in_list:
        blocks.append("</ul>")

    return mark_safe("\n".join(blocks))
