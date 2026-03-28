"""
GUI – Tkinter-based user interface for the Handwritten Notes Generator.
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class HandwritingNotesApp:
    """Main application window."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Handwritten Notes Generator")
        self.root.geometry("720x620")
        self.root.resizable(True, True)

        # ── variables ──────────────────────────────────────────────────
        self.hw_sample_path = tk.StringVar()
        self.pdf_input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.default_marks = tk.IntVar(value=2)
        self.status_text = tk.StringVar(value="Ready.")

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Title.TLabel", font=("Helvetica", 16, "bold"))
        style.configure("Desc.TLabel", foreground="#666666")

        main = ttk.Frame(self.root, padding=20)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        # Title
        ttk.Label(main, text="✍  Handwritten Notes Generator",
                  style="Title.TLabel").grid(
            row=0, column=0, columnspan=3, pady=(0, 18)
        )

        # ── Step 1 ──────────────────────────────────────────────────
        self._file_row(
            parent=main, grid_row=1,
            title="Step 1 – Handwriting Sample  (optional)",
            desc="Upload a photo/scan of your own handwriting so the app can "
                 "mimic your ink colour and letter size.",
            var=self.hw_sample_path,
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff"),
                       ("All files", "*.*")],
        )

        # ── Step 2 ──────────────────────────────────────────────────
        self._file_row(
            parent=main, grid_row=3,
            title="Step 2 – Input PDF  (reference notes + questions)",
            desc="Upload the PDF that contains both the reference notes and "
                 "the questions to be answered.",
            var=self.pdf_input_path,
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )

        # ── Step 3 – settings ───────────────────────────────────────
        sf = ttk.LabelFrame(main, text="Step 3 – Settings", padding=10)
        sf.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)
        sf.columnconfigure(1, weight=1)

        ttk.Label(sf, text="Default marks per question:").grid(
            row=0, column=0, sticky="w", padx=5
        )
        ttk.Spinbox(sf, from_=1, to=20,
                    textvariable=self.default_marks, width=6).grid(
            row=0, column=1, sticky="w", padx=5
        )
        ttk.Label(sf,
                  text="(Overridden automatically when marks are specified in "
                       "the PDF, e.g. '[3 marks]'.)",
                  style="Desc.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=5, pady=(2, 0)
        )

        # ── Step 4 – output ─────────────────────────────────────────
        self._file_row(
            parent=main, grid_row=6,
            title="Step 4 – Output PDF location",
            desc="Choose where to save the generated handwritten-notes PDF.",
            var=self.output_path,
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            save=True,
        )

        # ── Generate button ──────────────────────────────────────────
        self.gen_btn = ttk.Button(
            main, text="✍  Generate Handwritten Notes",
            command=self._on_generate,
        )
        self.gen_btn.grid(row=8, column=0, columnspan=3, pady=(18, 6))

        # Progress bar
        self.progress = ttk.Progressbar(
            main, mode="indeterminate", length=500
        )
        self.progress.grid(row=9, column=0, columnspan=3, pady=4)

        # Status
        ttk.Label(main, textvariable=self.status_text,
                  style="Desc.TLabel").grid(
            row=10, column=0, columnspan=3
        )

    def _file_row(
        self, parent, grid_row: int, title: str, desc: str,
        var: tk.StringVar, filetypes: list, save: bool = False,
    ) -> None:
        frame = ttk.LabelFrame(parent, text=title, padding=10)
        frame.grid(row=grid_row, column=0, columnspan=3,
                   sticky="ew", pady=5)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text=desc, style="Desc.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )
        ttk.Entry(frame, textvariable=var).grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=(0, 6)
        )

        if save:
            cmd = lambda v=var, ft=filetypes: self._save_dialog(v, ft)
            btn_text = "Save as…"
        else:
            cmd = lambda v=var, ft=filetypes: self._open_dialog(v, ft)
            btn_text = "Browse…"

        ttk.Button(frame, text=btn_text, command=cmd).grid(
            row=1, column=2, sticky="e"
        )

    # ------------------------------------------------------------------
    # Dialog helpers
    # ------------------------------------------------------------------

    def _open_dialog(self, var: tk.StringVar, filetypes: list) -> None:
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            var.set(path)

    def _save_dialog(self, var: tk.StringVar, filetypes: list) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=filetypes
        )
        if path:
            var.set(path)

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def _on_generate(self) -> None:
        pdf_in = self.pdf_input_path.get().strip()
        out = self.output_path.get().strip()

        if not pdf_in:
            messagebox.showerror("Missing input", "Please select an input PDF.")
            return
        if not os.path.exists(pdf_in):
            messagebox.showerror("File not found",
                                 f"Cannot find:\n{pdf_in}")
            return
        if not out:
            messagebox.showerror("Missing output",
                                 "Please specify an output file path.")
            return

        self.gen_btn.config(state="disabled")
        self.progress.start(12)
        self._set_status("Starting…")

        thread = threading.Thread(target=self._worker, daemon=True)
        thread.start()

    def _worker(self) -> None:
        """Background thread that does the heavy lifting."""
        try:
            from app.pdf_processor import PDFProcessor
            from app.answer_generator import AnswerGenerator
            from app.handwriting_renderer import (
                HandwritingAnalyzer, HandwritingRenderer,
            )

            pdf_in = self.pdf_input_path.get().strip()
            out = self.output_path.get().strip()
            hw_sample = self.hw_sample_path.get().strip()
            def_marks = self.default_marks.get()

            # 1. Read PDF
            self._set_status("Reading PDF…")
            processor = PDFProcessor()
            processor.load_pdf(pdf_in)
            questions = processor.get_questions()
            ref_text = processor.get_reference_notes()

            # 2. Generate answers
            self._set_status("Analysing content and generating answers…")
            gen = AnswerGenerator()
            gen.load_reference(ref_text)

            output_lines: list[str] = []
            total = len(questions)

            if total == 0:
                # No questions detected – render the whole document as notes
                self._set_status("No questions detected – rendering full notes…")
                output_lines = ref_text.splitlines()
            else:
                for idx, q in enumerate(questions, 1):
                    self._set_status(
                        f"Answering question {idx}/{total}…"
                    )
                    marks = q.get("marks", def_marks)
                    answer = gen.generate_answer(q["text"], marks)

                    output_lines += [
                        f"Q{idx}. {q['text']}",
                        "",
                        f"Answer  ({marks} {'mark' if marks == 1 else 'marks'}):",
                        answer,
                        "",
                        "─" * 40,
                        "",
                    ]

            # 3. Analyse handwriting sample
            self._set_status("Analysing handwriting style…")
            analyzer = HandwritingAnalyzer()
            if hw_sample and os.path.exists(hw_sample):
                analyzer.analyze(hw_sample)

            # 4. Render
            self._set_status("Rendering handwritten notes…")
            renderer = HandwritingRenderer(analyzer=analyzer)
            pages = renderer.split_text_into_pages("\n".join(output_lines))
            renderer.render_pages(pages, out)

            self.root.after(0, self._on_success, out)

        except Exception as exc:
            import traceback
            traceback.print_exc()
            self.root.after(0, self._on_error, str(exc))

    # ------------------------------------------------------------------
    # Callbacks (run on main thread via root.after)
    # ------------------------------------------------------------------

    def _set_status(self, msg: str) -> None:
        self.root.after(0, lambda: self.status_text.set(msg))

    def _on_success(self, out_path: str) -> None:
        self.progress.stop()
        self.gen_btn.config(state="normal")
        self.status_text.set(f"Done!  Saved → {out_path}")
        messagebox.showinfo(
            "Success",
            f"Handwritten notes generated successfully!\n\nSaved to:\n{out_path}",
        )

    def _on_error(self, msg: str) -> None:
        self.progress.stop()
        self.gen_btn.config(state="normal")
        self.status_text.set(f"Error: {msg}")
        messagebox.showerror("Error", f"Generation failed:\n\n{msg}")
