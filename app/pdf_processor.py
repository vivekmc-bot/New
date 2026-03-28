"""
PDF Processor – extracts text from a PDF and separates questions
from reference notes.
"""

import re
import fitz  # PyMuPDF


# Patterns that identify a question line
_QUESTION_PATTERNS = [
    re.compile(r"^\s*\d+[\.\)]\s+\S"),          # 1. text / 1) text
    re.compile(r"^\s*[a-zA-Z][\.\)]\s+\S"),      # a. text / a) text
    re.compile(r"^\s*Q\.?\s*\d+", re.I),          # Q1 / Q.1
    re.compile(r"^\s*(Question|Ques)[\s\d]", re.I),
    re.compile(r"\?\s*$"),                         # ends with ?
]

# Marks annotations like [2 marks], (3 marks), 5 marks
_MARKS_RE = re.compile(
    r"\[?\(?\s*(\d+)\s*marks?\s*\)?\]?", re.I
)


def _is_question_line(line: str) -> bool:
    return any(p.search(line) for p in _QUESTION_PATTERNS)


class PDFProcessor:
    """Load a PDF and split its content into questions and reference notes."""

    def __init__(self):
        self.full_text: str = ""
        self.questions: list[dict] = []
        self._notes_lines: list[str] = []

    # ------------------------------------------------------------------
    def load_pdf(self, pdf_path: str) -> str:
        """Extract all text from *pdf_path* and populate questions/notes."""
        doc = fitz.open(pdf_path)
        pages: list[str] = [page.get_text() for page in doc]
        doc.close()

        self.full_text = "\n".join(pages)
        self._parse_content()
        return self.full_text

    # ------------------------------------------------------------------
    def _parse_content(self) -> None:
        """Heuristically split lines into questions and reference notes."""
        lines = self.full_text.splitlines()

        questions: list[dict] = []
        notes: list[str] = []
        q_buffer: list[str] = []

        def _flush_question(buf: list[str]) -> None:
            if not buf:
                return
            text = " ".join(buf).strip()
            if not text:
                return
            m = _MARKS_RE.search(text)
            # Fall back to 2 when no marks annotation is found in the PDF.
            # The GUI lets users override this via its "default marks" setting.
            marks = int(m.group(1)) if m else 2
            questions.append({"text": text, "marks": marks})

        for raw in lines:
            line = raw.strip()
            if not line:
                # blank line may end a question block
                if q_buffer:
                    _flush_question(q_buffer)
                    q_buffer = []
                continue

            if _is_question_line(line):
                # start of a new question
                _flush_question(q_buffer)
                q_buffer = [line]
            elif q_buffer:
                # continuation of a question (multi-line)
                q_buffer.append(line)
            else:
                notes.append(line)

        # flush any remaining question
        _flush_question(q_buffer)

        self.questions = questions
        self._notes_lines = notes

    # ------------------------------------------------------------------
    def get_questions(self) -> list[dict]:
        """Return list of dicts with keys ``text`` and ``marks``."""
        return self.questions

    def get_reference_notes(self) -> str:
        """Return the reference-notes text (non-question content)."""
        return "\n".join(self._notes_lines)
