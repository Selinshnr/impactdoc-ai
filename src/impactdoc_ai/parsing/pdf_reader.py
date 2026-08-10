"""PDF dokümanlarını okuma işlemleri."""

from pathlib import Path

from pypdf import PdfReader

from impactdoc_ai.models.document import Document
from impactdoc_ai.utils.hashing import calculate_sha256


def read_pdf(file_path: str | Path) -> Document:
    """
    Bir PDF dosyasını okuyarak standart Document nesnesine dönüştürür.

    Args:
        file_path: Okunacak PDF dosyasının yolu.

    Returns:
        Okunan dokümanı temsil eden Document nesnesi.

    Raises:
        FileNotFoundError: Dosya bulunamazsa.
        ValueError: Dosya uzantısı PDF değilse veya metin çıkarılamazsa.
    """
    path = Path(file_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Dosya bulunamadı: {path}")

    if not path.is_file():
        raise ValueError(f"Verilen yol bir dosya değil: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            f"Desteklenmeyen dosya uzantısı: {path.suffix}. "
            "Bu okuyucu yalnızca PDF dosyalarını destekler."
        )

    reader = PdfReader(path)

    page_texts: list[str] = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""

        if page_text.strip():
            page_texts.append(page_text.strip())
        else:
            page_texts.append(
                f"[Sayfa {page_number}: Metin çıkarılamadı]"
            )

    text = "\n\n".join(page_texts).strip()

    if not text:
        raise ValueError(
            "PDF dosyasından metin çıkarılamadı. "
            "Dosya taranmış görüntülerden oluşuyor olabilir."
        )

    return Document(
        file_path=path,
        file_name=path.name,
        extension=path.suffix.lower(),
        text=text,
        page_count=len(reader.pages),
        character_count=len(text),
        word_count=len(text.split()),
        sha256=calculate_sha256(path),
    )