"""
transforms/utils_text.py
==========================
Hàm tiện ích thuần (pure) dùng chung giữa nhiều file tang*_*.py — regex,
chuẩn hoá unicode, đo độ tương đồng chuỗi, v.v.

Nguyên tắc: mọi hàm ở đây phải THUẦN (không side-effect, cùng input luôn ra
cùng output) để các hàm ở tang*_*.py có thể compose lại một cách an toàn.
"""

import difflib
import re
import unicodedata
from functools import lru_cache

# Nguyên âm (không dấu) tiếng Việt/Anh, dùng kèm unicodedata.normalize("NFD", ...)
# để bắt được cả nguyên âm có dấu (vd 'ế' -> NFD tách thành 'e' + dấu mũ/sắc rời,
# nên chỉ cần so ký tự nền 'e' là đủ, không cần liệt kê hết các biến thể có dấu).
_VOWELS = set("aeiouyAEIOUY")

# Các khoảng Unicode emoji phổ biến (mặt cười, ký hiệu, phương tiện, cờ quốc
# gia, dingbats...) + các ký tự đi kèm thường gặp trong chuỗi emoji (variation
# selector-16 ép hiển thị dạng emoji, zero-width joiner dùng để ghép emoji vd
# emoji gia đình, combining enclosing keycap vd '1' + U+20E3).
# Dùng \\uXXXX / \\UXXXXXXXX thay vì gõ thẳng ký tự emoji để tránh lỗi encoding
# khi file được mở/chỉnh sửa trên các editor/console không hỗ trợ đủ Unicode.
_EMOJI_RANGES = (
    "\U0001F1E6-\U0001F1FF"  # regional indicator symbols (cờ quốc gia)
    "\U0001F300-\U0001F5FF"  # ký hiệu & hình ảnh linh tinh
    "\U0001F600-\U0001F64F"  # emoticon (mặt cười...)
    "\U0001F680-\U0001F6FF"  # phương tiện & bản đồ
    "\U0001F700-\U0001F77F"  # ký hiệu giả kim
    "\U0001F780-\U0001F7FF"  # hình học mở rộng
    "\U0001F800-\U0001F8FF"  # mũi tên bổ sung C
    "\U0001F900-\U0001F9FF"  # ký hiệu & hình ảnh bổ sung
    "\U0001FA00-\U0001FA6F"  # ký hiệu cờ vua
    "\U0001FA70-\U0001FAFF"  # ký hiệu & hình ảnh mở rộng A
    "☀-⛿"  # ký hiệu linh tinh (mặt trời, ngôi sao...)
    "✀-➿"  # dingbats (kéo, dấu tích, máy bay giấy...)
    "⌀-⏿"  # ký hiệu kỹ thuật linh tinh (đồng hồ...)
    "⬀-⯿"  # ký hiệu & mũi tên linh tinh (ngôi sao, mũi tên...)
    "️"  # variation selector-16
    "‍"  # zero-width joiner
    "⃣"  # combining enclosing keycap
)
_EMOJI_CHAR_RE = re.compile(f"[{_EMOJI_RANGES}]")

# Regex URL dùng chung cho T2.13 (review chỉ chứa URL/quảng cáo) + T2.14
# (review spam) — bắt scheme tường minh (http(s)://...), tiền tố www., hoặc
# domain trần kèm TLD phổ biến trong quảng cáo bán hàng (vd 'khuyenmai.vn',
# 'abc.com/sp1'). KHÔNG dùng 'shop'/'me' trong danh sách TLD dù rất phổ biến
# trong domain quảng cáo thực tế: review tiếng Việt thường thiếu khoảng trắng
# sau dấu chấm cuối câu (vd '...lùi 1 size.Shop đóng gói...' — ý là 'size.
# Shop...' 2 câu riêng), khiến 'size.Shop' bị đọc nhầm thành domain — đã gặp
# false positive thật trong data/interim khi triển khai (xem lessons-learned).
_URL_RE = re.compile(
    r"https?://\S+"
    r"|www\.\S+"
    r"|\b[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.(?:com|net|org|vn|store|info|biz|io)(?:\.\w{2,3})?(?:/\S*)?\b",
    re.IGNORECASE,
)

