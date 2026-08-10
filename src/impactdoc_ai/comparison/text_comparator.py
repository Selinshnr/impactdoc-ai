"""Metin belgeleri arasındaki değişiklikleri tespit eder."""

from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum
from typing import Any


class ChangeType(str, Enum):
    """Dokümanda tespit edilebilecek değişiklik türleri."""

    UNCHANGED = "unchanged"
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


@dataclass
class TextChange:
    """Tek bir metin değişikliğini temsil eder."""

    change_type: ChangeType
    old_text: str | None = None
    new_text: str | None = None
    old_position: int | None = None
    new_position: int | None = None
    similarity_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Değişiklik nesnesini sözlüğe dönüştürür."""

        return {
            "change_type": self.change_type.value,
            "old_text": self.old_text,
            "new_text": self.new_text,
            "old_position": self.old_position,
            "new_position": self.new_position,
            "similarity_score": self.similarity_score,
        }


@dataclass
class ComparisonResult:
    """İki metin arasındaki karşılaştırma sonucunu temsil eder."""

    old_file_name: str
    new_file_name: str
    changes: list[TextChange]

    @property
    def added_count(self) -> int:
        return sum(
            change.change_type == ChangeType.ADDED
            for change in self.changes
        )

    @property
    def removed_count(self) -> int:
        return sum(
            change.change_type == ChangeType.REMOVED
            for change in self.changes
        )

    @property
    def modified_count(self) -> int:
        return sum(
            change.change_type == ChangeType.MODIFIED
            for change in self.changes
        )

    @property
    def unchanged_count(self) -> int:
        return sum(
            change.change_type == ChangeType.UNCHANGED
            for change in self.changes
        )

    @property
    def total_change_count(self) -> int:
        return self.added_count + self.removed_count + self.modified_count

    def summary(self) -> dict[str, int | str]:
        """Karşılaştırma sonucunun özetini döndürür."""

        return {
            "old_file_name": self.old_file_name,
            "new_file_name": self.new_file_name,
            "added": self.added_count,
            "removed": self.removed_count,
            "modified": self.modified_count,
            "unchanged": self.unchanged_count,
            "total_changes": self.total_change_count,
        }


def split_into_paragraphs(text: str) -> list[str]:
    """Metni boş olmayan satır veya paragraflara ayırır."""

    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


def calculate_similarity(old_text: str, new_text: str) -> float:
    """İki metin arasındaki karakter tabanlı benzerliği hesaplar."""

    return SequenceMatcher(
        None,
        old_text.casefold(),
        new_text.casefold(),
        autojunk=False,
    ).ratio()


def compare_texts(
    old_text: str,
    new_text: str,
    old_file_name: str = "old_document",
    new_file_name: str = "new_document",
    similarity_threshold: float = 0.45,
) -> ComparisonResult:
    """İki metni paragraf bazında karşılaştırır.

    Args:
        old_text: Dokümanın eski sürümünün metni.
        new_text: Dokümanın yeni sürümünün metni.
        old_file_name: Eski dokümanın dosya adı.
        new_file_name: Yeni dokümanın dosya adı.
        similarity_threshold: İki paragrafın değiştirilmiş kabul edilmesi
            için gereken minimum benzerlik oranı.

    Returns:
        Karşılaştırma sonucu.
    """

    if not 0.0 <= similarity_threshold <= 1.0:
        raise ValueError(
            "similarity_threshold değeri 0.0 ile 1.0 arasında olmalıdır."
        )

    old_paragraphs = split_into_paragraphs(old_text)
    new_paragraphs = split_into_paragraphs(new_text)

    matcher = SequenceMatcher(
        None,
        old_paragraphs,
        new_paragraphs,
        autojunk=False,
    )

    changes: list[TextChange] = []

    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag == "equal":
            for offset, paragraph in enumerate(
                old_paragraphs[old_start:old_end]
            ):
                changes.append(
                    TextChange(
                        change_type=ChangeType.UNCHANGED,
                        old_text=paragraph,
                        new_text=paragraph,
                        old_position=old_start + offset,
                        new_position=new_start + offset,
                        similarity_score=1.0,
                    )
                )

        elif tag == "delete":
            for offset, paragraph in enumerate(
                old_paragraphs[old_start:old_end]
            ):
                changes.append(
                    TextChange(
                        change_type=ChangeType.REMOVED,
                        old_text=paragraph,
                        old_position=old_start + offset,
                    )
                )

        elif tag == "insert":
            for offset, paragraph in enumerate(
                new_paragraphs[new_start:new_end]
            ):
                changes.append(
                    TextChange(
                        change_type=ChangeType.ADDED,
                        new_text=paragraph,
                        new_position=new_start + offset,
                    )
                )

        elif tag == "replace":
            old_group = old_paragraphs[old_start:old_end]
            new_group = new_paragraphs[new_start:new_end]

            matched_old_indexes: set[int] = set()
            matched_new_indexes: set[int] = set()

            candidate_matches: list[tuple[float, int, int]] = []

            for old_offset, old_paragraph in enumerate(old_group):
                for new_offset, new_paragraph in enumerate(new_group):
                    similarity = calculate_similarity(
                        old_paragraph,
                        new_paragraph,
                    )

                    if similarity >= similarity_threshold:
                        candidate_matches.append(
                            (
                                similarity,
                                old_offset,
                                new_offset,
                            )
                        )

            candidate_matches.sort(
                key=lambda candidate: candidate[0],
                reverse=True,
            )

            for similarity, old_offset, new_offset in candidate_matches:
                if old_offset in matched_old_indexes:
                    continue

                if new_offset in matched_new_indexes:
                    continue

                matched_old_indexes.add(old_offset)
                matched_new_indexes.add(new_offset)

                changes.append(
                    TextChange(
                        change_type=ChangeType.MODIFIED,
                        old_text=old_group[old_offset],
                        new_text=new_group[new_offset],
                        old_position=old_start + old_offset,
                        new_position=new_start + new_offset,
                        similarity_score=round(similarity, 4),
                    )
                )

            for old_offset, old_paragraph in enumerate(old_group):
                if old_offset not in matched_old_indexes:
                    changes.append(
                        TextChange(
                            change_type=ChangeType.REMOVED,
                            old_text=old_paragraph,
                            old_position=old_start + old_offset,
                        )
                    )

            for new_offset, new_paragraph in enumerate(new_group):
                if new_offset not in matched_new_indexes:
                    changes.append(
                        TextChange(
                            change_type=ChangeType.ADDED,
                            new_text=new_paragraph,
                            new_position=new_start + new_offset,
                        )
                    )

    changes.sort(
        key=lambda change: (
            change.new_position
            if change.new_position is not None
            else float("inf"),
            change.old_position
            if change.old_position is not None
            else float("inf"),
        )
    )

    return ComparisonResult(
        old_file_name=old_file_name,
        new_file_name=new_file_name,
        changes=changes,
    )


def compare_documents(
    old_document: Any,
    new_document: Any,
    similarity_threshold: float = 0.45,
) -> ComparisonResult:
    """Yüklenmiş iki dokümanı karşılaştırır."""

    return compare_texts(
        old_text=old_document.text,
        new_text=new_document.text,
        old_file_name=old_document.file_name,
        new_file_name=new_document.file_name,
        similarity_threshold=similarity_threshold,
    )