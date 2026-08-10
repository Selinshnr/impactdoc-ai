"""LLM tabanlı etki analizi sonuçlarını JSON raporuna kaydeder."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from impactdoc_ai.analysis import LLMImpactAnalysisResult


def llm_analysis_result_to_dict(
    result: LLMImpactAnalysisResult,
) -> dict[str, Any]:
    """LLM analiz sonucunu JSON uyumlu sözlüğe dönüştürür."""

    return {
        "report_metadata": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "report_type": "llm_role_impact_analysis",
            "model_name": result.model_name,
        },
        "documents": {
            "old_file_name": result.old_file_name,
            "new_file_name": result.new_file_name,
        },
        "summary": result.summary(),
        "impacts": [
            impact.to_dict()
            for impact in result.impacts
        ],
    }


def save_llm_analysis_report(
    result: LLMImpactAnalysisResult,
    output_path: str | Path,
) -> Path:
    """LLM analiz sonucunu JSON dosyasına kaydeder."""

    destination = Path(output_path)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_data = llm_analysis_result_to_dict(result)

    destination.write_text(
        json.dumps(
            report_data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return destination