# Regex số điện thoại VN — số bắt đầu bằng '0' hoặc '+84', tổng cộng 9-11 chữ
# số (đúng độ dài SĐT di động/cố định VN thực tế), có thể tách bằng khoảng
# trắng/dấu chấm/gạch ngang (vd '090.123.4567'). Yêu cầu TỐI THIỂU 9 chữ số
# (thay vì 8) để tránh bắt nhầm ngày tháng dạng 'DD.MM.YYYY' (vd '01.02.2023'
# chỉ có 8 chữ số) — đã gặp rủi ro false positive này khi rà soát thực tế.
_PHONE_RE = re.compile(r"(?<!\d)(?:\+84|0)(?:[\s.\-]?\d){8,10}(?!\d)")


def normalize_unicode(text: str) -> str:
    """Chuẩn hoá Unicode (NFC) cho tiếng Việt — nền tảng cho nhiều bước Tầng 2.

    TODO: implement bằng unicodedata.normalize("NFC", text).
    """
    raise NotImplementedError


def strip_extra_whitespace(text: str) -> str:
    """Loại khoảng trắng thừa / nhiều khoảng trắng liên tiếp (T2.24).

    TODO: implement bằng regex.
    """
    raise NotImplementedError


def is_emoji_only(text: str) -> bool:
    """T2.9 — True nếu `text` (sau khi bỏ hết khoảng trắng) CHỈ gồm ký tự
    emoji, không lẫn bất kỳ chữ/số/ký tự đặc biệt nào khác.

    Chuỗi rỗng / toàn khoảng trắng / None trả về False — đó là phạm vi T1.3
    (dòng thiếu nội dung), không phải T2.9 (nội dung chỉ toàn emoji).
    """
    if text is None:
        return False
    non_ws = re.sub(r"\s+", "", str(text))
    if not non_ws:
        return False
    return all(_EMOJI_CHAR_RE.fullmatch(ch) for ch in non_ws)


def is_emoji_or_special_char_only(text: str) -> bool:
    """T2.9 + T2.10 (GỘP CHUNG) — True nếu `text` (sau khi strip khoảng
    trắng) KHÔNG chứa bất kỳ chữ cái/chữ số nào (dùng `str.isalnum()`, xử lý
    đúng cả tiếng Việt có dấu lẫn ký tự Latin/số) — nghĩa là toàn bộ nội dung
    chỉ gồm emoji và/hoặc ký tự đặc biệt (dấu câu, ký hiệu...), CÓ THỂ TRỘN
    LẪN cả 2 loại (vd '!!! 😊' vẫn tính, không cần phân biệt riêng T2.9/T2.10).

    Chuỗi rỗng / toàn khoảng trắng / None trả về False — đó là phạm vi T1.3,
    không phải T2.9/T2.10.
    """
    if text is None:
        return False
    stripped = str(text).strip()
    if not stripped:
        return False
    return not any(ch.isalnum() for ch in stripped)


def has_vowel(text: str) -> bool:
    """True nếu `text` có ít nhất 1 nguyên âm (a/e/i/o/u/y, có dấu hay không).

    Dùng `unicodedata.normalize("NFD", ...)` để tách dấu ra khỏi ký tự nền
    (vd 'ế' -> 'e' + dấu rời) trước khi so — nhờ vậy không cần liệt kê hết
    mọi biến thể có dấu của nguyên âm tiếng Việt.
    """
    decomposed = unicodedata.normalize("NFD", str(text))
    return any(ch in _VOWELS for ch in decomposed)


