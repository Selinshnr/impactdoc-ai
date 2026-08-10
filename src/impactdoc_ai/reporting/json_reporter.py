"""Karşılaştırma sonuçlarını JSON raporuna dönüştürür."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from impactdoc_ai.comparison import ComparisonResult


def comparison_result_to_dict(
    result: ComparisonResult,
    include_unchanged: bool = False,
) -> dict[str, Any]:
    """Karşılaştırma sonucunu JSON uyumlu sözlüğe dönüştürür."""

    changes = []

    for change in result.changes:
        if not include_unchanged and change.change_type.value == "unchanged":
            continue

        changes.append(change.to_dict())

    return {
        "report_metadata": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "report_type": "document_comparison",
        },
        "documents": {
            "old_file_name": result.old_file_name,
            "new_file_name": result.new_file_name,
        },
        "summary": result.summary(),
        "changes": changes,
    }


def save_comparison_report(
    result: ComparisonResult,
    output_path: str | Path,
    include_unchanged: bool = False,
) -> Path:
    """Karşılaştırma sonucunu JSON dosyasına kaydeder."""

    destination = Path(output_path)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_data = comparison_result_to_dict(
        result=result,
        include_unchanged=include_unchanged,
    )

    destination.write_text(
        json.dumps(
            report_data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return destination