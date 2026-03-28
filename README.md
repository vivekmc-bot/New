# Handwritten Notes Generator

> A desktop application that analyses your handwriting, reads a PDF containing
> reference notes and questions, synthesises mark-appropriate answers, and
> produces a PDF that looks like it was handwritten in a notebook.

Author – Vivek

---

## Features

| Feature | Details |
|---------|---------|
| **Handwriting-style mimicry** | Upload a photo/scan of your own handwriting; the app extracts your ink colour and letter size and applies them to the output. |
| **PDF input** | Accepts any PDF containing both reference notes and questions. |
| **Automatic question detection** | Detects numbered questions (`1.`, `Q1`, etc.) and questions ending in `?`. |
| **Mark-aware answer synthesis** | Answers are generated with a word-count scaled to the marks value (e.g. `[2 marks]`, `[5 marks]`). |
| **TF-IDF retrieval** | Finds the most relevant sentences from the reference notes for each question without copying text verbatim. |
| **Notebook PDF output** | Renders the answers onto ruled notebook paper with a red margin line, subtle paper texture, and per-character handwriting variations. |

---

## Requirements

- Python 3.10+
- Packages listed in `requirements.txt`

```bash
pip install -r requirements.txt
```

---

## Running the Application

```bash
python main.py
```

The GUI walks you through four steps:

1. **Handwriting sample** *(optional)* – browse to a PNG/JPG image of your handwriting.
2. **Input PDF** – browse to the PDF that contains both reference notes and questions.
3. **Settings** – set the default marks per question (overridden automatically when the PDF specifies marks).
4. **Output PDF** – choose where to save the generated handwritten-notes PDF.

Click **✍ Generate Handwritten Notes** and the app processes everything in the background.

---

## Running Tests

```bash
python -m pytest tests/ -v
```

---

## Project Structure

```
.
├── main.py                      # Entry point – launches the GUI
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── gui.py                   # Tkinter GUI
│   ├── pdf_processor.py         # PDF text extraction & question detection
│   ├── answer_generator.py      # TF-IDF answer synthesis
│   └── handwriting_renderer.py  # Handwriting-style image/PDF renderer
└── tests/
    └── test_app.py              # Pytest test suite (18 tests)
```