def count_meaningful_tokens(text: str) -> int:
    """Đếm số "từ có nghĩa" trong chuỗi — hỗ trợ T2.11, T2.12
    (review quá ngắn / chỉ có ký tự vô nghĩa).

    TODO: implement — cân nhắc dùng tokenizer tiếng Việt (underthesea/pyvi) khi
    triển khai thật, hiện để interface trung lập với thư viện cụ thể.
    """
    raise NotImplementedError


def text_similarity(a: str, b: str) -> float:
    """Trả về điểm tương đồng [0,1] giữa 2 chuỗi — dùng cho near-duplicate (T2.16).

    Dùng `difflib.SequenceMatcher` (Ratcliff/Obershelp — cùng họ với các thuật
    toán edit-distance kiểu Levenshtein, không cần cài thêm dependency ngoài
    stdlib) trên chuỗi đã lowercase + strip khoảng trắng, để 2 review giống hệt
    nhau ngoại trừ khác biệt HOA/thường hoặc khoảng trắng đầu/cuối vẫn được
    tính là tương đồng tuyệt đối (1.0). `rapidfuzz` (xem requirements.txt) là
    lựa chọn thay thế nếu cần tốc độ cao hơn trên dataset lớn — đổi cài đặt
    hàm này khi có số liệu thực nghiệm cho thấy cần.

    Chuỗi rỗng/toàn khoảng trắng/None ở BẤT KỲ bên nào trả về 0.0 (không đủ
    nội dung để so sánh, không phải "trùng lặp").
    """
    if a is None or b is None:
        return 0.0
    a_norm = str(a).strip().lower()
    b_norm = str(b).strip().lower()
    if not a_norm or not b_norm:
        return 0.0
    return difflib.SequenceMatcher(None, a_norm, b_norm).ratio()


def contains_url(text: str) -> bool:
    """Kiểm tra chuỗi có chứa URL không (http(s)://..., www...., hoặc domain
    trần kèm TLD phổ biến như 'abc.vn') — hỗ trợ T2.13 (review chỉ chứa
    URL/quảng cáo) + T2.14 (review spam, dùng chung bộ lọc regex này).

    Chuỗi rỗng/None trả về False.
    """
    if text is None:
        return False
    return _URL_RE.search(str(text)) is not None


@lru_cache(maxsize=8)
def _word_boundary_pattern(sorted_terms: tuple) -> re.Pattern:
    """Regex khớp BẤT KỲ chuỗi nào trong `sorted_terms` theo ranh giới từ
    (\\b...\\b), không phân biệt hoa/thường — dùng chung cho
    `normalize_teencode_text` (thay thế) và `contains_any_term` (chỉ kiểm
    tra có khớp hay không), hỗ trợ T2.17 + T2.18.

    `sorted_terms` PHẢI đã sắp xếp GIẢM DẦN theo độ dài chuỗi trước khi
    truyền vào: đảm bảo cụm nhiều từ (vd 'san pham') được thử khớp TRƯỚC từ
    đơn lẻ nếu cả 2 cùng bắt đầu tại 1 vị trí trong văn bản (regex alternation
    `|` chọn nhánh nào khớp trước theo thứ tự liệt kê).

    Cache bằng lru_cache vì cùng 1 bộ `sorted_terms` (vd toàn bộ khoá từ điển
    teencode) được dùng lại cho MỖI dòng review khi xử lý — tránh biên dịch
    lại regex hàng nghìn lần.
    """
    return re.compile(r"\b(" + "|".join(re.escape(t) for t in sorted_terms) + r")\b", re.IGNORECASE)


TEENCODE_CONTEXT_WINDOW = 40  # so ky tu xet moi ben quanh vi tri khop, xem normalize_teencode_text


