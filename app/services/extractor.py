# app/services/extractor.py

import pdfplumber
import docx
import io
import logging

# ─────────────────────────────────────────
# LOGGER SETUP
# Logs to console in Phase 1
# Phase 9 will upgrade this to structured JSON file logging
# ─────────────────────────────────────────

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────

MINIMUM_TEXT_LENGTH = 50          # Your zero-hallucination guard
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB limit from your spec
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


# ─────────────────────────────────────────
# CUSTOM EXCEPTIONS
# Raised by this service, caught by the route layer
# ─────────────────────────────────────────

class DocumentParsingError(Exception):
    """Raised when a document cannot be parsed."""
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class InsufficientContextError(Exception):
    """Raised when extracted text is too short to analyze safely."""
    def __init__(self):
        self.message = (
            "Insufficient context. The analyzer cannot safely process "
            "this input structure without hallucinating data metrics."
        )
        self.error_code = "INSUFFICIENT_CONTEXT"
        super().__init__(self.message)


# ─────────────────────────────────────────
# CORE EXTRACTION FUNCTIONS
# ───────────────────────────────────────── 

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract raw text from a PDF file.

    Args:
        file_bytes: Raw bytes of the PDF file

    Returns:
        Cleaned text string extracted from all pages

    Raises:
        DocumentParsingError: If PDF is unreadable, encrypted, or empty
    """
    try:
        text_parts = []

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:

            if len(pdf.pages) == 0:
                raise DocumentParsingError(
                    message="The uploaded PDF contains no pages.",
                    error_code="EMPTY_DOCUMENT"
                )

            for page_number, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()

                if page_text:
                    text_parts.append(page_text)
                else:
                    logger.warning(
                        f"Page {page_number} returned no text — "
                        f"may be image-based or empty."
                    )

        full_text = "\n".join(text_parts).strip()
        logger.info(f"PDF extracted successfully — {len(full_text)} characters")
        return full_text

    except DocumentParsingError:
        # Re-raise our own exceptions without wrapping them
        raise

    except Exception as e:
        logger.error(f"PDF parsing failed: {str(e)}")
        raise DocumentParsingError(
            message=(
                "The uploaded PDF structure is invalid, "
                "password-protected, or unreadable."
            ),
            error_code="DOCUMENT_PARSING_FAILED"
        )


def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extract raw text from a .docx Word file.

    Args:
        file_bytes: Raw bytes of the DOCX file

    Returns:
        Cleaned text string from all paragraphs

    Raises:
        DocumentParsingError: If DOCX is corrupted or unreadable
    """
    try:
        document = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [
            para.text.strip()
            for para in document.paragraphs
            if para.text.strip()  # Skip empty paragraphs
        ]

        if not paragraphs:
            raise DocumentParsingError(
                message="The uploaded DOCX file contains no readable text.",
                error_code="EMPTY_DOCUMENT"
            )

        full_text = "\n".join(paragraphs)
        logger.info(f"DOCX extracted successfully — {len(full_text)} characters")
        return full_text

    except DocumentParsingError:
        raise

    except Exception as e:
        logger.error(f"DOCX parsing failed: {str(e)}")
        raise DocumentParsingError(
            message="The uploaded DOCX file is corrupted or unreadable.",
            error_code="DOCUMENT_PARSING_FAILED"
        )


# ─────────────────────────────────────────
# MAIN ENTRY POINT
# Called by the route — routes never call
# extract_text_from_pdf directly
# ─────────────────────────────────────────

def extract_text_from_file(
    file_bytes: bytes,
    filename: str
) -> str:
    """
    Main extractor function. Detects file type and routes
    to the correct extraction function.

    Args:
        file_bytes: Raw bytes of the uploaded file
        filename: Original filename including extension

    Returns:
        Validated text string ready for matching engine

    Raises:
        DocumentParsingError: Invalid file type or parsing failure
        InsufficientContextError: Extracted text too short
    """

    # ── Validate file size ──────────────────
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise DocumentParsingError(
            message="File size exceeds the 5MB limit.",
            error_code="FILE_TOO_LARGE"
        )

    # ── Validate file extension ─────────────
    file_extension = "." + filename.rsplit(".", 1)[-1].lower()

    if file_extension not in ALLOWED_EXTENSIONS:
        raise DocumentParsingError(
            message=(
                f"File type '{file_extension}' is not supported. "
                f"Please upload a .pdf or .docx file."
            ),
            error_code="UNSUPPORTED_FILE_TYPE"
        )

    # ── Route to correct extractor ──────────
    if file_extension == ".docx":
        raw_text = extract_text_from_docx(file_bytes)
    else:
        raw_text = extract_text_from_pdf(file_bytes)

    # ── Zero-hallucination guard ────────────
    # Your spec: if text < 50 chars, return "Insufficient-context-error"
    if len(raw_text.strip()) < MINIMUM_TEXT_LENGTH:
        logger.warning(
            f"Extracted text too short: {len(raw_text)} characters. "
            f"Raising InsufficientContextError."
        )
        raise InsufficientContextError()

    return raw_text