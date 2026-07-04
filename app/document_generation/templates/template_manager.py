import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List


DEFAULT_TEMPLATES_DIR = Path(__file__).parent / "data"

DEFAULT_TEMPLATES = {
    "default": {
        "name": "Default",
        "description": "Clean default template",
        "fonts": {"heading": "Arial", "body": "Arial"},
        "margins": {"top": 72, "bottom": 72, "left": 72, "right": 72},
        "colors": {"primary": "#1a1a2e", "secondary": "#16213e", "accent": "#0f3460", "text": "#333333", "background": "#ffffff"},
        "header": "",
        "footer": "",
    },
    "report": {
        "name": "Report",
        "description": "Professional report layout",
        "fonts": {"heading": "Calibri", "body": "Calibri"},
        "margins": {"top": 72, "bottom": 72, "left": 90, "right": 90},
        "colors": {"primary": "#1b4965", "secondary": "#62b6cb", "accent": "#cae9ff", "text": "#2d2d2d", "background": "#ffffff"},
        "header": "<p style='text-align:right;font-size:10px;color:#666;'>{title}</p><hr>",
        "footer": "<p style='text-align:center;font-size:10px;color:#666;'>Page {page}</p>",
    },
    "resume": {
        "name": "Resume",
        "description": "Professional resume/CV layout",
        "fonts": {"heading": "Georgia", "body": "Calibri"},
        "margins": {"top": 54, "bottom": 54, "left": 72, "right": 72},
        "colors": {"primary": "#2c3e50", "secondary": "#34495e", "accent": "#3498db", "text": "#2c3e50", "background": "#ffffff"},
        "header": "",
        "footer": "",
    },
    "meeting-notes": {
        "name": "Meeting Notes",
        "description": "Structured meeting notes layout",
        "fonts": {"heading": "Segoe UI", "body": "Segoe UI"},
        "margins": {"top": 72, "bottom": 72, "left": 72, "right": 72},
        "colors": {"primary": "#6c5ce7", "secondary": "#a29bfe", "accent": "#dfe6e9", "text": "#2d3436", "background": "#ffffff"},
        "header": "<p style='text-align:left;font-size:10px;color:#666;'>Meeting Notes</p><hr>",
        "footer": "<p style='text-align:center;font-size:10px;color:#666;'>Page {page}</p>",
    },
    "letter": {
        "name": "Letter",
        "description": "Formal letter format",
        "fonts": {"heading": "Times New Roman", "body": "Times New Roman"},
        "margins": {"top": 96, "bottom": 96, "left": 96, "right": 96},
        "colors": {"primary": "#000000", "secondary": "#333333", "accent": "#555555", "text": "#000000", "background": "#ffffff"},
        "header": "",
        "footer": "",
    },
    "invoice": {
        "name": "Invoice",
        "description": "Professional invoice layout",
        "fonts": {"heading": "Arial", "body": "Arial"},
        "margins": {"top": 54, "bottom": 54, "left": 72, "right": 72},
        "colors": {"primary": "#e74c3c", "secondary": "#c0392b", "accent": "#f39c12", "text": "#2c3e50", "background": "#ffffff"},
        "header": "",
        "footer": "<p style='text-align:center;font-size:10px;color:#666;'>Thank you for your business</p>",
    },
    "research-paper": {
        "name": "Research Paper",
        "description": "Academic research paper format",
        "fonts": {"heading": "Times New Roman", "body": "Times New Roman"},
        "margins": {"top": 96, "bottom": 96, "left": 96, "right": 96},
        "colors": {"primary": "#000000", "secondary": "#222222", "accent": "#444444", "text": "#000000", "background": "#ffffff"},
        "header": "",
        "footer": "<p style='text-align:center;font-size:10px;color:#666;'>{page}</p>",
    },
    "assignment": {
        "name": "Assignment",
        "description": "Academic assignment format",
        "fonts": {"heading": "Arial", "body": "Arial"},
        "margins": {"top": 72, "bottom": 72, "left": 72, "right": 72},
        "colors": {"primary": "#2d3436", "secondary": "#636e72", "accent": "#0984e3", "text": "#2d3436", "background": "#ffffff"},
        "header": "",
        "footer": "",
    },
}