def normalize_teencode_text(text: str, teencode_dict: dict, context_window: int = TEENCODE_CONTEXT_WINDOW) -> str:
    """T2.17 + T2.18 (GỘP CHUNG) — Thay thế teencode/từ viết tắt trong `text`
    bằng dạng chuẩn theo `teencode_dict` ({teencode (đã lowercase): [ứng
    viên, ...]}, xem `dataio.dictionary_loader.load_teencode_dict`).

    Khớp KHÔNG phân biệt hoa/thường theo ranh giới từ, hỗ trợ CẢ khoá nhiều
    từ (vd 'san pham' -> 'sản phẩm') lẫn khoá 1 từ, thực hiện trong 1 lượt
    `re.sub` duy nhất (không lặp lại thay thế đè lên kết quả vừa thay).

    Với mỗi vị trí khớp 1 khoá:
      - Chỉ 1 ứng viên (khoá không đa nghĩa, hoặc từ điển chỉ khai báo 1 dòng
        cho khoá này) -> LUÔN thay thế bằng ứng viên đó, bất kể `flag`.
      - NHIỀU ứng viên (khoá đa nghĩa, vd 'nc' -> 'nước'/'nói chung') -> xét
        cửa sổ `context_window` ký tự MỖI BÊN quanh vị trí khớp (trong `text`
        GỐC, chưa qua thay thế), tìm ứng viên có `context_keywords` xuất hiện
        (dạng chuỗi con, không phân biệt hoa/thường) trong cửa sổ đó:
          - ĐÚNG 1 ứng viên khớp từ khoá -> dùng ứng viên đó.
          - 0 hoặc >=2 ứng viên cùng khớp (không đủ căn cứ chọn 1) -> GIỮ
            NGUYÊN từ gốc tại vị trí này (không đoán) — các occurrence chưa
            xử lý được này là căn cứ để
            `tang2_content_quality.split_suspect_teencode_reviews` tách dòng
            ra Suspect_Teencode_Abbreviation.xlsx.

    `text`/`teencode_dict` rỗng trả về nguyên vẹn `text` (không có gì để thay).
    """
    if text is None or not teencode_dict:
        return text
    s = str(text)
    sorted_keys = tuple(sorted(teencode_dict, key=len, reverse=True))
    pattern = _word_boundary_pattern(sorted_keys)

    def _resolve(m: re.Match) -> str:
        candidates = teencode_dict[m.group(0).lower()]
        if len(candidates) == 1:
            return candidates[0]["value"]
        window = (
            s[max(0, m.start() - context_window):m.start()]
            + " " + s[m.end():m.end() + context_window]
        ).lower()
        matched = [
            c for c in candidates
            if c["context_keywords"] and any(kw in window for kw in c["context_keywords"])
        ]
        return matched[0]["value"] if len(matched) == 1 else m.group(0)

    return pattern.sub(_resolve, s)


def contains_any_term(text: str, terms) -> bool:
    """True nếu `text` chứa ÍT NHẤT 1 từ/cụm từ trong `terms` (ranh giới từ,
    không phân biệt hoa/thường) — hỗ trợ
    `tang2_content_quality.split_suspect_teencode_reviews` (tách review chứa
    từ nghi vấn ra Suspect_Teencode_Abbreviation.xlsx).

    `text`/`terms` rỗng trả về False.
    """
    if text is None or not terms:
        return False
    sorted_terms = tuple(sorted(terms, key=len, reverse=True))
    pattern = _word_boundary_pattern(sorted_terms)
    return pattern.search(str(text)) is not None


def contains_phone_number(text: str) -> bool:
    """Kiểm tra chuỗi có chứa số điện thoại VN không (chuỗi số thật, xem
    `_PHONE_RE`) — hỗ trợ T2.13 + T2.14 (dùng chung 1 bộ lọc regex URL/số
    điện thoại với `contains_url`, xem
    `tang2_content_quality.drop_url_hotline_or_spam_reviews`).

    CỐ TÌNH KHÔNG bắt theo từ khoá kiểu 'hotline'/'zalo'/'ib'/'inbox'/'sđt'
    đứng riêng (dù tên hàm gốc từng gợi ý vậy): rà soát thực tế trên
    data/interim cho thấy các từ này xuất hiện RẤT NHIỀU trong review THẬT
    (vd 'Ko cài đc zalo' — đang chê tính năng máy, không phải quảng cáo; 'shop
    rep ib nhanh' — khen thái độ phục vụ) nên bắt theo từ khoá gây xoá nhầm
    hàng loạt review hợp lệ. Số điện thoại dạng chuỗi số thật đáng tin cậy
    hơn nhiều và vẫn bắt được hầu hết trường hợp hotline/SĐT thực tế (vì
    quảng cáo hầu như luôn kèm số cụ thể).

    Chuỗi rỗng/None trả về False.
    """
    if text is None:
        return False
    return _PHONE_RE.search(str(text)) is not None


