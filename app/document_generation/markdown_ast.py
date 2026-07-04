"""Shared Markdown -> AST module using markdown-it-py.

This is the *only* shared component across all generators.
Output is a list of BlockToken dicts suitable for direct walking by
per-format generators.

BlockToken types:
  heading       {type, level, children}
  paragraph     {type, children}
  list          {type, ordered, children (list_item)}
  list_item     {type, children}
  table         {type, children (table_head, table_body)}
  table_head    {type, children (table_row)}
  table_body    {type, children (table_row)}
  table_row     {type, children (table_cell)}
  table_cell    {type, align, children}
  block_code    {type, raw, info (language)}
  block_quote   {type, children}
  thematic_break {type}
  image         {type, src, alt}
  link          {type, url, children}

Inline tokens:
  text          {type, raw}
  strong        {type, children}
  emphasis      {type, children}
  codespan      {type, raw}
  linebreak     {type}
  softbreak     {type}
"""

from markdown_it import MarkdownIt
from markdown_it.token import Token


_md = MarkdownIt("default")


def parse(markdown_text: str) -> list[dict]:
    """Parse markdown text into a list of AST block tokens."""
    if not markdown_text:
        return []
    tokens = _md.parse(markdown_text)
    return _build_tree(tokens)


def _build_tree(tokens: list[Token]) -> list[dict]:
    root = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        node = _make_block_node(t, tokens, i)
        if node is not None:
            ntype = node["type"]
            if ntype == "list":
                children, i = _collect_list(tokens, i)
                node["children"] = children
            elif ntype == "table":
                children, i = _collect_table(tokens, i)
                node["children"] = children
            elif ntype == "block_quote":
                children, i = _collect_blockquote(tokens, i)
                node["children"] = children
            root.append(node)
        i += 1
    return root


def _make_block_node(t: Token, tokens: list[Token], i: int) -> dict | None:
    if t.type == "heading_open":
        level = 0
        if t.attrs and "level" in t.attrs:
            level = int(t.attrs.get("level", 0))
        else:
            h_tag = t.tag
            if h_tag and h_tag.startswith("h"):
                try:
                    level = int(h_tag[1])
                except (ValueError, IndexError):
                    level = 0
        inline = tokens[i + 1]
        children = _parse_inline(inline) if inline.type == "inline" else []
        return {"type": "heading", "level": level, "children": children}
    if t.type == "paragraph_open":
        inline = tokens[i + 1]
        if inline.type == "inline":
            children = _parse_inline(inline)
            if len(children) == 1 and children[0]["type"] == "image":
                return children[0]
            return {"type": "paragraph", "children": children}
        return {"type": "paragraph", "children": []}
    if t.type == "hr":
        return {"type": "thematic_break"}
    if t.type == "fence":
        return {"type": "block_code", "raw": t.content, "info": t.info.strip() if t.info else ""}
    if t.type == "code_block":
        return {"type": "block_code", "raw": t.content, "info": ""}
    if t.type == "bullet_list_open":
        return {"type": "list", "ordered": False}
    if t.type == "ordered_list_open":
        return {"type": "list", "ordered": True}
    if t.type == "blockquote_open":
        return {"type": "block_quote"}
    if t.type == "table_open":
        return {"type": "table"}
    return None


def _collect_list(tokens: list[Token], start: int) -> tuple[list[dict], int]:
    items = []
    i = start + 1
    while i < len(tokens):
        t = tokens[i]
        if t.type in ("bullet_list_close", "ordered_list_close"):
            return items, i
        if t.type == "list_item_open":
            item = _parse_list_item(tokens, i)
            items.append(item)
            i += _count_item_tokens(tokens, i)
        else:
            i += 1
    return items, len(tokens) - 1


def _parse_list_item(tokens: list[Token], start: int) -> dict:
    children = []
    i = start + 1
    depth = 0
    while i < len(tokens):
        t = tokens[i]
        if t.type == "list_item_close":
            if depth == 0:
                break
            depth -= 1
        elif t.type == "list_item_open":
            depth += 1
        elif t.type == "bullet_list_open" or t.type == "ordered_list_open":
            sub_items, i = _collect_list(tokens, i)
            children.append({"type": "list", "ordered": t.type == "ordered_list_open", "children": sub_items})
            continue
        elif t.type == "inline" and t.content.strip():
            parsed = _parse_inline(t)
            children.extend(parsed)
        i += 1
    return {"type": "list_item", "children": children}


def _count_item_tokens(tokens: list[Token], start: int) -> int:
    count = 1
    depth = 0
    i = start + 1
    while i < len(tokens):
        count += 1
        t = tokens[i]
        if t.type == "list_item_open":
            depth += 1
        elif t.type == "list_item_close":
            if depth == 0:
                break
            depth -= 1
        i += 1
    return count


