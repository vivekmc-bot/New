"""
Answer Generator – uses TF-IDF similarity to find relevant sentences
from reference notes and composes answers scaled to the required marks.
"""

import re
import random
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Approximate target word-count per mark.
# Typical exam answers range from 20-40 words per mark; 40 is a safe upper bound
# that still gives enough detail for higher-mark questions.
_WORDS_PER_MARK = 40

# Light paraphrase substitutions applied probabilistically
_SUBSTITUTIONS = [
    (r"\bThe\b", "This"),
    (r"\bis defined as\b", "refers to"),
    (r"\bFor example\b", "As an illustration"),
    (r"\bHowever\b", "Nevertheless"),
    (r"\bFirstly\b", "To begin with"),
    (r"\bSecondly\b", "Furthermore"),
    (r"\bIn conclusion\b", "Therefore"),
    (r"\bIn addition\b", "Moreover"),
    (r"\bBecause\b", "Since"),
    (r"\bDue to\b", "Owing to"),
]


class AnswerGenerator:
    """Synthesise answers from reference text using TF-IDF retrieval."""

    def __init__(self):
        self._sentences: list[str] = []
        self._matrix = None
        self._vectorizer: Optional[TfidfVectorizer] = None

    # ------------------------------------------------------------------
    def load_reference(self, reference_text: str) -> bool:
        """Index the reference notes for similarity search."""
        chunks = self._chunk_text(reference_text)
        self._sentences = [s for s in chunks if len(s.split()) > 3]

        if not self._sentences:
            return False

        try:
            self._vectorizer = TfidfVectorizer(
                stop_words="english",
                max_features=15000,
                ngram_range=(1, 2),
            )
            self._matrix = self._vectorizer.fit_transform(self._sentences)
            return True
        except Exception as exc:
            print(f"[AnswerGenerator] Indexing failed: {exc}")
            return False

    # ------------------------------------------------------------------
    def generate_answer(self, question_text: str, marks: int = 2) -> str:
        """Return a synthesised answer scaled to *marks*."""
        clean_q = self._clean_question(question_text)

        if self._sentences and self._matrix is not None:
            try:
                q_vec = self._vectorizer.transform([clean_q])
                sims = cosine_similarity(q_vec, self._matrix)[0]

                top_k = min(marks * 4 + 3, len(self._sentences))
                top_idx = np.argsort(sims)[-top_k:][::-1]
                relevant = [
                    self._sentences[i] for i in top_idx if sims[i] > 0.04
                ]

                if relevant:
                    return self._compose(relevant, marks)
            except Exception as exc:
                print(f"[AnswerGenerator] Retrieval error: {exc}")

        return self._fallback_answer(clean_q, marks)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _chunk_text(text: str) -> list[str]:
        """Split text into sentence/paragraph chunks."""
        paragraphs = re.split(r"\n{2,}", text)
        chunks: list[str] = []
        for para in paragraphs:
            para = para.strip()
            if len(para.split()) > 40:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                chunks.extend(sentences)
            else:
                chunks.append(para)
        return [c.strip() for c in chunks if c.strip()]

    @staticmethod
    def _clean_question(q: str) -> str:
        """Strip marks notation and leading numbering from a question."""
        q = re.sub(r"\[?\(?\s*\d+\s*marks?\s*\)?\]?", "", q, flags=re.I)
        q = re.sub(r"^\s*\d+[\.\)]\s*", "", q)
        q = re.sub(r"^\s*[a-z][\.\)]\s*", "", q, flags=re.I)
        q = re.sub(r"^\s*Q\.?\s*\d+[\.:)]\s*", "", q, flags=re.I)
        return q.strip()

    def _compose(self, sentences: list[str], marks: int) -> str:
        """Build an answer of the right length from retrieved sentences."""
        target = marks * _WORDS_PER_MARK
        parts: list[str] = []
        current = 0

        for sent in sentences:
            if current >= target:
                break
            paraphrased = self._paraphrase(sent)
            parts.append(paraphrased)
            current += len(paraphrased.split())

        answer = " ".join(parts)

        # Hard-trim if too long
        words = answer.split()
        limit = int(target * 1.35)
        if len(words) > limit:
            words = words[:limit]
            answer = " ".join(words)
            if not answer.endswith("."):
                answer += "."

        return answer

    @staticmethod
    def _paraphrase(sentence: str) -> str:
        """Apply one random light substitution to avoid verbatim copying."""
        rng = random.Random(hash(sentence))
        sub = rng.choice(_SUBSTITUTIONS)
        return re.sub(sub[0], sub[1], sentence, count=1)

    @staticmethod
    def _fallback_answer(question: str, marks: int) -> str:
        """Produce a generic answer when no reference is available."""
        topic_words = re.sub(
            r"^(what|how|why|when|where|who|which|explain|describe|define|"
            r"list|discuss|outline)\s+",
            "",
            question,
            flags=re.I,
        )
        topic = " ".join(topic_words.split()[:6]) or question[:40]

        parts = [
            f"{topic.capitalize()} is a fundamental concept that involves "
            f"understanding its key principles and their practical significance."
        ]
        if marks >= 3:
            parts.append(
                "It encompasses various aspects that require careful analysis "
                "and systematic application in relevant contexts."
            )
        if marks >= 5:
            parts.append(
                "A thorough understanding of the underlying mechanisms enables "
                "effective problem-solving and informed decision-making across "
                "multiple domains."
            )
        return " ".join(parts)