# --- T2.19: kiểm tra chính tả tiếng Việt theo cấu trúc âm tiết ---------------
# Tiếng Việt đơn lập: mỗi "từ" tách bằng khoảng trắng là 1 âm tiết, và tập âm
# tiết hợp lệ hữu hạn, sinh được bằng luật ghép (phụ âm đầu + vần + thanh) —
# nên KHÔNG cần từ điển ngoài (vốn không có sẵn trong requirements) để biết 1
# token có phải âm tiết tiếng Việt hay không: 'hangf', 'cũnh', 'hj' đều không
# khớp luật. Luật ở đây CỐ TÌNH lỏng ở chỗ hiếm gặp (vd 'giêng') để không
# tách nhầm từ đúng; từ ngoại lai/thương hiệu ('ok', 'seal', 'iphone') cũng
# không khớp luật -> cần `dictionary/spelling_whitelist.txt` (xem
# `dataio.dictionary_loader`) cho các từ ngoại lai bị trùng với 1 cách sửa.
_TONE_MARKS = {"̀": "f", "́": "s", "̃": "x", "̉": "r", "̣": "j"}
_TELEX_TONES = {v: k for k, v in _TONE_MARKS.items()}
_LATIN_LETTERS = set("abcdefghijklmnopqrstuvwxyzđ")
_ONSET = "ngh|ng|nh|ch|gh|gi|kh|ph|th|tr|qu|[bcdđghklmnprstvx]"
_OPEN_RIME = "ay|ai|ao|au|âu|ây|eo|êu|ia|iêu|yêu|iu|oai|oay|oeo|oi|ôi|ơi|ua|ui|uôi|uây|ưa|ưi|ươi|ươu|ưu|uya|uyu|uơ|y"
_CLOSABLE = "a|ă|â|e|ê|i|o|ô|ơ|u|ư|iê|yê|oa|oă|oe|uâ|uê|uô|uy|uyê|ươ"
_CODA_RIMES = {  # phụ âm cuối -> nhân vần được phép đứng trước nó
    "c": "a|ă|â|e|o|ô|u|ư|iê|uô|ươ|oa|oă|uâ|oo",
    "ng": "a|ă|â|e|o|ô|u|ư|iê|uô|ươ|oa|oă|uâ|oo",
    "ch": "a|ê|i|e|oa|uê|uy",
    "nh": "a|ê|i|e|oa|uê|uy",
    "n": _CLOSABLE, "m": _CLOSABLE, "t": _CLOSABLE, "p": _CLOSABLE,
}
_RIME_RE = "|".join(
    [_OPEN_RIME, _CLOSABLE] + [f"(?:{v})(?:{c})" for c, v in _CODA_RIMES.items()]
)
_SYLLABLE_RE = re.compile(rf"^({_ONSET})?({_RIME_RE})$")
_SPELLING_TOKEN_RE = re.compile(r"(?<![\w@#])[^\W\d_]+(?![\w@])")


def _split_tone(word: str) -> tuple[str, str]:
    """'hàng' -> ('hang', dấu huyền). Tách dấu thanh (5 dấu combining), giữ
    nguyên dấu mũ/móc/trăng vì đó là 1 phần của chữ cái (â, ê, ơ, ư, ă)."""
    decomposed = unicodedata.normalize("NFD", word.lower())
    tone = "".join(ch for ch in decomposed if ch in _TONE_MARKS)
    base = "".join(ch for ch in decomposed if ch not in _TONE_MARKS)
    return unicodedata.normalize("NFC", base), tone


