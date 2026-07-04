import re
from typing import Optional


class MarkdownConverter:
    @staticmethod
    def to_html(markdown_text: str) -> str:
        lines = markdown_text.split("\n")
        html_parts = []
        in_code_block = False
        code_block_content = []
        code_lang = ""
        in_table = False
        table_buffer = []
        in_list = False
        list_type = None

        i = 0
        while i < len(lines):
            line = lines[i]

            # Code blocks
            if line.strip().startswith("```"):
                if in_code_block:
                    lang_attr = f' class="language-{code_lang}"' if code_lang else ""
                    escaped = _escape_html("\n".join(code_block_content))
                    html_parts.append(f"<pre><code{lang_attr}>{escaped}</code></pre>")
                    code_block_content = []
                    in_code_block = False
                    code_lang = ""
                else:
                    in_code_block = True
                    code_lang = line.strip()[3:].strip()
                i += 1
                continue

            if in_code_block:
                code_block_content.append(line)
                i += 1
                continue

            # Empty lines
            if not line.strip():
                if in_list:
                    html_parts.append(_close_list(list_type))
                    in_list = False
                    list_type = None
                if in_table and table_buffer:
                    html_parts.append(_render_table(table_buffer))
                    table_buffer = []
                    in_table = False
                html_parts.append("")
                i += 1
                continue

            # Tables
            if "|" in line and line.strip().startswith("|"):
                in_table = True
                table_buffer.append(line)
                i += 1
                continue
            else:
                if in_table and table_buffer:
                    html_parts.append(_render_table(table_buffer))
                    table_buffer = []
                    in_table = False

            # Horizontal rules
            if re.match(r"^[-*_]{3,}\s*$", line.strip()):
                html_parts.append("<hr>")
                i += 1
                continue

            # Headings
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                level = len(heading_match.group(1))
                text = _inline_html(heading_match.group(2))
                html_parts.append(f"<h{level}>{text}</h{level}>")
                i += 1
                continue

            # Unordered list
            ul_match = re.match(r"^(\s*)[*\-+]\s+(.+)$", line)
            if ul_match:
                indent = len(ul_match.group(1))
                text = _inline_html(ul_match.group(2))
                if not in_list or list_type != "ul":
                    if in_list:
                        html_parts.append(_close_list(list_type))
                    html_parts.append("<ul>")
                    in_list = True
                    list_type = "ul"
                html_parts.append(f"<li>{text}</li>")
                i += 1
                continue

            # Ordered list
            ol_match = re.match(r"^(\s*)\d+\.\s+(.+)$", line)
            if ol_match:
                text = _inline_html(ol_match.group(2))
                if not in_list or list_type != "ol":
                    if in_list:
                        html_parts.append(_close_list(list_type))
                    html_parts.append("<ol>")
                    in_list = True
                    list_type = "ol"
                html_parts.append(f"<li>{text}</li>")
                i += 1
                continue

            # Blockquotes
            bq_match = re.match(r"^>\s?(.*)$", line)
            if bq_match:
                text = _inline_html(bq_match.group(1))
                html_parts.append(f"<blockquote>{text}</blockquote>")
                i += 1
                continue

            # Paragraph (default)
            text = _inline_html(line.strip())
            if text:
                html_parts.append(f"<p>{text}</p>")
            i += 1

        if in_code_block and code_block_content:
            escaped = _escape_html("\n".join(code_block_content))
            lang_attr = f' class="language-{code_lang}"' if code_lang else ""
            html_parts.append(f"<pre><code{lang_attr}>{escaped}</code></pre>")

        if in_list:
            html_parts.append(_close_list(list_type))

        if in_table and table_buffer:
            html_parts.append(_render_table(table_buffer))

        result = "\n".join(html_parts)
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result

    @staticmethod
    def to_sanitized_html(markdown_text: str) -> str:
        from app.document_generation.utils.sanitizer import sanitize_html
        html = MarkdownConverter.to_html(markdown_text)
        return sanitize_html(html)


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _inline_html(text: str) -> str:
    text = _escape_html(text)

    # Images
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        r'<img src="\2" alt="\1" style="max-width:100%">',
        text,
    )

    # Links
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" target="_blank">\1</a>',
        text,
    )

    # Bold + Italic
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    text = re.sub(r"___(.+?)___", r"<strong><em>\1</em></strong>", text)

    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)

    # Italic
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)

    # Strikethrough
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)

    # Inline code
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    return text


def _render_table(rows: list) -> str:
    if len(rows) < 2:
        return ""

    header_cells = [c.strip() for c in rows[0].strip().strip("|").split("|")]
    alignments = ["left"] * len(header_cells)

    if len(rows) >= 2 and re.match(r"^\|?[\s:-]+\|", rows[1].strip()):
        align_row = rows[1].strip().strip("|").split("|")
        alignments = []
        for cell in align_row:
            cell = cell.strip()
            if cell.startswith(":") and cell.endswith(":"):
                alignments.append("center")
            elif cell.endswith(":"):
                alignments.append("right")
            elif cell.startswith(":"):
                alignments.append("left")
            else:
                alignments.append("left")
        data_rows = rows[2:]
    else:
        data_rows = rows[1:]

    html = "<table><thead><tr>"
    for i, cell in enumerate(header_cells):
        align = alignments[i] if i < len(alignments) else "left"
        html += f"<th align='{align}'>{_inline_html(cell)}</th>"
    html += "</tr></thead><tbody>"

    for row in data_rows:
        if not row.strip():
            continue
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        html += "<tr>"
        for i, cell in enumerate(cells):
            content = _inline_html(cell)
            html += f"<td>{content}</td>"
        html += "</tr>"

    html += "</tbody></table>"
    return html


def _close_list(list_type: str) -> str:
    return f"</{list_type}>"


def markdown_to_html(markdown_text: str, sanitize: bool = True) -> str:
    converter = MarkdownConverter()
    if sanitize:
        return converter.to_sanitized_html(markdown_text)
    return converter.to_html(markdown_text)
