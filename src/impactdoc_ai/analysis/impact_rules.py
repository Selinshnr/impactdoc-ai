"""Etki seviyesi hesaplamasında kullanılan merkezi kurallar."""
from __future__ import annotations
from impactdoc_ai.analysis.change_category import ChangeCategory

HIGH_IMPACT_KEYWORDS: tuple[str, ...] = (
    "çok faktörlü", "mfa", "kimlik doğrulama", "erişim yetkisi",
    "erişim hakkı", "uzaktan erişim", "vpn", "hesap kapatma",
    "hesabın kapatılması", "devre dışı", "güvenlik onayı",
    "kritik sistem", "kritik erişim", "yetki kaldırma",
    "yetkinin kaldırılması", "işten ayrılış saatinde",
    "veri ihlali", "kişisel veri",
)

MEDIUM_IMPACT_KEYWORDS: tuple[str, ...] = (
    "kullanıcı hesabı", "uzaktan çalışma", "izin talebi", "portal",
    "onay", "iş günü", "iş akışı", "iş sürekliliği", "zimmetli cihaz",
    "personel dosyası", "personel sistemi", "sorumluluk",
    "görevlendirme", "değerlendirme",
)

LOW_IMPACT_KEYWORDS: tuple[str, ...] = (
    "sürüm", "versiyon", "yürürlük tarihi", "yayın tarihi",
    "dokümanın amacı", "doküman amacı", "kapsar", "başlık",
    "yazım", "imla",
)

CATEGORY_MINIMUM_LEVEL_VALUE: dict[ChangeCategory, str] = {
    ChangeCategory.TASK: "medium",
    ChangeCategory.PROCESS: "medium",
    ChangeCategory.AUTHORITY: "medium",
    ChangeCategory.DEFINITION: "low",
    ChangeCategory.TECHNICAL: "medium",
    ChangeCategory.LEGISLATION: "medium",
    ChangeCategory.OTHER: "low",
}