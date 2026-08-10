"""ImpactDoc AI komut satırı uygulaması."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from impactdoc_ai.analysis import analyze_role_impacts_with_llm
from impactdoc_ai.comparison import compare_documents
from impactdoc_ai.ingestion import load_document
from impactdoc_ai.models import Document
from impactdoc_ai.reporting import save_llm_analysis_report


def create_parser() -> argparse.ArgumentParser:
    """Komut satırı argümanlarını tanımlar."""

    parser = argparse.ArgumentParser(
        prog="impactdoc",
        description=(
            "Kurumsal dokümanları okuyan, sürümleri karşılaştıran "
            "ve rol bazlı değişiklik etki analizi yapan uygulama."
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Tek bir dokümanın metadata özetini gösterir.",
    )

    inspect_parser.add_argument(
        "file_path",
        type=Path,
        help="Okunacak dokümanın dosya yolu.",
    )

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="İki doküman sürümünü karşılaştırır ve etki analizi yapar.",
    )

    analyze_parser.add_argument(
        "old_file",
        type=Path,
        help="Eski doküman sürümünün yolu.",
    )

    analyze_parser.add_argument(
        "new_file",
        type=Path,
        help="Yeni doküman sürümünün yolu.",
    )

    analyze_parser.add_argument(
        "--model",
        default="qwen3:4b",
        help="Ollama model adı. Varsayılan: qwen3:4b",
    )

    analyze_parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reports/impact_analysis.json"),
        help="JSON raporunun kaydedileceği yol.",
    )

    analyze_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Analiz edilecek maksimum değişiklik sayısı.",
    )

    analyze_parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="LLM istek zaman aşımı. Varsayılan: 600 saniye.",
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


def run_inspect(file_path: Path) -> None:
    """Tek dokümanın metadata özetini gösterir."""

    document = load_document(file_path)
    print_document_summary(document)


def run_analysis(
    old_file: Path,
    new_file: Path,
    model: str,
    output: Path,
    limit: int | None,
    timeout: int,
) -> None:
    """İki doküman sürümü için rol bazlı etki analizi çalıştırır."""

    old_document = load_document(old_file)
    new_document = load_document(new_file)

    comparison = compare_documents(
        old_document,
        new_document,
    )

    analysis = analyze_role_impacts_with_llm(
        comparison,
        model_name=model,
        limit=limit,
        timeout=timeout,
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = save_llm_analysis_report(
        analysis,
        output,
    )

    summary = analysis.summary()

    print()
    print("=" * 70)
    print("IMPACTDOC AI — ANALİZ TAMAMLANDI")
    print("=" * 70)
    print(json.dumps(
        summary,
        ensure_ascii=False,
        indent=2,
    ))
    print()
    print(f"Rapor: {report_path}")
    print("=" * 70)


def main() -> None:
    """Uygulamanın başlangıç noktası."""

    parser = create_parser()
    args = parser.parse_args()

    try:
        if args.command == "inspect":
            run_inspect(args.file_path)
            return

        if args.command == "analyze":
            run_analysis(
                old_file=args.old_file,
                new_file=args.new_file,
                model=args.model,
                output=args.output,
                limit=args.limit,
                timeout=args.timeout,
            )
            return

        parser.error(
            f"Desteklenmeyen komut: {args.command}"
        )

    except (
        FileNotFoundError,
        ValueError,
        UnicodeError,
        ConnectionError,
        TimeoutError,
    ) as error:
        print(
            f"Hata: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()