def is_vietnamese_syllable(word: str) -> bool:
    """True nếu `word` (1 token chữ cái) là 1 âm tiết tiếng Việt hợp lệ theo
    cấu trúc (phụ âm đầu + vần + thanh) — KHÔNG kiểm tra có nghĩa hay không
    ('hoà'/'hòa' đều đúng, 'thí' vs 'thì' không phân biệt được)."""
    base, tone = _split_tone(word)
    if len(tone) > 1:
        return False
    if base in ("gi", "gin"):  # 'gì', 'gìn': 'gi' vừa là phụ âm đầu vừa là nguyên âm
        return True
    m = _SYLLABLE_RE.match(base)
    if not m:
        return False
    onset, rime = m.group(1), m.group(2)
    if onset == "qu" and rime[0] == "u":
        return False
    if onset == "gi" and rime[0] == "i":
        return False
    if onset in ("k", "gh", "ngh") and rime[0] not in "eêiy":
        return False
    if onset in ("c", "g", "ng") and rime[0] in "eêiy":
        return False
    # Vần kết thúc bằng c/ch/p/t chỉ đi với thanh sắc/nặng (hoặc chưa có dấu —
    # bỏ qua lỗi thiếu dấu, thuộc T2.20).
    return not (rime.endswith(("c", "ch", "p", "t")) and tone and tone not in ("́", "̣"))


def _telex_decode(word: str) -> str | None:
    """'hangf' -> 'hàng', 'tôts' -> 'tốt', 'nhaanj' -> 'nhận': người gõ Telex
    quên chuyển bộ gõ nên phím dấu (s f r x j) còn sót ở cuối từ. None nếu
    `word` không có dạng đó hoặc kết quả không phải âm tiết hợp lệ."""
    if len(word) < 3 or word[-1] not in _TELEX_TONES:
        return None
    base = word[:-1]
    for raw, mark in (("dd", "đ"), ("aa", "â"), ("ee", "ê"), ("oo", "ô"), ("aw", "ă"), ("ow", "ơ"), ("uw", "ư")):
        base = base.replace(raw, mark, 1)
    vowels = [i for i, ch in enumerate(base) if ch in "aăâeêioôơuưy"]
    # 'u' sau 'q' và 'i' sau 'g' thuộc phụ âm đầu (qu, gi), không nhận dấu thanh.
    vowels = [i for i in vowels if not (i and base[i - 1:i + 1] in ("qu", "gi") and i + 1 < len(base))]
    if not vowels:
        return None
    marked = [i for i in vowels if base[i] in "ăâêôơư"]
    if marked:
        pos = marked[-1]
    elif len(vowels) == 3:
        pos = vowels[1]
    elif len(vowels) == 2 and vowels[-1] < len(base) - 1 and base[vowels[0]:vowels[0] + 2] in ("oa", "oe", "uy"):
        pos = vowels[1]  # có phụ âm cuối: 'toán', 'hoàn'
    else:
        pos = vowels[0]
    result = unicodedata.normalize("NFC", base[:pos + 1] + _TELEX_TONES[word[-1]] + base[pos + 1:])
    return result if is_vietnamese_syllable(result) else None


def _edits1(word: str, alphabet: str) -> set:
    """Mọi chuỗi cách `word` đúng 1 phép sửa (xoá/đảo 2 ký tự liền kề/thay/chèn)."""
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    return (
        {a + b[1:] for a, b in splits if b}
        | {a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1}
        | {a + c + b[1:] for a, b in splits if b for c in alphabet}
        | {a + c + b for a, b in splits for c in alphabet}
    )