def _collect_table(tokens: list[Token], start: int) -> tuple[list[dict], int]:
    children = []
    i = start + 1
    head_rows = []
    body_rows = []
    in_head = False

    while i < len(tokens):
        t = tokens[i]
        if t.type == "table_close":
            if head_rows:
                children.append({"type": "table_head", "children": head_rows})
            if body_rows:
                children.append({"type": "table_body", "children": body_rows})
            return children, i
        if t.type == "thead_open":
            in_head = True
        elif t.type == "thead_close":
            in_head = False
        elif t.type == "tr_open":
            row, i = _parse_table_row(tokens, i)
            if in_head:
                head_rows.append(row)
            else:
                body_rows.append(row)
            continue
        i += 1
    return children, len(tokens) - 1


def _parse_table_row(tokens: list[Token], start: int) -> tuple[dict, int]:
    cells = []
    i = start + 1
    while i < len(tokens):
        t = tokens[i]
        if t.type == "tr_close":
            return {"type": "table_row", "children": cells}, i
        if t.type in ("th_open", "td_open"):
            align = t.attrs.get("align", None) if t.attrs else None
            inline = tokens[i + 1]
            cell_children = _parse_inline(inline) if inline.type == "inline" else []
            cells.append({"type": "table_cell", "align": align, "children": cell_children})
            i += 1
        i += 1
    return {"type": "table_row", "children": cells}, i


def _collect_blockquote(tokens: list[Token], start: int) -> tuple[list[dict], int]:
    children = []
    i = start + 1
    while i < len(tokens):
        t = tokens[i]
        if t.type == "blockquote_close":
            return children, i
        node = _make_block_node(t, tokens, i)
        if node is not None:
            children.append(node)
            if node["type"] == "list":
                sub_items, i = _collect_list(tokens, i)
                node["children"] = sub_items
            elif node["type"] == "table":
                sub_children, i = _collect_table(tokens, i)
                node["children"] = sub_children
        i += 1
    return children, len(tokens) - 1


def _parse_inline(t: Token) -> list[dict]:
    """Convert inline token with children into nested AST."""
    if not t.children:
        raw = t.content.strip()
        if raw:
            return [{"type": "text", "raw": raw}]
        return []
    if t.type != "inline":
        raw = t.content.strip()
        if raw:
            return [{"type": "text", "raw": raw}]
        return []
    result = _walk_inline_tokens(t.children)
    return _merge_text(result)


def _walk_inline_tokens(tokens: list[Token]) -> list[dict]:
    """Walk inline token children with nesting support."""
    result = []
    stack = [result]
    for ct in tokens:
        node = None
        if ct.type == "text":
            node = {"type": "text", "raw": ct.content}
        elif ct.type == "code_inline":
            node = {"type": "codespan", "raw": ct.content}
        elif ct.type == "softbreak":
            node = {"type": "softbreak"}
        elif ct.type == "hardbreak":
            node = {"type": "linebreak"}
        elif ct.type == "strong_open":
            node = {"type": "strong", "children": []}
            stack[-1].append(node)
            stack.append(node["children"])
            continue
        elif ct.type == "strong_close":
            if len(stack) > 1:
                stack.pop()
            continue
        elif ct.type == "em_open":
            node = {"type": "emphasis", "children": []}
            stack[-1].append(node)
            stack.append(node["children"])
            continue
        elif ct.type == "em_close":
            if len(stack) > 1:
                stack.pop()
            continue
        elif ct.type == "link_open":
            url = ct.attrs.get("href", "") if ct.attrs else ""
            node = {"type": "link", "url": url, "children": []}
            stack[-1].append(node)
            stack.append(node["children"])
            continue
        elif ct.type == "link_close":
            if len(stack) > 1:
                stack.pop()
            continue
        elif ct.type == "image":
            src = ct.attrs.get("src", "") if ct.attrs else ""
            alt = ct.content or ""
            node = {"type": "image", "src": src, "alt": alt}

        if node is not None:
            stack[-1].append(node)

    return result


def _merge_text(nodes: list) -> list:
    """Merge adjacent text nodes and drop empty ones."""
    if not nodes:
        return []
    merged = []
    for node in nodes:
        if node["type"] == "text":
            raw = node["raw"]
            if not raw:
                continue
            if merged and merged[-1]["type"] == "text":
                merged[-1]["raw"] += raw
            else:
                merged.append({"type": "text", "raw": raw})
        else:
            merged.append(node)
    return merged


def extract_text(children: list) -> str:
    """Recursively extract plain text from AST children."""
    parts = []
    _extract_text(children, parts)
    return "".join(parts)


def _extract_text(children: list, parts: list):
    for token in children:
        t = token["type"]
        if t == "text":
            parts.append(token.get("raw", ""))
        elif t == "codespan":
            parts.append(token.get("raw", ""))
        elif "children" in token:
            _extract_text(token["children"], parts)
