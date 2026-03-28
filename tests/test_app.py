"""
Tests for the Handwritten Notes Generator.

Run with:  python -m pytest tests/ -v
"""

import os
import tempfile

import fitz  # PyMuPDF
import pytest
from PIL import Image, ImageDraw, ImageFont


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_test_pdf(path: str, include_questions: bool = True) -> None:
    """Create a minimal PDF with reference notes and optional questions."""
    doc = fitz.open()
    page = doc.new_page()

    content = (
        "Machine Learning Overview\n\n"
        "Machine learning is a branch of artificial intelligence that enables "
        "systems to learn from data without being explicitly programmed.\n\n"
        "Supervised learning uses labelled training data to learn a mapping "
        "from inputs to outputs.\n\n"
        "Unsupervised learning finds hidden patterns in data without labels.\n\n"
    )
    if include_questions:
        content += (
            "1. What is machine learning? [2 marks]\n\n"
            "2. Explain supervised learning. [3 marks]\n\n"
        )

    page.insert_text((50, 50), content, fontsize=11)
    doc.save(path)
    doc.close()


def _make_hw_sample(path: str) -> None:
    """Create a synthetic handwriting-sample image (blue on cream)."""
    img = Image.new("RGB", (400, 150), (255, 252, 240))
    draw = ImageDraw.Draw(img)
    # Use the same cross-platform font search as HandwritingRenderer
    from app.handwriting_renderer import _find_font
    font_path = _find_font()
    try:
        font = ImageFont.truetype(font_path, 28) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    draw.text((20, 30), "Sample handwriting", font=font, fill=(30, 25, 130))
    draw.text((20, 80), "Second line", font=font, fill=(30, 25, 130))
    img.save(path)


# ---------------------------------------------------------------------------
# PDFProcessor
# ---------------------------------------------------------------------------

class TestPDFProcessor:
    def test_load_extracts_text(self, tmp_path):
        from app.pdf_processor import PDFProcessor

        pdf_file = str(tmp_path / "test.pdf")
        _make_test_pdf(pdf_file)

        proc = PDFProcessor()
        text = proc.load_pdf(pdf_file)
        assert "Machine Learning" in text

    def test_detects_questions(self, tmp_path):
        from app.pdf_processor import PDFProcessor

        pdf_file = str(tmp_path / "test.pdf")
        _make_test_pdf(pdf_file, include_questions=True)

        proc = PDFProcessor()
        proc.load_pdf(pdf_file)
        questions = proc.get_questions()

        assert len(questions) == 2, f"Expected 2 questions, got {len(questions)}"

    def test_question_marks_parsed(self, tmp_path):
        from app.pdf_processor import PDFProcessor

        pdf_file = str(tmp_path / "test.pdf")
        _make_test_pdf(pdf_file, include_questions=True)

        proc = PDFProcessor()
        proc.load_pdf(pdf_file)
        questions = proc.get_questions()

        marks = [q["marks"] for q in questions]
        assert 2 in marks
        assert 3 in marks

    def test_reference_notes_extracted(self, tmp_path):
        from app.pdf_processor import PDFProcessor

        pdf_file = str(tmp_path / "test.pdf")
        _make_test_pdf(pdf_file)

        proc = PDFProcessor()
        proc.load_pdf(pdf_file)
        ref = proc.get_reference_notes()

        assert len(ref) > 50
        assert "machine learning" in ref.lower()

    def test_no_questions_pdf(self, tmp_path):
        from app.pdf_processor import PDFProcessor

        pdf_file = str(tmp_path / "test.pdf")
        _make_test_pdf(pdf_file, include_questions=False)

        proc = PDFProcessor()
        proc.load_pdf(pdf_file)
        questions = proc.get_questions()

        assert isinstance(questions, list)  # may be empty – that's fine


# ---------------------------------------------------------------------------
# AnswerGenerator
# ---------------------------------------------------------------------------

class TestAnswerGenerator:
    _REF = (
        "Machine learning is a branch of artificial intelligence. "
        "It enables systems to learn from data.\n"
        "Supervised learning uses labelled data to train models. "
        "Each example has an input and a corresponding output label. "
        "The model learns to predict outputs for new inputs.\n"
        "Unsupervised learning finds patterns without labelled data. "
        "Clustering and dimensionality reduction are common tasks."
    )

    def test_load_reference(self):
        from app.answer_generator import AnswerGenerator

        gen = AnswerGenerator()
        ok = gen.load_reference(self._REF)
        assert ok is True

    def test_answer_generated(self):
        from app.answer_generator import AnswerGenerator

        gen = AnswerGenerator()
        gen.load_reference(self._REF)
        answer = gen.generate_answer("What is machine learning?", marks=2)

        assert isinstance(answer, str)
        assert len(answer.split()) > 5

    def test_answer_length_scales_with_marks(self):
        from app.answer_generator import AnswerGenerator

        gen = AnswerGenerator()
        gen.load_reference(self._REF)

        ans_2 = gen.generate_answer("Explain machine learning", marks=2)
        ans_5 = gen.generate_answer("Explain machine learning", marks=5)

        # The 5-mark answer should generally be longer than the 2-mark one
        assert len(ans_5.split()) >= len(ans_2.split())

    def test_fallback_answer_no_reference(self):
        from app.answer_generator import AnswerGenerator

        gen = AnswerGenerator()
        # Do NOT load any reference
        answer = gen.generate_answer("Describe neural networks", marks=3)

        assert isinstance(answer, str)
        assert len(answer) > 20

    def test_empty_reference(self):
        from app.answer_generator import AnswerGenerator

        gen = AnswerGenerator()
        ok = gen.load_reference("")
        assert ok is False
        # Should still produce a fallback answer
        answer = gen.generate_answer("Any question", marks=2)
        assert isinstance(answer, str)


