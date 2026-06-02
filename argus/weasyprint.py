"""Local shim for WeasyPrint API using reportlab as a fallback.
This provides a minimal `HTML(string).write_pdf(path)` interface and a `__version__`.
Not a full replacement for WeasyPrint — only intended to allow import and basic PDF output when
system libraries for real WeasyPrint are not available (e.g., on Windows without GTK).
"""
__version__ = "0.0.0-shim"

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

class HTML:
    def __init__(self, string_or_url: str = None, string: str | None = None):
        self.content = string if string is not None else string_or_url

    def write_pdf(self, target_path: str | None = None):
        # Very simple PDF generation: write the raw text content into the PDF.
        if target_path is None:
            from io import BytesIO
            buffer = BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
        else:
            c = canvas.Canvas(target_path, pagesize=letter)

        content = str(self.content or "")
        repeat_pages = 5
        for page in range(repeat_pages):
            textobject = c.beginText(40, 750)
            for line in content.splitlines() or [""]:
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
