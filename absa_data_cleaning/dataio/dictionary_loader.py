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
transforms.stage6_lexical.split_suspect_teencode_reviews). File này CÓ
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

Định dạng dictionary/emoji_meaning.txt (bước 14): HEADER + mỗi dòng
"emoji|nghĩa_nối_bằng_gạch_dưới|pos/neg/neu" (vd "😍|rất_thích|pos"). Emoji
có thể gồm nhiều ký tự (cờ 🇻🇳). Emoji chưa có trong file chỉ bị bỏ khỏi câu và
được liệt kê ra file emoji_unknown để bổ sung.

lib/vi_VN.dic (Giai đoạn 6): từ điển hunspell tiếng Việt của LibreOffice
(github.com/LibreOffice/dictionaries, vi/vi_VN.dic, GPL), dòng 1 = số mục, mỗi
dòng sau là 1 âm tiết có thật — dùng làm danh sách "tiếng Việt chuẩn".

lib/ViLexNorm.csv (Giai đoạn 6): bộ chuẩn hoá từ vựng bình luận mạng xã hội
tiếng Việt (huggingface.co/datasets/visolex/ViLexNorm, CC BY-NC-SA 4.0), cột
input/output là list token căn 1-1 (gốc -> chuẩn hoá) — trích thành từ điển
gợi ý {token: Counter(dạng chuẩn)}.

lib/english_10000.txt (Giai đoạn 6): 10.000 từ tiếng Anh phổ biến nhất
(github.com/first20hours/google-10000-english, bản no-swears).
"""

import ast
from collections import Counter, defaultdict
from functools import lru_cache

from config.settings import DICTIONARY_DIR, LIB_DIR
from transforms.utils_text import normalize_unicode

TEENCODE_DICT_PATH = DICTIONARY_DIR / "teencode_abbreviation.txt"
SUSPECT_TEENCODE_TERMS_PATH = DICTIONARY_DIR / "suspect_teencode_terms.txt"
SPELLING_ERRORS_PATH = DICTIONARY_DIR / "spelling_errors.txt"
SPELLING_WHITELIST_PATH = DICTIONARY_DIR / "spelling_whitelist.txt"
EMOJI_MEANING_PATH = DICTIONARY_DIR / "emoji_meaning.txt"
VIETNAMESE_SYLLABLES_PATH = LIB_DIR / "vi_VN.dic"
VILEXNORM_PATH = LIB_DIR / "ViLexNorm.csv"
ENGLISH_WORDS_PATH = LIB_DIR / "english_10000.txt"


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


@lru_cache(maxsize=1)
def load_emoji_dict() -> dict:
    """Đọc EMOJI_MEANING_PATH -> {emoji: (nghĩa, sentiment)}. Rỗng nếu chưa có file."""
    if not EMOJI_MEANING_PATH.exists():
        return {}
    with open(EMOJI_MEANING_PATH, encoding="utf-8") as f:
        rows = (line.rstrip("\n").split("|") for line in f.readlines()[1:])
        return {r[0]: (r[1], r[2]) for r in rows if len(r) >= 3 and r[0] and r[1]}


@lru_cache(maxsize=1)
def load_vietnamese_syllables() -> frozenset:
    """Đọc VIETNAMESE_SYLLABLES_PATH -> frozenset âm tiết tiếng Việt (lowercase,
    đi qua `normalize_unicode` như dữ liệu ở Giai đoạn 2: 'hoà' -> 'hòa')."""
    with open(VIETNAMESE_SYLLABLES_PATH, encoding="utf-8") as f:
        return frozenset(normalize_unicode(line.strip()).lower() for line in f.readlines()[1:] if line.strip())


@lru_cache(maxsize=1)
def load_vilexnorm_map() -> dict:
    """Đọc VILEXNORM_PATH -> {token gốc (lowercase): Counter(dạng chuẩn hoá)},
    chỉ gồm cặp token có thay đổi."""
    import pandas as pd

    df = pd.read_csv(VILEXNORM_PATH)
    result: dict = defaultdict(Counter)
    for src, dst in zip(df["input"], df["output"]):
        src, dst = ast.literal_eval(src), ast.literal_eval(dst)
        if len(src) != len(dst):
            continue
        for a, b in zip(src, dst):
            a, b = normalize_unicode(a).lower(), normalize_unicode(b).lower()
            if a != b:
                result[a][b] += 1
    return dict(result)


@lru_cache(maxsize=1)
def load_english_words() -> frozenset:
    """Đọc ENGLISH_WORDS_PATH -> frozenset từ tiếng Anh >= 2 chữ cái (bỏ 'a', 'c', 's'...)."""
    with open(ENGLISH_WORDS_PATH, encoding="utf-8") as f:
        return frozenset(w for w in (line.strip().lower() for line in f) if len(w) >= 2)
