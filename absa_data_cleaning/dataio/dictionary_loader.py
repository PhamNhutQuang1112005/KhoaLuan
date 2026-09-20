"""
dataio/dictionary_loader.py
==============================
Đọc từ điển teencode/viết tắt + danh sách từ nghi vấn từ thư mục dictionary/
— tách riêng I/O đọc file khỏi transforms/utils_text.py (vốn chỉ chứa hàm
THUẦN không I/O, xem docstring module đó).

Định dạng dictionary/teencode_abbreviation.txt: file TSV có HEADER (dòng 1 cố
định "Teencode\tChuan\tContext_Keywords\tFlag"), mỗi dòng sau đó là 1 ỨNG VIÊN
nghĩa cho 1 teencode/viết tắt:
  - Teencode: khoá (không phân biệt hoa/thường khi tra cứu).
  - Chuan: dạng chuẩn để thay thế.
  - Context_Keywords: '1' nếu Teencode CHỈ có đúng 1 nghĩa (không cần xét ngữ
    cảnh) — HOẶC danh sách từ khoá ngữ cảnh cách nhau bởi dấu phẩy, dùng để
    NHẬN DIỆN nghĩa này khi Teencode có NHIỀU ứng viên (nhiều dòng cùng
    Teencode, vd 'nc' có 2 dòng: 'nước' và 'nói chung' — xem
    transforms.utils_text.normalize_teencode_text).
  - Flag: 'safe' (1 nghĩa duy nhất, luôn thay thế) hoặc 'ambiguous' (nhiều
    ứng viên, CHỈ thay thế khi đúng 1 ứng viên khớp từ khoá ngữ cảnh quanh vị
    trí xuất hiện — nếu 0 hoặc >=2 ứng viên khớp, GIỮ NGUYÊN từ gốc, không
    đoán, coi như chưa xử lý được).

Định dạng dictionary/suspect_teencode_terms.txt: mỗi dòng 1 từ/cụm từ nghi
vấn KHÔNG hề có trong teencode_abbreviation.txt (chưa rõ nghĩa gì cả — khác
với khoá ĐA NGHĨA đã biết các ứng viên, vốn khai báo NGAY trong
teencode_abbreviation.txt bằng nhiều dòng + Context_Keywords, xem ở trên) —
dùng để TÁCH RIÊNG review chứa từ này ra Suspect_Teencode_Abbreviation.xlsx
cho con người rà soát thủ công (xem
transforms.tang2_content_quality.split_suspect_teencode_reviews). File này CÓ
THỂ không tồn tại (chưa từ nào nghi vấn).

Định dạng dictionary/spelling_errors.txt (T2.19): TSV có HEADER (dòng 1 bỏ
qua), mỗi dòng "từ sai<TAB>từ đúng" — từ điển sửa lỗi chính tả thường gặp
trong review TMĐT, ưu tiên cao hơn bộ kiểm tra âm tiết tự động (xem
transforms.utils_text.correct_spelling_text). CHỈ thêm cặp CHẮC CHẮN đúng ở
mọi ngữ cảnh (vd 'ngừoi' -> 'người'; KHÔNG thêm 'thí' -> 'thì' vì 'thí
nghiệm' cũng đúng).

Định dạng dictionary/spelling_whitelist.txt (T2.19): HEADER + mỗi dòng 1 từ
ngoại lai/thương hiệu/tên riêng (đã lowercase) KHÔNG được coi là sai chính tả
dù không phải âm tiết tiếng Việt, và không bị "sửa" nhầm (vd 'box' bị đoán
thành 'bõ' do trông giống lỗi gõ Telex).
"""

from functools import lru_cache

from config.settings import DICTIONARY_DIR

TEENCODE_DICT_PATH = DICTIONARY_DIR / "teencode_abbreviation.txt"
SUSPECT_TEENCODE_TERMS_PATH = DICTIONARY_DIR / "suspect_teencode_terms.txt"
SPELLING_ERRORS_PATH = DICTIONARY_DIR / "spelling_errors.txt"
SPELLING_WHITELIST_PATH = DICTIONARY_DIR / "spelling_whitelist.txt"


@lru_cache(maxsize=1)
def load_teencode_dict() -> dict:
    """Đọc TEENCODE_DICT_PATH -> dict {teencode/viết tắt (đã lowercase): [ứng
    viên, ...]}. Mỗi ứng viên là dict {"value": dạng chuẩn, "context_keywords":
    list từ khoá đã lowercase (None nếu Context_Keywords == '1', tức không
    cần xét ngữ cảnh), "flag": 'safe'/'ambiguous'} — xem docstring module để
    biết định dạng file + cách `normalize_teencode_text` dùng cấu trúc này.

    Bỏ qua dòng 1 (header) + dòng trống/thiếu cột. Cache bằng lru_cache vì
    file không đổi trong 1 lần chạy chương trình, và hàm này được gọi lại cho
    MỖI sản phẩm trong PRODUCT_FILES.
    """
    result: dict = {}
    with open(TEENCODE_DICT_PATH, encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines[1:]:
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 4:
            continue
        key, value, context_raw, flag = (p.strip() for p in parts[:4])
        if not key or not value:
            continue
        context_keywords = (
            None if context_raw == "1" or not context_raw
            else [kw.strip().lower() for kw in context_raw.split(",") if kw.strip()]
        )
        result.setdefault(key.lower(), []).append(
            {"value": value, "context_keywords": context_keywords, "flag": flag.lower()}
        )
    return result


@lru_cache(maxsize=1)
def load_suspect_teencode_terms() -> frozenset:
    """Đọc SUSPECT_TEENCODE_TERMS_PATH -> frozenset các từ/cụm từ nghi vấn
    (đã lowercase). Trả về frozenset rỗng nếu file chưa tồn tại."""
    if not SUSPECT_TEENCODE_TERMS_PATH.exists():
        return frozenset()
    terms = set()
    with open(SUSPECT_TEENCODE_TERMS_PATH, encoding="utf-8") as f:
        for line in f:
            term = line.strip().lower()
            if term:
                terms.add(term)
    return frozenset(terms)


@lru_cache(maxsize=1)
def load_spelling_errors_dict() -> dict:
    """Đọc SPELLING_ERRORS_PATH -> {từ sai (lowercase): từ đúng}. Trả về dict
    rỗng nếu file chưa tồn tại."""
    if not SPELLING_ERRORS_PATH.exists():
        return {}
    result = {}
    with open(SPELLING_ERRORS_PATH, encoding="utf-8") as f:
        for line in f.readlines()[1:]:
            parts = [p.strip() for p in line.split("\t")]
            if len(parts) >= 2 and parts[0] and parts[1]:
                result[parts[0].lower()] = parts[1]
    return result


@lru_cache(maxsize=1)
def load_spelling_whitelist() -> frozenset:
    """Đọc SPELLING_WHITELIST_PATH -> frozenset từ ngoại lai (lowercase). Trả
    về frozenset rỗng nếu file chưa tồn tại."""
    if not SPELLING_WHITELIST_PATH.exists():
        return frozenset()
    with open(SPELLING_WHITELIST_PATH, encoding="utf-8") as f:
        return frozenset(line.strip().lower() for line in f.readlines()[1:] if line.strip())
