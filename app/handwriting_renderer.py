"""
Handwriting Renderer – analyses an optional handwriting sample image to
extract ink colour and approximate letter size, then renders text onto
notebook-style PIL Images and saves them as a multi-page PDF.
"""

import math
import os
import random
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# A4 (210 × 297 mm) at 200 dpi gives a comfortable desktop-sized output.
# 210 mm × (200/25.4) ≈ 1654 px wide; 297 mm × (200/25.4) ≈ 2339 px tall.
# ---------------------------------------------------------------------------
PAGE_W, PAGE_H = 1654, 2339  # A4 @ 200 dpi
MARGIN_LEFT = 148
MARGIN_TOP = 100
MARGIN_RIGHT_PAD = 60


# ---------------------------------------------------------------------------
# Candidate system fonts (checked in order; first existing one wins)
# ---------------------------------------------------------------------------
_FONT_CANDIDATES = [
    # Liberation Serif gives a pen-like appearance at slight italic
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
    # macOS
    "/Library/Fonts/Arial.ttf",
    # Windows
    "C:/Windows/Fonts/times.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _find_font() -> Optional[str]:
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


# ---------------------------------------------------------------------------

class HandwritingAnalyzer:
    """
    Analyses a handwriting sample image to extract rendering parameters.
    Falls back gracefully to sensible defaults if analysis is not possible.
    """

    def __init__(self):
        self.ink_color: tuple[int, int, int] = (30, 25, 130)  # blue-ish default
        self.font_size: int = 28
        self.line_height: int = 48

    # ------------------------------------------------------------------
    def analyze(self, image_path: str) -> bool:
        """
        Extract ink colour and estimate letter height from *image_path*.
        Returns ``True`` on success, ``False`` on failure.
        """
        try:
            img = Image.open(image_path).convert("RGB")
            arr = np.array(img, dtype=np.float32)
            self._extract_color(arr)
            self._estimate_size(arr)
            return True
        except Exception as exc:
            print(f"[HandwritingAnalyzer] Could not analyse sample: {exc}")
            return False

    # ------------------------------------------------------------------
    def _extract_color(self, arr: np.ndarray) -> None:
        gray = arr.mean(axis=2)
        # Treat darkest 8 % of pixels as ink
        threshold = np.percentile(gray, 8)
        mask = gray < threshold
        if mask.any():
            median = np.median(arr[mask], axis=0)
            self.ink_color = tuple(int(c) for c in median)

    def _estimate_size(self, arr: np.ndarray) -> None:
        gray = arr.mean(axis=2)
        bg = np.median(gray)
        ink_rows = (gray < bg * 0.75).sum(axis=1)

        if ink_rows.max() == 0:
            return

        normed = ink_rows / ink_rows.max()
        in_line, start = False, 0
        heights: list[int] = []

        for i, d in enumerate(normed):
            if not in_line and d > 0.1:
                in_line, start = True, i
            elif in_line and d <= 0.1:
                in_line = False
                heights.append(i - start)

        if len(heights) >= 2:
            avg_h = int(np.median(heights))
            self.font_size = max(20, min(50, int(avg_h * 1.2)))
            self.line_height = max(38, int(avg_h * 2.4))


# ---------------------------------------------------------------------------

class HandwritingRenderer:
    """
    Renders plain text into notebook-style PIL images and saves as PDF.

    Parameters
    ----------
    analyzer:
        An *already populated* :class:`HandwritingAnalyzer` instance.
        If ``None``, default parameters are used.
    font_path:
        Explicit path to a .ttf font.  Searched automatically when ``None``.
    """

    def __init__(
        self,
        analyzer: Optional[HandwritingAnalyzer] = None,
        font_path: Optional[str] = None,
    ):
        self.analyzer = analyzer or HandwritingAnalyzer()
        self._font_path = font_path or _find_font()

        # Derived parameters (overrideable)
        self.font_size: int = self.analyzer.font_size
        self.line_height: int = self.analyzer.line_height

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render_pages(self, pages: list[str], output_path: str) -> str:
        """
        Render each item in *pages* as one notebook page and save to
        *output_path* as a multi-page PDF.  Returns *output_path*.
        """
        images = [self._render_page(text) for text in pages]
        rgb_images = [img.convert("RGB") for img in images]

        if not rgb_images:
            rgb_images = [self._render_page("")]

        rgb_images[0].save(
            output_path,
            save_all=True,
            append_images=rgb_images[1:],
            format="PDF",
            resolution=200,
        )
        return output_path

    def split_text_into_pages(self, text: str) -> list[str]:
        """Divide *text* into chunks that fit on one notebook page."""
        usable_h = PAGE_H - MARGIN_TOP - 80
        lines_per_page = max(1, int(usable_h / self.line_height))

        lines = text.splitlines()
        pages: list[str] = []
        buf: list[str] = []

        for line in lines:
            buf.append(line)
            if len(buf) >= lines_per_page:
                pages.append("\n".join(buf))
                buf = []

        if buf:
            pages.append("\n".join(buf))

        return pages or [""]

    # ------------------------------------------------------------------
    # Private rendering helpers
    # ------------------------------------------------------------------

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        if self._font_path:
            try:
                return ImageFont.truetype(self._font_path, size)
            except Exception:
                pass
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()

    def _render_page(self, text: str) -> Image.Image:
        img = self._make_background()
        draw = ImageDraw.Draw(img)
        font = self._get_font(self.font_size)

        max_x = PAGE_W - MARGIN_RIGHT_PAD
        x_origin = MARGIN_LEFT
        y = MARGIN_TOP

        for raw_line in text.splitlines():
            if y + self.line_height > PAGE_H - 40:
                break
            # Word-wrap long lines
            wrapped = self._wrap_line(raw_line, font, max_x - x_origin)
            for sub_line in wrapped:
                if y + self.line_height > PAGE_H - 40:
                    break
                self._draw_handwritten_line(draw, sub_line, x_origin, y, font)
                y += self.line_height

        return img

    def _wrap_line(self, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
        """Wrap *text* to fit within *max_w* pixels."""
        if not text.strip():
            return [text]

        words = text.split(" ")
        lines: list[str] = []
        current: list[str] = []

        for word in words:
            candidate = " ".join(current + [word])
            w = self._text_width(candidate, font)
            if current and w > max_w:
                lines.append(" ".join(current))
                current = [word]
            else:
                current.append(word)

        if current:
            lines.append(" ".join(current))

        return lines or [""]

    @staticmethod
    def _text_width(text: str, font: ImageFont.FreeTypeFont) -> int:
        try:
            bbox = font.getbbox(text)
            return bbox[2] - bbox[0]
        except AttributeError:
            return int(len(text) * font.size * 0.62)

    def _draw_handwritten_line(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        font: ImageFont.FreeTypeFont,
    ) -> None:
        """
        Draw *text* character by character, adding micro-level variations
        to simulate natural handwriting:
          - tiny baseline jitter
          - slight per-character slant (via vertical offset gradient)
          - ink pressure variation (colour brightness)
          - minor horizontal spacing noise
        """
        ink = self.analyzer.ink_color
        current_x = float(x)

        # A gentle overall slant for the whole line (±2°)
        slant_px_per_char = random.uniform(-0.3, 0.5)

        for i, ch in enumerate(text):
            # --- baseline jitter ---
            dy = random.uniform(-2.0, 2.5)
            # --- slant offset accumulates left-to-right ---
            char_y = y + dy + slant_px_per_char * i

            # --- ink pressure: darken or lighten slightly ---
            pressure = random.uniform(-18, 8)
            char_color = tuple(
                max(0, min(255, int(c + pressure))) for c in ink
            )

            draw.text((current_x, char_y), ch, font=font, fill=char_color)

            cw = self._text_width(ch, font)
            # minor spacing noise
            current_x += cw + random.uniform(-0.4, 1.1)

    # ------------------------------------------------------------------
    def _make_background(self) -> Image.Image:
        """Create a ruled-notebook background with margin line and texture."""
        img = Image.new("RGB", (PAGE_W, PAGE_H), (255, 252, 238))
        draw = ImageDraw.Draw(img)

        # Horizontal ruling
        rule_color = (170, 210, 230)
        y = MARGIN_TOP + self.line_height - 5
        while y < PAGE_H - 30:
            draw.line([(80, y), (PAGE_W - 40, y)], fill=rule_color, width=1)
            y += self.line_height

        # Red margin line
        mx = MARGIN_LEFT - 20
        draw.line([(mx, 0), (mx, PAGE_H)], fill=(215, 130, 130), width=2)

        # Subtle paper grain
        arr = np.array(img, dtype=np.float32)
        noise = np.random.default_rng(seed=42).normal(0, 1.2, arr.shape)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)

        return Image.fromarray(arr)
