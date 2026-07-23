from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Document:
    """
    Sistemdeki standart doküman modeli.
    """

    file_path: Path

    file_name: str

    extension: str

    text: str

    page_count: int

    character_count: int

    word_count: int

    sha256: str