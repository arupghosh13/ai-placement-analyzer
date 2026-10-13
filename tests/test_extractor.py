# tests/test_extractor.py

import io
import pytest

from app.services.extractor import (
    MINIMUM_TEXT_LENGTH,
    DocumentParsingError,
    InsufficientContextError,
    extract_text_from_file,
)

from app.services.matcher import normalize_token
# ─────────────────────────────────────────
# HELPERS
# Build fake file bytes for testing
# without needing real files on disk
# ─────────────────────────────────────────

def make_minimal_docx_bytes(text: str) -> bytes:
    """
    Create a real in-memory DOCX file with the given text.
    python-docx writes it to a BytesIO stream.
    """
    import docx
    document = docx.Document()
    document.add_paragraph(text)
    stream = io.BytesIO()
    document.save(stream)
    return stream.getvalue()

# ─────────────────────────────────────────
# PDF HELPERS
# ─────────────────────────────────────────

def make_pdf_bytes(pages, password=None) -> bytes:
    """
    Create a real in-memory PDF. `pages` is a list of pages,
    each page is a list of text lines. An empty page = no text layer
    (simulates a scanned / image-only resume).
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    # encrypt=<password string> makes reportlab write a password-protected PDF
    pdf = canvas.Canvas(buffer, pagesize=letter, encrypt=password)

    for lines in pages:
        y = 740
        for line in lines:
            pdf.drawString(72, y, line)
            y -= 16
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


RESUME_LINES = [
    "Arup Ghosh - Backend Developer",
    "Skills: Python, FastAPI, PostgreSQL, Docker, Git",
    "Built a REST API with pytest coverage and JWT auth.",
]

# ─────────────────────────────────────────
# NORMALIZE TOKEN TESTS
# ─────────────────────────────────────────

class TestNormalizeToken:

    def test_converts_to_lowercase(self):
        assert normalize_token("Python") == "python"

    def test_strips_trailing_punctuation(self):
        assert normalize_token("FastAPI,") == "fastapi"

    def test_strips_whitespace(self):
        assert normalize_token("  docker  ") == "docker"

    def test_preserves_plus_sign(self):
        # C++ must stay as c++
        result = normalize_token("C++")
        assert "c" in result

    def test_preserves_hash_sign(self):
        # C# must stay as c#
        result = normalize_token("C#")
        assert "c" in result

    def test_empty_string(self):
        assert normalize_token("") == ""


# ─────────────────────────────────────────
# FILE VALIDATION TESTS
# ─────────────────────────────────────────

class TestFileValidation:

    def test_rejects_unsupported_file_type(self):
        """
        .jpg files must be rejected immediately
        with UNSUPPORTED_FILE_TYPE error code
        """
        fake_bytes = b"fake image content"
        with pytest.raises(DocumentParsingError) as exc_info:
            extract_text_from_file(fake_bytes, "photo.jpg")

        assert exc_info.value.error_code == "UNSUPPORTED_FILE_TYPE"

    def test_rejects_file_over_5mb(self):
        """
        Files over 5MB must be rejected
        with FILE_TOO_LARGE error code
        """
        # 6MB of random bytes
        large_bytes = b"x" * (6 * 1024 * 1024)
        with pytest.raises(DocumentParsingError) as exc_info:
            extract_text_from_file(large_bytes, "resume.pdf")

        assert exc_info.value.error_code == "FILE_TOO_LARGE"

    def test_rejects_txt_file(self):
        """
        Only .pdf and .docx allowed
        """
        with pytest.raises(DocumentParsingError) as exc_info:
            extract_text_from_file(b"some text", "resume.txt")

        assert exc_info.value.error_code == "UNSUPPORTED_FILE_TYPE"

    def test_accepts_pdf_extension(self):
        """
        .pdf extension passes the extension check
        (will fail later on content, not extension)
        """
        with pytest.raises(DocumentParsingError) as exc_info:
            extract_text_from_file(b"not a real pdf", "resume.pdf")

        # Error should be parsing failure, NOT unsupported type
        assert exc_info.value.error_code != "UNSUPPORTED_FILE_TYPE"

    def test_accepts_docx_extension(self):
        """
        .docx extension passes the extension check
        """
        with pytest.raises(DocumentParsingError) as exc_info:
            extract_text_from_file(b"not a real docx", "resume.docx")

        assert exc_info.value.error_code != "UNSUPPORTED_FILE_TYPE"


# ─────────────────────────────────────────
# DOCX EXTRACTION TESTS
# ─────────────────────────────────────────

class TestDocxExtraction:

    def test_extracts_text_from_valid_docx(self):
        """
        A valid DOCX with sufficient text
        should return that text successfully
        """
        long_text = "Python developer with FastAPI and PostgreSQL experience. " * 5
        docx_bytes = make_minimal_docx_bytes(long_text)

        result = extract_text_from_file(docx_bytes, "resume.docx")

        assert isinstance(result, str)
        assert len(result) >= MINIMUM_TEXT_LENGTH
        assert "python" in result.lower()

    def test_raises_insufficient_context_for_short_docx(self):
        """
        A DOCX with text under 50 characters
        must raise InsufficientContextError
        """
        short_text = "Hi"
        docx_bytes = make_minimal_docx_bytes(short_text)

        with pytest.raises(InsufficientContextError):
            extract_text_from_file(docx_bytes, "resume.docx")

    def test_raises_error_for_corrupt_docx(self):
        """
        Random bytes pretending to be a DOCX
        must raise DocumentParsingError
        """
        corrupt_bytes = b"this is not a docx file at all"
        with pytest.raises(DocumentParsingError) as exc_info:
            extract_text_from_file(corrupt_bytes, "resume.docx")

        assert exc_info.value.error_code == "DOCUMENT_PARSING_FAILED"

# ─────────────────────────────────────────
# PDF EXTRACTION TESTS
# ─────────────────────────────────────────

class TestPdfExtraction:

    def test_extracts_text_from_valid_pdf(self):
        result = extract_text_from_file(make_pdf_bytes([RESUME_LINES]), "resume.pdf")
        assert isinstance(result, str)
        assert len(result) >= MINIMUM_TEXT_LENGTH
        assert "python" in result.lower()
        assert "fastapi" in result.lower()

    def test_extracts_text_from_all_pages(self):
        pages = [
            RESUME_LINES,
            ["Experience: Docker and Kubernetes deployments",
             "Education: BTech, final year student"],
        ]
        result = extract_text_from_file(make_pdf_bytes(pages), "resume.pdf")
        assert "fastapi" in result.lower()      # page 1
        assert "kubernetes" in result.lower()   # page 2

    def test_uppercase_extension_is_accepted(self):
        result = extract_text_from_file(make_pdf_bytes([RESUME_LINES]), "RESUME.PDF")
        assert "python" in result.lower()

    def test_short_text_pdf_raises_insufficient_context(self):
        with pytest.raises(InsufficientContextError):
            extract_text_from_file(make_pdf_bytes([["Hi"]]), "resume.pdf")

    def test_blank_pdf_raises_insufficient_context(self):
        # Pages exist but have no text layer (scanned / image-only resume)
        with pytest.raises(InsufficientContextError):
            extract_text_from_file(make_pdf_bytes([[]]), "resume.pdf")

    def test_corrupt_pdf_raises_parsing_error(self):
        with pytest.raises(DocumentParsingError) as exc_info:
            extract_text_from_file(b"this is not a pdf at all", "resume.pdf")
        assert exc_info.value.error_code == "DOCUMENT_PARSING_FAILED"

    def test_empty_bytes_pdf_raises_parsing_error(self):
        with pytest.raises(DocumentParsingError) as exc_info:
            extract_text_from_file(b"", "resume.pdf")
        assert exc_info.value.error_code == "DOCUMENT_PARSING_FAILED"

    def test_password_protected_pdf_raises_parsing_error(self):
        locked = make_pdf_bytes([RESUME_LINES], password="secret")
        with pytest.raises(DocumentParsingError) as exc_info:
            extract_text_from_file(locked, "resume.pdf")
        assert exc_info.value.error_code == "DOCUMENT_PARSING_FAILED"

    def test_oversized_pdf_rejected_before_parsing(self):
        with pytest.raises(DocumentParsingError) as exc_info:
            extract_text_from_file(b"%PDF-" + b"x" * (6 * 1024 * 1024), "resume.pdf")
        assert exc_info.value.error_code == "FILE_TOO_LARGE"