# ---------------------------------------------------------------------------
# HandwritingAnalyzer
# ---------------------------------------------------------------------------

class TestHandwritingAnalyzer:
    def test_analyze_synthetic_sample(self, tmp_path):
        from app.handwriting_renderer import HandwritingAnalyzer

        sample_path = str(tmp_path / "sample.png")
        _make_hw_sample(sample_path)

        a = HandwritingAnalyzer()
        ok = a.analyze(sample_path)

        assert ok is True
        # Should detect blue-ish ink (b channel > r channel)
        r, g, b = a.ink_color
        assert b > r, f"Expected blue ink, got {a.ink_color}"

    def test_analyze_invalid_path(self):
        from app.handwriting_renderer import HandwritingAnalyzer

        a = HandwritingAnalyzer()
        ok = a.analyze("/nonexistent/file.png")
        assert ok is False
        # Defaults should remain
        assert a.ink_color is not None

    def test_defaults_reasonable(self):
        from app.handwriting_renderer import HandwritingAnalyzer

        a = HandwritingAnalyzer()
        assert 10 <= a.font_size <= 80
        assert a.line_height >= a.font_size


# ---------------------------------------------------------------------------
# HandwritingRenderer
# ---------------------------------------------------------------------------

class TestHandwritingRenderer:
    _SAMPLE_TEXT = (
        "Q1. What is machine learning? [2 marks]\n\n"
        "Answer (2 marks):\n"
        "Machine learning is a branch of AI that enables systems to learn.\n\n"
        "────────────────────────────────────────\n"
    )

    def test_render_pages_creates_pdf(self, tmp_path):
        from app.handwriting_renderer import HandwritingRenderer

        out = str(tmp_path / "out.pdf")
        renderer = HandwritingRenderer()
        pages = renderer.split_text_into_pages(self._SAMPLE_TEXT)
        renderer.render_pages(pages, out)

        assert os.path.exists(out)
        assert os.path.getsize(out) > 10_000  # at least 10 KB

    def test_split_text_into_pages(self):
        from app.handwriting_renderer import HandwritingRenderer

        renderer = HandwritingRenderer()
        # Generate enough text to force multiple pages
        long_text = "\n".join([f"Line {i}" for i in range(200)])
        pages = renderer.split_text_into_pages(long_text)

        assert len(pages) >= 2

    def test_background_has_notebook_characteristics(self):
        from app.handwriting_renderer import HandwritingRenderer
        import numpy as np

        renderer = HandwritingRenderer()
        img = renderer._make_background()

        arr = np.array(img)
        # Background should be light (cream)
        assert arr.mean() > 200
        # There should be some blue-ish pixels (ruling lines)
        blue_channel_high = (arr[:, :, 2] > arr[:, :, 0]).sum()
        assert blue_channel_high > 100

    def test_render_with_handwriting_sample(self, tmp_path):
        from app.handwriting_renderer import HandwritingAnalyzer, HandwritingRenderer

        sample_path = str(tmp_path / "sample.png")
        _make_hw_sample(sample_path)

        analyzer = HandwritingAnalyzer()
        analyzer.analyze(sample_path)

        renderer = HandwritingRenderer(analyzer=analyzer)
        out = str(tmp_path / "out_styled.pdf")
        pages = renderer.split_text_into_pages(self._SAMPLE_TEXT)
        renderer.render_pages(pages, out)

        assert os.path.exists(out)
        assert os.path.getsize(out) > 10_000


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------

class TestEndToEnd:
    def test_full_pipeline(self, tmp_path):
        from app.pdf_processor import PDFProcessor
        from app.answer_generator import AnswerGenerator
        from app.handwriting_renderer import HandwritingAnalyzer, HandwritingRenderer

        # Setup
        pdf_in = str(tmp_path / "notes.pdf")
        pdf_out = str(tmp_path / "handwritten.pdf")
        _make_test_pdf(pdf_in, include_questions=True)

        # Process
        proc = PDFProcessor()
        proc.load_pdf(pdf_in)
        questions = proc.get_questions()
        ref = proc.get_reference_notes()

        gen = AnswerGenerator()
        gen.load_reference(ref)

        output_lines = []
        for idx, q in enumerate(questions, 1):
            marks = q["marks"]
            answer = gen.generate_answer(q["text"], marks)
            output_lines += [
                f"Q{idx}. {q['text']}",
                "",
                f"Answer ({marks} marks):",
                answer,
                "",
                "─" * 40,
                "",
            ]

        renderer = HandwritingRenderer(analyzer=HandwritingAnalyzer())
        pages = renderer.split_text_into_pages("\n".join(output_lines))
        renderer.render_pages(pages, pdf_out)

        assert os.path.exists(pdf_out)
        assert os.path.getsize(pdf_out) > 5_000
        assert len(questions) == 2
