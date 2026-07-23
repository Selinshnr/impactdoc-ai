"""TXT dokümanlarını okuma işlemleri."""

from pathlib import Path

from impactdoc_ai.models.document import Document
from impactdoc_ai.utils.hashing import calculate_sha256


def read_txt(file_path: str | Path) -> Document:
    """
    Bir TXT dosyasını okuyarak standart Document nesnesine dönüştürür.

    Args:
        file_path: Okunacak TXT dosyasının yolu.

    Returns:
        Okunan dokümanı temsil eden Document nesnesi.

    Raises:
        FileNotFoundError: Dosya bulunamazsa.
        ValueError: Dosyanın uzantısı TXT değilse.
        UnicodeError: Dosya desteklenen kodlamalarla okunamazsa.
    """
    path = Path(file_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Dosya bulunamadı: {path}")

    if not path.is_file():
        raise ValueError(f"Verilen yol bir dosya değil: {path}")

    if path.suffix.lower() != ".txt":
        raise ValueError(
            f"Desteklenmeyen dosya uzantısı: {path.suffix}. "
            "Bu okuyucu yalnızca TXT dosyalarını destekler."
        )

    text = _read_text_with_fallback(path)

    return Document(
        file_path=path,
        file_name=path.name,
        extension=path.suffix.lower(),
        text=text,
        page_count=1,
        character_count=len(text),
        word_count=len(text.split()),
        sha256=calculate_sha256(path),
    )


def _read_text_with_fallback(path: Path) -> str:
    """
    TXT dosyasını yaygın kodlamalarla okumayı dener.

    Türkçe Windows ortamlarında UTF-8 dışında CP1254 kodlamasıyla
    kaydedilmiş metin dosyaları bulunabileceği için alternatif
    kodlamalar sırayla denenir.
    """
    encodings = ("utf-8", "utf-8-sig", "cp1254")

    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue

    raise UnicodeError(
        f"Dosya desteklenen kodlamalarla okunamadı: {path}"
    )