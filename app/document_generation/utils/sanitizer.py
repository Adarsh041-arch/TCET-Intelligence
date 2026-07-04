import re
from typing import Optional


class HTMLSanitizer:
    ALLOWED_TAGS = {
        "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "br", "hr",
        "ul", "ol", "li",
        "table", "thead", "tbody", "tr", "th", "td",
        "strong", "b", "em", "i", "u", "s", "del", "ins",
        "a", "img",
        "pre", "code", "blockquote",
        "div", "span", "section",
        "dl", "dt", "dd",
        "sub", "sup",
        "figure", "figcaption",
    }

    ALLOWED_ATTRS = {
        "a": {"href", "title", "target"},
        "img": {"src", "alt", "width", "height"},
        "td": {"colspan", "rowspan", "align"},
        "th": {"colspan", "rowspan", "align"},
        "table": {"border", "cellpadding", "cellspacing"},
        "*": {"class", "id", "style"},
    }

    ALLOWED_PROTOCOLS = {"http:", "https:", "mailto:", "data:"}

    FORBIDDEN_PATTERNS = [
        re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),
        re.compile(r"vbscript:", re.IGNORECASE),
        re.compile(r"<iframe", re.IGNORECASE),
        re.compile(r"<object", re.IGNORECASE),
        re.compile(r"<embed", re.IGNORECASE),
        re.compile(r"<link", re.IGNORECASE),
        re.compile(r"<style[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL),
        re.compile(r"<form", re.IGNORECASE),
        re.compile(r"<input", re.IGNORECASE),
        re.compile(r"<textarea", re.IGNORECASE),
        re.compile(r"<select", re.IGNORECASE),
        re.compile(r"<button", re.IGNORECASE),
        re.compile(r"<!\[CDATA\[", re.IGNORECASE),
        re.compile(r"<\?xml", re.IGNORECASE),
    ]

    @classmethod
    def sanitize(cls, html: str) -> str:
        result = html
        for pattern in cls.FORBIDDEN_PATTERNS:
            result = pattern.sub("", result)
        result = cls._strip_unsafe_tags(result)
        result = cls._strip_unsafe_attrs(result)
        return result

    @classmethod
    def _strip_unsafe_tags(cls, html: str) -> str:
        tag_pattern = re.compile(r"<\/?(\w+)[^>]*?>", re.IGNORECASE | re.DOTALL)

        def replace_tag(m):
            tag_name = m.group(1).lower()
            if tag_name in cls.ALLOWED_TAGS:
                return m.group(0)
            return ""

        return tag_pattern.sub(replace_tag, html)

    @classmethod
    def _strip_unsafe_attrs(cls, html: str) -> str:
        def clean_attrs(m):
            tag = m.group(0)
            tag_name_match = re.match(r"<\/?(\w+)", tag, re.IGNORECASE)
            if not tag_name_match:
                return tag
            tag_name = tag_name_match.group(1).lower()
            allowed = set(cls.ALLOWED_ATTRS.get(tag_name, set()) | set(cls.ALLOWED_ATTRS.get("*", set())))

            def attr_filter(attr_match):
                attr_full = attr_match.group(0)
                attr_name_match = re.match(r"(\w+)", attr_full)
                if not attr_name_match:
                    return ""
                attr_name = attr_name_match.group(1).lower()
                if attr_name not in allowed:
                    return ""
                value_match = re.search(r'=(["\'])(.*?)\1', attr_full)
                if value_match:
                    value = value_match.group(2).lower()
                    if ":" in value and not any(value.startswith(p) for p in cls.ALLOWED_PROTOCOLS):
                        return ""
                return attr_full

            cleaned = re.sub(r'\s+\w+(?:\s*=\s*(?:"[^"]*"|\'[^\']*\'|\S+))?', attr_filter, tag)
            return cleaned

        attr_pattern = re.compile(r"<[^>]+>", re.DOTALL)
        return attr_pattern.sub(clean_attrs, html)


def sanitize_html(html: str) -> str:
    return HTMLSanitizer.sanitize(html)
