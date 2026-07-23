"""Dosya türüne göre uygun doküman okuyucuyu seçer."""

from pathlib import Path

from impactdoc_ai.models.document import Document
from impactdoc_ai.parsing.txt_reader import read_txt


SUPPORTED_EXTENSIONS = {".txt"}


def load_document(file_path: str | Path) -> Document:
    """
    Dosya uzantısına göre uygun okuyucuyu çağırır.

    Args:
        file_path: Okunacak dokümanın yolu.

    Returns:
        Standart Document nesnesi.

    Raises:
        FileNotFoundError: Dosya bulunamazsa.
        ValueError: Dosya uzantısı desteklenmiyorsa.
    """
    path = Path(file_path).resolve()
    extension = path.suffix.lower()

    if extension == ".txt":
        return read_txt(path)

    supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))

    raise ValueError(
        f"Desteklenmeyen dosya türü: '{extension or 'uzantı yok'}'. "
        f"Desteklenen uzantılar: {supported}"
    )