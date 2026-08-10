"""Doküman değişiklikleri için kategori veri modeli.

Bu modül, LLM tarafından üretilen değişiklik kategorilerinin
standart ve doğrulanabilir bir yapıda tutulmasını sağlar.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ChangeCategory(str, Enum):
    """Desteklenen değişiklik kategorileri.

    Enum değerlerinde İngilizce ve makine-dostu ifadeler kullanılır.
    Kullanıcıya gösterilen Türkçe karşılıklar `label` özelliğinden alınır.
    """

    TASK = "task_change"
    PROCESS = "process_change"
    AUTHORITY = "authority_change"
    DEFINITION = "definition_change"
    TECHNICAL = "technical_change"
    LEGISLATION = "legislation_change"
    OTHER = "other"

    @property
    def label(self) -> str:
        """Kategorinin kullanıcıya gösterilecek Türkçe adını döndürür."""

        labels = {
            ChangeCategory.TASK: "Görev değişikliği",
            ChangeCategory.PROCESS: "Süreç değişikliği",
            ChangeCategory.AUTHORITY: "Yetki değişikliği",
            ChangeCategory.DEFINITION: "Tanım değişikliği",
            ChangeCategory.TECHNICAL: "Teknik değişiklik",
            ChangeCategory.LEGISLATION: "Mevzuat değişikliği",
            ChangeCategory.OTHER: "Diğer",
        }

        return labels[self]

    @property
    def description(self) -> str:
        """Kategorinin sınıflandırma sırasında kullanılacak açıklamasını döndürür."""

        descriptions = {
            ChangeCategory.TASK: (
                "Bir rolün yapacağı işin, sorumluluğun veya görevin "
                "eklenmesi, kaldırılması ya da değiştirilmesi."
            ),
            ChangeCategory.PROCESS: (
                "Bir işin hangi adımlarla, hangi sırayla, hangi araçla "
                "veya hangi yöntemle yürütüleceğinin değiştirilmesi."
            ),
            ChangeCategory.AUTHORITY: (
                "Onay, karar, erişim, imza, kontrol veya sorumluluk "
                "yetkisinin değiştirilmesi."
            ),
            ChangeCategory.DEFINITION: (
                "Bir kavramın, terimin, rolün veya kapsamın "
                "tanımının değiştirilmesi."
            ),
            ChangeCategory.TECHNICAL: (
                "Yazılım, sistem, altyapı, güvenlik, entegrasyon, "
                "teknik standart veya teknolojik gereksinim değişikliği."
            ),
            ChangeCategory.LEGISLATION: (
                "Kanun, yönetmelik, genelge, mevzuat hükmü veya "
                "uyum yükümlülüğünden kaynaklanan değişiklik."
            ),
            ChangeCategory.OTHER: (
                "Desteklenen ana kategorilerden hiçbirine açık biçimde "
                "girmeyen değişiklik."
            ),
        }

        return descriptions[self]


@dataclass(frozen=True)
class ChangeClassification:
    """Bir doküman değişikliğinin sınıflandırma sonucunu temsil eder."""

    category: ChangeCategory
    confidence: float
    reason: str
    source: str = "ollama"

    def __post_init__(self) -> None:
        """Sınıflandırma sonucunun temel alanlarını doğrular."""

        if self.source not in {"rule", "ollama", "manual"}:
            raise ValueError(
                "source yalnızca rule, ollama veya manual olabilir."
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "confidence değeri 0.0 ile 1.0 arasında olmalıdır."
            )

        if not self.reason.strip():
            raise ValueError("Sınıflandırma gerekçesi boş olamaz.")

    def to_dict(self) -> dict[str, Any]:
        """Nesneyi JSON uyumlu sözlüğe dönüştürür."""

        return {
            "category": self.category.value,
            "category_label": self.category.label,
            "confidence": self.confidence,
            "reason": self.reason,
            "source": self.source,
        }


_CATEGORY_ALIASES: dict[str, ChangeCategory] = {
    # Makine değerleri
    "task_change": ChangeCategory.TASK,
    "process_change": ChangeCategory.PROCESS,
    "authority_change": ChangeCategory.AUTHORITY,
    "definition_change": ChangeCategory.DEFINITION,
    "technical_change": ChangeCategory.TECHNICAL,
    "legislation_change": ChangeCategory.LEGISLATION,
    "other": ChangeCategory.OTHER,

    # Türkçe ifadeler
    "görev değişikliği": ChangeCategory.TASK,
    "gorev degisikligi": ChangeCategory.TASK,
    "süreç değişikliği": ChangeCategory.PROCESS,
    "surec degisikligi": ChangeCategory.PROCESS,
    "yetki değişikliği": ChangeCategory.AUTHORITY,
    "yetki degisikligi": ChangeCategory.AUTHORITY,
    "tanım değişikliği": ChangeCategory.DEFINITION,
    "tanim degisikligi": ChangeCategory.DEFINITION,
    "teknik değişiklik": ChangeCategory.TECHNICAL,
    "teknik degisiklik": ChangeCategory.TECHNICAL,
    "mevzuat değişikliği": ChangeCategory.LEGISLATION,
    "mevzuat degisikligi": ChangeCategory.LEGISLATION,
    "diğer": ChangeCategory.OTHER,
    "diger": ChangeCategory.OTHER,

    # LLM'in kullanabileceği kısa ifadeler
    "görev": ChangeCategory.TASK,
    "gorev": ChangeCategory.TASK,
    "süreç": ChangeCategory.PROCESS,
    "surec": ChangeCategory.PROCESS,
    "yetki": ChangeCategory.AUTHORITY,
    "tanım": ChangeCategory.DEFINITION,
    "tanim": ChangeCategory.DEFINITION,
    "teknik": ChangeCategory.TECHNICAL,
    "mevzuat": ChangeCategory.LEGISLATION,
}


def parse_change_category(value: str) -> ChangeCategory:
    """Metin olarak gelen kategori değerini doğrulanmış Enum'a dönüştürür.

    Args:
        value: LLM veya başka bir kaynaktan gelen kategori metni.

    Returns:
        Doğrulanmış ChangeCategory değeri.

    Raises:
        TypeError: Değer metin değilse.
        ValueError: Değer desteklenen kategorilerden biri değilse.
    """

    if not isinstance(value, str):
        raise TypeError("Kategori değeri metin olmalıdır.")

    normalized_value = value.strip().lower()

    category = _CATEGORY_ALIASES.get(normalized_value)

    if category is None:
        supported_values = ", ".join(
            category.value for category in ChangeCategory
        )

        raise ValueError(
            f"Geçersiz değişiklik kategorisi: {value!r}. "
            f"Desteklenen değerler: {supported_values}"
        )

    return category


def get_category_catalog() -> list[dict[str, str]]:
    """Prompt ve arayüzlerde kullanılabilecek kategori kataloğunu döndürür."""

    return [
        {
            "value": category.value,
            "label": category.label,
            "description": category.description,
        }
        for category in ChangeCategory
    ]