class TemplateManager:
    def __init__(self):
        self._templates_dir = DEFAULT_TEMPLATES_DIR
        self._templates_dir.mkdir(parents=True, exist_ok=True)
        self._load_defaults()

    def _load_defaults(self):
        for key, tmpl in DEFAULT_TEMPLATES.items():
            filepath = self._templates_dir / f"{key}.json"
            if not filepath.exists():
                with open(filepath, "w") as f:
                    json.dump({"id": key, **tmpl}, f, indent=2)

    def list_templates(self) -> List[Dict[str, Any]]:
        templates = []
        for filepath in self._templates_dir.glob("*.json"):
            with open(filepath) as f:
                tmpl = json.load(f)
                templates.append({
                    "id": tmpl.get("id", filepath.stem),
                    "name": tmpl.get("name", filepath.stem),
                    "description": tmpl.get("description", ""),
                })
        return templates

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        filepath = self._templates_dir / f"{template_id}.json"
        if not filepath.exists():
            return DEFAULT_TEMPLATES.get(template_id) or DEFAULT_TEMPLATES.get("default")
        with open(filepath) as f:
            return json.load(f)

    def save_template(self, template_id: str, data: Dict[str, Any]):
        filepath = self._templates_dir / f"{template_id}.json"
        data["id"] = template_id
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def delete_template(self, template_id: str):
        filepath = self._templates_dir / f"{template_id}.json"
        if filepath.exists():
            filepath.unlink()

    def apply_template(self, html: str, template: Dict[str, Any]) -> str:
        fonts = template.get("fonts", {})
        colors = template.get("colors", {})
        header = template.get("header", "")
        footer = template.get("footer", "")

        styled_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{
        font-family: {fonts.get('body', 'Arial')}, sans-serif;
        font-size: 12pt;
        color: {colors.get('text', '#333')};
        background: {colors.get('background', '#fff')};
        margin: 0;
        padding: 20px;
        line-height: 1.5;
    }}
    h1, h2, h3, h4, h5, h6 {{
        font-family: {fonts.get('heading', 'Arial')}, sans-serif;
        color: {colors.get('primary', '#000')};
        margin-top: 1.2em;
        margin-bottom: 0.5em;
    }}
    h1 {{ font-size: 24pt; }}
    h2 {{ font-size: 20pt; }}
    h3 {{ font-size: 16pt; }}
    h4 {{ font-size: 14pt; }}
    h5 {{ font-size: 12pt; }}
    h6 {{ font-size: 11pt; }}
    p {{ margin: 0.5em 0; }}
    table {{
        border-collapse: collapse;
        width: 100%;
        margin: 1em 0;
    }}
    th, td {{
        border: 1px solid {colors.get('secondary', '#ccc')};
        padding: 8px 12px;
        text-align: left;
    }}
    th {{
        background-color: {colors.get('accent', '#f5f5f5')};
        font-weight: bold;
    }}
    pre {{
        background: #f5f5f5;
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 12px;
        overflow-x: auto;
        font-family: 'Courier New', monospace;
        font-size: 10pt;
    }}
    code {{
        background: #f0f0f0;
        padding: 2px 4px;
        border-radius: 3px;
        font-family: 'Courier New', monospace;
        font-size: 10pt;
    }}
    blockquote {{
        border-left: 4px solid {colors.get('accent', '#ccc')};
        margin: 1em 0;
        padding: 0.5em 1em;
        color: #666;
        background: #fafafa;
    }}
    img {{
        max-width: 100%;
        height: auto;
    }}
    hr {{
        border: none;
        border-top: 2px solid {colors.get('secondary', '#ccc')};
        margin: 1.5em 0;
    }}
    ul, ol {{ margin: 0.5em 0; padding-left: 2em; }}
    li {{ margin: 0.3em 0; }}
    a {{ color: {colors.get('accent', '#0066cc')}; text-decoration: none; }}
</style>
</head>
<body>
{header}
{html}
{footer}
</body>
</html>"""
        return styled_html


template_manager = TemplateManager()
