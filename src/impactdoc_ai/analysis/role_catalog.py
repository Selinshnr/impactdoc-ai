"""Doküman ve değişiklik içeriğine göre dinamik rol havuzu üretir."""
from __future__ import annotations
from dataclasses import dataclass
from impactdoc_ai.analysis.change_category import ChangeClassification
from impactdoc_ai.comparison import TextChange

@dataclass(frozen=True)
class RoleDefinition:
    name: str
    keywords: tuple[str, ...]
    categories: tuple[str, ...]

ROLE_DEFINITIONS = (
    RoleDefinition("İnsan Kaynakları Uzmanı", ("insan kaynakları", "insan kaynakları birimi", "personel dosyası", "personel sistemi", "izin kaydı", "sözleşme", "uzaktan çalışma talebi"), ("personel_yonetimi", "genel")),
    RoleDefinition("Birim Yöneticisi", ("birim yöneticisi", "birim yöneticileri", "yönetici", "iş sürekliliği", "görevlendirme", "planlama"), ("personel_yonetimi", "is_sureci", "genel")),
    RoleDefinition("Çalışan", ("çalışan", "kurum çalışanları", "izin talebi", "uzaktan çalışma talebi", "işten ayrılan personel", "zimmetli cihaz", "çalışma düzeni"), ("personel_yonetimi", "genel")),
    RoleDefinition("Personel Yöneticisi", ("personel yöneticisi", "personel yönetimi", "personel planlaması", "personel hareketi", "kadro"), ("personel_yonetimi",)),
    RoleDefinition("Doküman Yöneticisi", ("sürüm", "revizyon", "yürürlük tarihi", "doküman", "prosedür", "kapsam", "başlık"), ("personel_yonetimi", "bilgi_guvenligi", "bilgi_teknolojileri", "is_sureci", "genel")),
    RoleDefinition("Bilgi İşlem Uzmanı", ("bilgi işlem", "bilgi işlem birimi", "kullanıcı hesabı", "hesap açılması", "hesap kapatılması", "vpn", "erişim tanımlama", "erişim tanımlar", "devre dışı", "yetki tanımlama"), ("bilgi_teknolojileri", "bilgi_guvenligi", "personel_yonetimi")),
    RoleDefinition("Bilgi Güvenliği Uzmanı", ("bilgi güvenliği", "bilgi güvenliği birimi", "güvenlik onayı", "kritik sistem", "çok faktörlü", "kimlik doğrulama", "yetkilendirme", "erişim kontrolü", "erişim rol", "erişim roller", "kullanıcı erişim", "uzaktan erişim", "açık oturum", "veri ihlali", "kişisel veri"), ("bilgi_guvenligi", "bilgi_teknolojileri", "personel_yonetimi")),
)

DOCUMENT_CATEGORY_KEYWORDS = {
    "personel_yonetimi": ("personel", "insan kaynakları", "işe alım", "işe başlatma", "işten ayrılma", "izin", "özlük", "uzaktan çalışma"),
    "bilgi_guvenligi": ("bilgi güvenliği", "erişim güvenliği", "kimlik doğrulama", "yetkilendirme", "veri güvenliği", "kritik sistem"),
    "bilgi_teknolojileri": ("bilgi işlem", "yazılım", "uygulama", "sistem", "sunucu", "vpn", "kullanıcı hesabı"),
    "is_sureci": ("iş süreci", "iş akışı", "onay süreci", "sorumluluk", "prosedür", "faaliyet"),
}

DEFAULT_ROLES_BY_CATEGORY = {
    "personel_yonetimi": ("İnsan Kaynakları Uzmanı", "Birim Yöneticisi", "Çalışan", "Doküman Yöneticisi"),
    "bilgi_guvenligi": ("Bilgi Güvenliği Uzmanı", "Bilgi İşlem Uzmanı", "Birim Yöneticisi", "Doküman Yöneticisi"),
    "bilgi_teknolojileri": ("Bilgi İşlem Uzmanı", "Bilgi Güvenliği Uzmanı", "Birim Yöneticisi", "Doküman Yöneticisi"),
    "is_sureci": ("Birim Yöneticisi", "Çalışan", "Doküman Yöneticisi"),
    "genel": ("Birim Yöneticisi", "Çalışan", "Doküman Yöneticisi"),
}

TECHNICAL_TRIGGER_KEYWORDS = ("bilgi işlem", "kullanıcı hesabı", "hesap açılması", "hesap kapatılması", "vpn", "erişim", "yetki", "kimlik doğrulama", "çok faktörlü", "güvenlik", "kritik sistem", "açık oturum", "devre dışı", "kişisel veri")

def normalize_text(value: str | None) -> str:
    if value is None:
        return ""

    normalized = value.translate(
        str.maketrans(
            {
                "İ": "i",
                "I": "ı",
            }
        )
    ).lower()

    return " ".join(normalized.split())

def combine_change_text(change: TextChange) -> str:
    return " ".join(v for v in (normalize_text(change.old_text), normalize_text(change.new_text)) if v)

def detect_document_category(old_file_name: str, new_file_name: str, document_text: str = "") -> str:
    searchable_text = normalize_text(f"{old_file_name} {new_file_name} {document_text}")
    scores = {category: sum(k in searchable_text for k in keywords) for category, keywords in DOCUMENT_CATEGORY_KEYWORDS.items()}
    best = max(scores, key=scores.get, default="genel")
    return best if scores.get(best, 0) else "genel"

def get_role_pool(change: TextChange, document_category: str, classification: ChangeClassification | None = None, max_roles: int = 6) -> list[str]:
    change_text = combine_change_text(change)
    defaults = list(DEFAULT_ROLES_BY_CATEGORY.get(document_category, DEFAULT_ROLES_BY_CATEGORY["genel"]))
    matched = []
    for rd in ROLE_DEFINITIONS:
        if (document_category in rd.categories or "genel" in rd.categories) and any(k in change_text for k in rd.keywords):
            matched.append(rd.name)
    technical = any(k in change_text for k in TECHNICAL_TRIGGER_KEYWORDS)
    if not technical:
        tech_roles = {"Bilgi İşlem Uzmanı", "Bilgi Güvenliği Uzmanı"}
        defaults = [r for r in defaults if r not in tech_roles]
        matched = [r for r in matched if r not in tech_roles]
    pool = []
    for role in matched + defaults:
        if role not in pool:
            pool.append(role)
    return pool[:max_roles]

def get_all_role_names() -> list[str]:
    return [rd.name for rd in ROLE_DEFINITIONS]