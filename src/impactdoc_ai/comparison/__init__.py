"""Doküman karşılaştırma bileşenleri."""

from impactdoc_ai.comparison.text_comparator import (
    ChangeType,
    ComparisonResult,
    TextChange,
    compare_documents,
    compare_texts,
    split_into_paragraphs,
)

__all__ = [
    "ChangeType",
    "ComparisonResult",
    "TextChange",
    "compare_documents",
    "compare_texts",
    "split_into_paragraphs",
]