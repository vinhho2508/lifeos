import pytest

from src.services.rag import parsers
from src.services.rag.chunking import chunk_sections, count_tokens
from src.services.rag.search import join_overlapping, to_tsquery
from tests.rag_helpers import make_pdf


def test_markdown_sections_carry_heading_path():
    md = (
        "Intro line.\n\n# Lease\n\nTerm text.\n\n## Pets\n\nOne cat.\n\n"
        "```\n# not a heading\n```\n\n# Other\n\nX"
    )
    sections = parsers.parse(md.encode(), parsers.MIME_MARKDOWN)

    assert [(s.heading_path, s.text.splitlines()[0]) for s in sections] == [
        (None, "Intro line."),
        ("Lease", "Term text."),
        ("Lease › Pets", "One cat."),
        ("Other", "X"),
    ]
    assert "# not a heading" in sections[2].text


def test_pdf_sections_keep_page_numbers():
    sections = parsers.parse(make_pdf(["First page text", "Second page text"]), parsers.MIME_PDF)

    assert [(s.page, s.text.strip()) for s in sections] == [
        (1, "First page text"),
        (2, "Second page text"),
    ]


def test_pdf_without_text_is_a_parse_error():
    with pytest.raises(parsers.ParseError, match="No extractable text"):
        parsers.parse(make_pdf([""]), parsers.MIME_PDF)


def test_html_main_content_is_extracted_as_markdown_sections():
    body = "".join(f"<p>Paragraph {i} about the garden and its tomatoes.</p>" for i in range(8))
    html = (
        "<html><head><title>Garden</title></head><body><nav>Menu Home About</nav>"
        f"<article><h1>Garden notes</h1>{body}<h2>Watering</h2>"
        "<p>Water the tomatoes every morning before nine o'clock in summer.</p></article>"
        "</body></html>"
    )
    sections = parsers.parse(html.encode(), parsers.MIME_HTML)

    assert any(s.heading_path == "Garden notes › Watering" for s in sections)
    assert all("Menu Home About" not in s.text for s in sections)


@pytest.mark.parametrize(
    ("filename", "head", "expected"),
    [
        ("notes.md", b"# Title", parsers.MIME_MARKDOWN),
        ("a.txt", b"plain", parsers.MIME_TEXT),
        ("doc.pdf", b"%PDF-1.7", parsers.MIME_PDF),
        ("page.html", b"<html>", parsers.MIME_HTML),
        ("noext", b"<!DOCTYPE html><html>", parsers.MIME_HTML),
    ],
)
def test_detect_type(filename, head, expected):
    assert parsers.detect_type(filename, head) == expected


@pytest.mark.parametrize(
    ("filename", "head"),
    [("fake.pdf", b"hello"), ("photo.txt", b"\x89PNG\r\n\x1a\n\x00\x00"), ("x.md", b"%PDF-1.4")],
)
def test_detect_type_rejects_mismatched_or_binary_files(filename, head):
    with pytest.raises(parsers.UnsupportedFileType):
        parsers.detect_type(filename, head)


def test_chunks_are_token_sized_with_metadata_and_context_header():
    text = " ".join(f"Sentence number {i} talks about budgets." for i in range(400))
    sections = [parsers.Section(text, page=3, heading_path="Finance › 2026")]

    drafts = chunk_sections(sections, "plan.pdf", chunk_tokens=100, overlap_tokens=10)

    assert len(drafts) > 5
    assert [d.ordinal for d in drafts] == list(range(len(drafts)))
    # The splitter sizes pieces before re-joining them, so allow a few tokens of slack.
    assert all(d.token_count <= 105 and d.token_count == count_tokens(d.content) for d in drafts)
    assert all(d.page == 3 and d.heading_path == "Finance › 2026" for d in drafts)
    assert drafts[0].embed_text.startswith("plan.pdf › Finance › 2026\n\n")
    assert not drafts[0].content.startswith("plan.pdf")


def test_tsquery_drops_stopwords_and_punctuation():
    assert to_tsquery("Does my lease allow pets?!") == "lease | allow | pets"
    assert to_tsquery("what is it?") == ""
    assert to_tsquery("hợp đồng thuê nhà") == "hợp | đồng | thuê | nhà"


def test_join_overlapping_removes_shared_text():
    assert join_overlapping("alpha beta gamma", "beta gamma delta") == "alpha beta gamma delta"
    assert join_overlapping("one", "two") == "one\ntwo"