def suggest_spelling_fix(word: str, vocab: dict) -> str | None:
    """Gợi ý dạng đúng cho `word` (đã lowercase) — hoặc None nếu không đủ chắc.

    Thử lần lượt: (1) giải mã Telex sót; (2) cách `word` đúng 1 phép sửa, chỉ
    chọn trong `vocab` ({âm tiết hợp lệ: số lần xuất hiện trong chính dữ liệu})
    với các điều kiện chống đoán bừa: ứng viên phải phổ biến (>= 5 lần) VÀ gấp
    >= 5 lần ứng viên kế tiếp, giữ nguyên ký tự đầu (gõ nhầm hiếm khi trúng
    chữ đầu; nếu không 'đthoai' -> 'thoai' sai), và `word` không chứa f/j/w/z
    (teencode kiểu 'zô' = 'vô'/'dô', mơ hồ) và dài >= 3 ký tự. (2) chỉ áp cho token CÓ dấu
    tiếng Việt: token ASCII trần đa số là từ ngoại lai ('ping' -> 'pin' sai)."""
    telex = _telex_decode(word)
    if telex and telex in vocab:
        return telex
    if len(word) < 3 or word.isascii() or any(ch in "fjwz" for ch in word):
        return None
    alphabet = "".join(sorted(set("".join(vocab))))
    ranked = sorted(
        ((vocab[c], c) for c in _edits1(word, alphabet) if c in vocab and c[0] == word[0]),
        reverse=True,
    )
    if ranked and ranked[0][0] >= 5 and (len(ranked) == 1 or ranked[0][0] >= 5 * ranked[1][0]):
        return ranked[0][1]
    return None


def build_syllable_vocab(texts, min_count: int = 2) -> dict:
    """{âm tiết hợp lệ (lowercase): số lần xuất hiện >= `min_count`} từ 1 dãy
    văn bản — làm từ điển ứng viên cho `suggest_spelling_fix`."""
    counts: dict = {}
    for text in texts:
        for w in _SPELLING_TOKEN_RE.findall(str(text).lower()):
            if is_vietnamese_syllable(w):
                counts[w] = counts.get(w, 0) + 1
    return {w: n for w, n in counts.items() if n >= min_count}


def _match_case(original: str, fixed: str) -> str:
    if len(original) > 1 and original.isupper():
        return fixed.upper()
    return fixed.capitalize() if original[:1].isupper() else fixed


def correct_spelling_text(text: str, errors: dict, whitelist, vocab: dict) -> tuple[str, list]:
    """Sửa lỗi chính tả trong `text` -> (text mới, [(từ sai, từ đúng), ...]).

    Với mỗi token chữ cái (bỏ qua token dính số/@/#): (a) có trong `errors`
    ({sai: đúng}, từ điển sửa tay — ưu tiên cao nhất, áp dụng cả khi token
    trông hợp lệ); (b) nếu không: chỉ xét token Latin >= 2 ký tự, KHÔNG phải
    âm tiết hợp lệ, không trong `whitelist`, và cũng không phải âm tiết hợp lệ
    sau khi gộp ký tự lặp ('nhaaa' — thuộc T2.21) rồi hỏi
    `suggest_spelling_fix`. Token không có cách sửa đủ chắc thì giữ nguyên."""
    fixes: list = []

    def _sub(m: re.Match) -> str:
        word, low = m.group(0), m.group(0).lower()
        fixed = errors.get(low)
        if fixed is None:
            if (
                len(low) < 2
                or low in whitelist
                or not all(unicodedata.normalize("NFD", ch)[0] in _LATIN_LETTERS for ch in low)
                or is_vietnamese_syllable(low)
                or any(is_vietnamese_syllable(re.sub(r"(.)\1+", r"\1", w)) for w in (low, _split_tone(low)[0]))
            ):
                return word
            fixed = suggest_spelling_fix(low, vocab)
        if fixed is None or fixed == low:
            return word
        fixes.append((word, fixed))
        return _match_case(word, fixed)

    return _SPELLING_TOKEN_RE.sub(_sub, str(text)), fixes
