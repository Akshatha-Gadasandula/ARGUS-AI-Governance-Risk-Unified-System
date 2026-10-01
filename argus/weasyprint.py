"""Local shim for WeasyPrint API using reportlab as a fallback.
This provides a minimal `HTML(string).write_pdf(path)` interface and a `__version__`.
Not a full replacement for WeasyPrint — only intended to allow import and basic PDF output when
system libraries for real WeasyPrint are not available (e.g., on Windows without GTK).
"""
__version__ = "0.0.0-shim"

from html.parser import HTMLParser
import re
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


class _TextExtractor(HTMLParser):
    """Extract readable text from rendered HTML for the reportlab fallback."""

    BLOCK_TAGS = {
        "article",
        "blockquote",
        "body",
        "div",
        "dl",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "head",
        "header",
        "li",
        "main",
        "ol",
        "p",
        "section",
        "table",
        "tbody",
        "td",
        "th",
        "thead",
        "tr",
        "ul",
    }

    def __init__(self):
        super().__init__()
        self.lines: list[str] = []
        self.current: list[str] = []
        self._skip_depth = 0

    def _flush(self, blank: bool = False):
        line = "".join(self.current).strip()
        self.current = []

        if line:
            self.lines.append(line)
        elif blank and (not self.lines or self.lines[-1] != ""):
            self.lines.append("")

    def _append_text(self, text: str):
        if not text:
            return

        if self.current and not self.current[-1].endswith((" ", "|", "•", "\n")) and not text.startswith((" ", "|")):
            self.current.append(" ")

        self.current.append(text)

    def handle_starttag(self, tag, attrs):
        if tag in {"style", "script"}:
            self._skip_depth += 1
            return

        if self._skip_depth:
            return

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "blockquote", "li", "tr", "table", "ul", "ol", "section", "article", "main", "header", "footer", "div"}:
            self._flush(blank=tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "blockquote", "section", "article", "main", "header", "footer", "div", "table", "ul", "ol"})

        if tag == "li":
            self.current.append("- ")

        if tag in {"td", "th"} and self.current:
            self.current.append(" | ")

    def handle_endtag(self, tag):
        if tag in {"style", "script"} and self._skip_depth:
            self._skip_depth -= 1
            return

        if self._skip_depth:
            return

        if tag in {"tr", "li", "p", "blockquote"}:
            self._flush()
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6", "table", "ul", "ol", "section", "article", "main", "header", "footer", "div"}:
            self._flush(blank=True)

    def handle_data(self, data):
        if self._skip_depth:
            return

        text = re.sub(r"\s+", " ", data).strip()
        if text:
            self._append_text(text)

    def get_text(self) -> str:
        self._flush()

        cleaned_lines: list[str] = []
        for line in self.lines:
            normalized = re.sub(r"\s+\|\s+", " | ", line).strip()
            if normalized:
                cleaned_lines.append(normalized)
            elif cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")

        return "\n".join(cleaned_lines)

class HTML:
    def __init__(self, string_or_url: str = None, string: str | None = None):
        self.content = string if string is not None else string_or_url

    def write_pdf(self, target_path: str | None = None):
        # Very simple PDF generation: extract readable text from the rendered HTML.
        if target_path is None:
            from io import BytesIO
            buffer = BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter, pageCompression=0)
        else:
            c = canvas.Canvas(target_path, pagesize=letter, pageCompression=0)

        extractor = _TextExtractor()
        extractor.feed(str(self.content or ""))
        content = extractor.get_text() or ""

        lines = content.splitlines() or [""]
        lines_per_page = 45
        for start in range(0, len(lines), lines_per_page):
            chunk = lines[start:start + lines_per_page]
            textobject = c.beginText(40, 750)
            for line in chunk:
                textobject.textLine(line)
            c.drawText(textobject)
            c.showPage()

        c.save()

        if target_path is None:
            buffer.seek(0)
            return buffer.getvalue()
        return Path(target_path).read_bytes()

# Provide a convenience function used by some code
def HTML_string_to_pdf(s: str, path: str):
    HTML(s).write_pdf(path)
