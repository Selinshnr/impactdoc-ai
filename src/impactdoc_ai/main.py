"""ImpactDoc AI komut satırı uygulaması."""

import argparse
import sys
from pathlib import Path

from impactdoc_ai.ingestion import load_document
from impactdoc_ai.models import Document


def create_parser() -> argparse.ArgumentParser:
    """Komut satırı argümanlarını tanımlar."""
    parser = argparse.ArgumentParser(
        prog="impactdoc",
        description=(
            "Dokümanları okuyarak metadata üreten ve değişiklik "
            "etki analizine hazırlayan komut satırı uygulaması."
        ),
    )

    parser.add_argument(
        "file_path",
        nargs="?",
        type=Path,
        help="Okunacak dokümanın dosya yolu.",
    )

    return parser


def print_document_summary(document: Document) -> None:
    """Doküman özetini terminale yazdırır."""
    print()
    print("=" * 60)
    print("IMPACTDOC AI — DOKÜMAN ÖZETİ")
    print("=" * 60)
    print(f"Dosya adı       : {document.file_name}")
    print(f"Dosya yolu      : {document.file_path}")
    print(f"Dosya türü      : {document.extension}")
    print(f"Sayfa sayısı    : {document.page_count}")
    print(f"Karakter sayısı : {document.character_count}")
    print(f"Kelime sayısı   : {document.word_count}")
    print(f"SHA-256         : {document.sha256}")
    print("=" * 60)


def main() -> None:
    """Uygulamanın başlangıç noktası."""
    parser = create_parser()
    args = parser.parse_args()

    if args.file_path is None:
        parser.print_help()
        return

    try:
        document = load_document(args.file_path)
        print_document_summary(document)
    except (FileNotFoundError, ValueError, UnicodeError) as error:
        print(f"Hata: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()