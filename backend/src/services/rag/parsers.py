"""Turn an uploaded original into text sections that keep their page / heading context."""

import io
import re
from dataclasses import dataclass

MIME_TEXT = "text/plain"
MIME_MARKDOWN = "text/markdown"
MIME_HTML = "text/html"
MIME_PDF = "application/pdf"
SUPPORTED_EXTENSIONS = {
    ".txt": MIME_TEXT,
    ".text": MIME_TEXT,
    ".md": MIME_MARKDOWN,
    ".markdown": MIME_MARKDOWN,
    ".html": MIME_HTML,
    ".htm": MIME_HTML,
    ".pdf": MIME_PDF,
}

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_HTML_START = re.compile(rb"^\s*(<!doctype html|<html|<head|<body)", re.IGNORECASE)


class UnsupportedFileType(Exception):
    """The upload is not a type we can parse."""


class ParseError(Exception):
    """The file could not be turned into text; the message is safe to show the user."""


@dataclass
class Section:
    text: str
    page: int | None = None
    heading_path: str | None = None


def detect_type(filename: str, head: bytes) -> str:
    """Pick a MIME type from the extension, confirmed by the first bytes of the file."""
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    mime = SUPPORTED_EXTENSIONS.get(ext)
    if head.startswith(b"%PDF-"):
        if mime not in (None, MIME_PDF):
            raise UnsupportedFileType("file content does not match its extension")
        return MIME_PDF
    if mime == MIME_PDF:
        raise UnsupportedFileType("file is not a valid PDF")
    if not _is_text(head):
        raise UnsupportedFileType("unsupported or binary file")
    if mime is None:
        return MIME_HTML if _HTML_START.match(head) else MIME_TEXT
    return mime


def _is_text(head: bytes) -> bool:
    if b"\x00" in head:
        return False
    try:
        head.decode("utf-8")
    except UnicodeDecodeError as e:
        # A multi-byte character may be cut at the end of the sniffed prefix.
        return e.start >= len(head) - 3
    return True


def parse(data: bytes, mime: str) -> list[Section]:
    if mime == MIME_PDF:
        sections = _parse_pdf(data)
    elif mime == MIME_HTML:
        sections = parse_html(_decode(data))
    elif mime == MIME_MARKDOWN:
        sections = parse_markdown(_decode(data))
    else:
        sections = [Section(_decode(data))]
    sections = [s for s in sections if s.text.strip()]
    if not sections:
        raise ParseError("No extractable text found in the document.")
    return sections


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ParseError("The document is not valid UTF-8 text.") from None


def parse_markdown(text: str) -> list[Section]:
    """Split on headings; each section carries its heading path ("A › B")."""
    sections: list[Section] = []
    stack: list[tuple[int, str]] = []
    lines: list[str] = []
    in_fence = False

    def flush():
        body = "\n".join(lines).strip()
        if body:
            path = " › ".join(title for _, title in stack) or None
            sections.append(Section(body, heading_path=path))
        lines.clear()

    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
        match = None if in_fence else _HEADING.match(line)
        if match:
            flush()
            level = len(match.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, match.group(2)))
        else:
            lines.append(line)
    flush()
    return sections


def parse_html(html: str) -> list[Section]:
    import trafilatura

    markdown = trafilatura.extract(
        html, output_format="markdown", include_formatting=True, include_tables=True
    )
    if not markdown:
        raise ParseError("No readable content found in the page.")
    return parse_markdown(markdown)


def html_title(html: str) -> str | None:
    import trafilatura

    metadata = trafilatura.extract_metadata(html)
    return metadata.title if metadata and metadata.title else None


def _parse_pdf(data: bytes) -> list[Section]:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ParseError("Encrypted PDFs are not supported.")
        return [
            Section(page.extract_text() or "", page=i)
            for i, page in enumerate(reader.pages, start=1)
        ]
    except PdfReadError as e:
        raise ParseError(f"Could not read the PDF: {e}") from None
