"""
transforms/stage6_lexical.py
==============================
GIAI ĐOẠN 6 — CHUẨN HOÁ TỪ VỰNG. Thứ tự rất quan trọng (mỗi bước cần đầu ra
của bước trước):

  17. Bước 9 + 10: teencode & viết tắt ('ko', 'dc', 'j', 'sp', 'đt') —
      `normalize_teencode_and_abbreviations` + `split_suspect_teencode_reviews`
      (taxonomy T2.17 + T2.18). Làm ĐẦU TIÊN vì khôi phục dấu/sửa chính tả cho
      kết quả sai nếu gặp 'ko', 'dc'.
  18. Bước 18: tiếng Anh xen lẫn & từ mượn — `mark_protected_tokens`. PHẢI
      TRƯỚC khôi phục dấu/sửa chính tả ('ship', 'size', 'pin', 'case',
      'fullbox' sẽ bị thêm dấu/sửa sai).
  19. Bước 12: khôi phục dấu — `restore_diacritics`. Trước sửa chính tả (sửa
      chính tả trên câu không dấu gần như vô nghĩa).
  20. Bước 11: lỗi chính tả — `fix_spelling_errors` /
      `split_spelling_error_reviews` (T2.19 -> Suspect_Spelling_Errors.xlsx).
  21. Bước 20: tiếng lóng cảm xúc — `normalize_emotional_slang`. Làm CUỐI vì
      chỉ nhận diện đúng khi văn bản đã có dấu + đúng chính tả.

Gợi ý kế hoạch: với bước 9, 10, 18, 20 kiểm duyệt ở CẤP TỪ VỰNG (trích token
ngoài từ điển + tần suất -> duyệt tay -> file ánh xạ trong dictionary/) thay
vì duyệt từng câu.

Checkpoint sau giai đoạn: v6_lexical.
"""

import re
import unicodedata
from collections import Counter, defaultdict

import pandas as pd

from dataio.dictionary_loader import (
    load_spelling_errors_dict,
    load_spelling_whitelist,
    load_suspect_teencode_terms,
    load_english_words,
    load_teencode_dict,
    load_vietnamese_syllables,
    load_vilexnorm_map,
)
from transforms.stage1_structure import CONTENT_COL, CRITERIA_COL
from transforms.stage2_normalize import text_columns
from transforms.stage4_char_noise import EMOJI_SENTIMENT_COL, EMOJIS_COL
from transforms.utils_text import (
    _match_case,
    build_syllable_vocab,
    contains_any_term,
    correct_spelling_text,
    is_vietnamese_syllable,
    normalize_teencode_text,
    suggest_spelling_fix,
)

PROTECTED_TOKENS_COL = "protected_tokens"
CORRECTED_CONTENT_COL = "Nội dung sau xử lý"  # T2.19: cột đề xuất sửa, để con người kiểm duyệt
CORRECTION_DETAIL_COL = "Chi tiết sửa"  # T2.19: 'từ sai -> từ đúng; ...'

# --- Kiểm duyệt cấp token (bước 9, 10, 18, 12, 11) ---------------------------
SOURCE_ROW_COL = "Dòng Excel gốc"  # = index + 2 (header + đánh số từ 1), như scripts/legacy
SUSPECT_TOKENS_COL = "Token nghi vấn"  # 'ko, đc, hang' (lowercase, mỗi token 1 lần)
TOKEN_DETAIL_COL = "Chi tiết token"  # 'ko -> không [teencode/viết tắt]; iphone [ngoài từ điển]'
# Gợi ý cho mỗi token được BỎ PHIẾU giữa các nguồn: SOURCE_RULE (classify_token), SOURCE_VILEXNORM
# (lib/ViLexNorm.csv, không ngữ cảnh) và các model theo ngữ cảnh do scripts/run_stage6.py truyền vào
# (bmd1905, model dấu). 'giữ nguyên' cũng là 1 phiếu.
SOURCE_RULE = "luật"
SOURCE_VILEXNORM = "ViLexNorm"
SOURCE_BMD = "bmd1905"
SOURCE_ACCENT = "model dấu"
KEEP = "giữ nguyên"
CLEANED_SUFFIX = " (chuẩn hoá)"  # cột mới = tên cột gốc + hậu tố; riêng nội dung: CLEANED_CONTENT_COL
CLEANED_CONTENT_COL = "Nội dung chuẩn hoá"
REPLACED_TOKENS_COL = "Token đã thay"  # 'ko -> không; mn -> mọi người'
# Từ hợp lệ có nghĩa khác khi đổi theo từ điển: 'đường may' != 'đường máy', '50 kg' != '50 không'.
NO_AUTO_REPLACE = frozenset({"may", "kg"})
MIN_RESTORATIONS = 2  # khôi phục dấu trong câu: cần >= 2 từ như vậy (câu viết không dấu); 1 từ lẻ trong câu đã có dấu thường là từ đúng ('con màn hình')
MIN_VOTES = 2  # chỉ thay token khi >= MIN_VOTES nguồn cùng gợi ý (1 phiếu = để người duyệt)
CONSENSUS_COL = "Gợi ý đồng thuận"
VOTES_COL = "Số nguồn đồng ý"
DIACRITIC_KIND = "thiếu/sai dấu"
_TOKEN_RE = re.compile(r"[^\W_]+")  # chữ/số liền nhau; '_' tách luôn tag emoji 'rất_thích'
# Token ASCII hợp lệ âm tiết ('hang', 'con') chỉ bị coi là thiếu dấu khi dạng có dấu cùng
# khung chữ xuất hiện >= DIACRITIC_RATIO lần nó trong dữ liệu — CẢ trong câu có dấu đầy đủ,
# nên 'con', 'qua', 'may' đúng vẫn bị liệt kê (chấp nhận nhiễu để không sót).
# ponytail: heuristic tần suất, không biết ngữ cảnh ('con' vs 'còn'); cần PhoBERT/model khôi phục dấu nếu muốn chính xác.
DIACRITIC_RATIO = 3


def normalize_teencode_and_abbreviations(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
) -> pd.DataFrame:
    """T2.17 + T2.18 (GỘP CHUNG) — Chuẩn hoá teencode (vd 'ko' -> 'không') VÀ
    mở rộng từ viết tắt (vd 'sp' -> 'sản phẩm') trong `content_col`.

    Gộp chung vì cả 2 mục dùng CHUNG 1 từ điển
    `dictionary/teencode_abbreviation.txt` (mỗi Teencode có thể có NHIỀU dòng
    ứng viên nghĩa, vd 'nc' -> 'nước'/'nói chung', kèm cột Context_Keywords +
    Flag để chọn đúng nghĩa theo ngữ cảnh — xem
    `dataio.dictionary_loader.load_teencode_dict`) — bản thân từ điển không
    phân biệt "teencode do gõ tắt/sai chính tả" (T2.17) với "từ viết tắt có
    chủ đích" (T2.18), cả 2 đều là 1 phép thay thế chuỗi->chuỗi NHƯ NHAU,
    khác biệt chỉ là NGUỒN GỐC của từ, không ảnh hưởng cách xử lý (đúng tinh
    thần gộp như T2.9+T2.10 ở nhóm 2.1).

    Dùng `transforms.utils_text.normalize_teencode_text` (khớp CẢ khoá nhiều
    từ vd 'san pham' lẫn khoá 1 từ, không phân biệt hoa/thường, theo ranh
    giới từ; khoá ĐA NGHĨA chỉ thay khi ngữ cảnh xung quanh đủ rõ, xem
    docstring hàm đó) áp cho từng dòng của `content_col`.

    Nếu `content_col` không tồn tại trong `df`: trả về bản sao nguyên vẹn.
    Dòng có `content_col` rỗng/NaN giữ nguyên (không có gì để chuẩn hoá).

    Hàm thuần (KHÔNG đọc file): từ điển được nạp qua tham số ẩn
    `load_teencode_dict()` (dataio.dictionary_loader) — cache sẵn, không đọc
    lại file mỗi dòng. Không sửa `df` gốc, giữ nguyên index gốc.
    """
    if content_col not in df.columns:
        return df.copy()

    teencode_dict = load_teencode_dict()
    result = df.copy()
    result[content_col] = result[content_col].apply(
        lambda v: v if pd.isna(v) else normalize_teencode_text(str(v), teencode_dict)
    )
    return result


def split_suspect_teencode_reviews(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """T2.17 + T2.18 — TÁCH dòng thành 2 nhóm (kept_df, suspect_df) — CÙNG
    tinh thần split_short_reviews/split_url_hotline_or_spam_reviews: từ nghi
    vấn được TÁCH RIÊNG ra `Suspect_Teencode_Abbreviation.xlsx` để con người
    rà soát thủ công, thay vì đoán bừa 1 dạng chuẩn có thể SAI. GỌI HÀM NÀY
    SAU `normalize_teencode_and_abbreviations` (trên chính output của nó) —
    xem `run_t218.py`.

    "Từ nghi vấn" gồm 2 nguồn:
      1. `load_suspect_teencode_terms()` — từ/cụm HOÀN TOÀN KHÔNG có trong
         `dictionary/teencode_abbreviation.txt` (chưa rõ nghĩa gì cả, xem
         `dictionary/suspect_teencode_terms.txt`).
      2. Khoá ĐA NGHĨA trong `dictionary/teencode_abbreviation.txt` (Flag =
         'ambiguous', nhiều dòng cùng Teencode, vd 'nc') mà
         `normalize_teencode_and_abbreviations` KHÔNG đủ ngữ cảnh để chọn 1
         ứng viên — occurrence đó vẫn còn nguyên dạng gốc trong `content_col`
         (xem `utils_text.normalize_teencode_text`), nên chỉ cần dò lại đúng
         các khoá đa nghĩa này là bắt được đúng những dòng CHƯA xử lý được.

    Một dòng thuộc `suspect_df` khi `content_col` chứa ÍT NHẤT 1 từ/cụm từ
    trong hợp của 2 nguồn trên (ranh giới từ, không phân biệt hoa/thường —
    xem `utils_text.contains_any_term`).

    Nếu `content_col` không tồn tại trong `df`, hoặc không có từ nghi vấn nào
    ở cả 2 nguồn: trả về (df.copy(), df rỗng cùng cột) — không có gì để tách.

    Hàm thuần: không sửa `df` gốc, không I/O trực tiếp (từ điển nạp qua các
    hàm `load_*` đã cache). Giữ nguyên index gốc của các dòng ở cả 2 DataFrame
    trả về.
    """
    ambiguous_keys = {key for key, candidates in load_teencode_dict().items() if len(candidates) > 1}
    suspect_terms = load_suspect_teencode_terms() | ambiguous_keys
    if content_col not in df.columns or not suspect_terms:
        return df.copy(), df.iloc[0:0].copy()

    is_suspect = df[content_col].apply(
        lambda v: False if pd.isna(v) else contains_any_term(str(v), suspect_terms)
    )
    return df.loc[~is_suspect].copy(), df.loc[is_suspect].copy()


def _correct_content(df: pd.DataFrame, content_col: str) -> tuple[pd.Series, pd.Series]:
    """(nội dung đã sửa, chi tiết sửa) theo từng dòng của `content_col`.
    Từ điển ứng viên sửa (`vocab`) dựng từ CHÍNH `df` — xem
    `utils_text.suggest_spelling_fix`. Dòng rỗng/NaN giữ nguyên, chi tiết ''."""
    errors, whitelist = load_spelling_errors_dict(), load_spelling_whitelist()
    vocab = build_syllable_vocab(df[content_col].dropna())
    results = df[content_col].apply(
        lambda v: (v, []) if pd.isna(v) else correct_spelling_text(v, errors, whitelist, vocab)
    )
    fixed = results.apply(lambda r: r[0])
    detail = results.apply(lambda r: "; ".join(f"{a} -> {b}" for a, b in r[1]))
    return fixed, detail


def fix_spelling_errors(df: pd.DataFrame, content_col: str = CONTENT_COL) -> pd.DataFrame:
    """T2.19 — Sửa lỗi chính tả trong `content_col` (trả về bản sao đã sửa).
    Muốn CON NGƯỜI KIỂM DUYỆT trước khi áp dụng thì dùng
    `split_spelling_error_reviews` (cách chạy thật, xem `run_t219.py`); hàm
    này là dạng "sửa luôn, không hỏi" của cùng logic.

    Phát hiện + sửa theo 3 lớp (xem `utils_text.correct_spelling_text`):
      1. `dictionary/spelling_errors.txt` — từ điển sửa tay các lỗi thường gặp.
      2. Bộ kiểm tra âm tiết tiếng Việt theo luật ghép vần (không cần từ điển
         ngoài): token không phải âm tiết hợp lệ, không thuộc
         `dictionary/spelling_whitelist.txt` (từ ngoại lai/thương hiệu) -> nghi
         sai chính tả.
      3. Cách sửa: giải mã Telex sót ('hangf' -> 'hàng') hoặc sửa 1 ký tự về
         âm tiết phổ biến trong chính dữ liệu ('cũnh' -> 'cũng'). Không đủ chắc
         thì GIỮ NGUYÊN.

    CỐ TÌNH KHÔNG xử lý: lỗi thiếu dấu ('nhieu' — T2.20), ký tự kéo dài
    ('nhaaa' — T2.21), teencode/viết tắt (T2.17+T2.18), từ sai nhưng vẫn là âm
    tiết hợp lệ ('thí' thay 'thì' — cần ngữ cảnh/mô hình ngôn ngữ).

    Nếu `content_col` không tồn tại: trả về bản sao nguyên vẹn. Hàm thuần,
    giữ nguyên index, không sửa `df` gốc.
    """
    result = df.copy()
    if content_col in result.columns:
        result[content_col] = _correct_content(result, content_col)[0]
    return result


def split_spelling_error_reviews(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """T2.19 — TÁCH dòng thành (kept_df, suspect_df) — cùng tinh thần
    `split_suspect_teencode_reviews`: dòng có lỗi chính tả được ghi nhận thì
    tách riêng ra `Suspect_Spelling_Errors.xlsx` để con người kiểm duyệt
    (xem `run_t219.py`). `suspect_df` có thêm 2 cột NGAY SAU `content_col`:
    `CORRECTED_CONTENT_COL` (bản đã sửa — chỗ để bạn chỉnh tay) và
    `CORRECTION_DETAIL_COL` (liệt kê từ sai -> từ đúng). `content_col` giữ
    NGUYÊN văn gốc để đối chiếu.

    Một dòng thuộc `suspect_df` khi `fix_spelling_errors` sửa được >= 1 từ.
    Hàm thuần, giữ nguyên index gốc ở cả 2 DataFrame trả về.
    """
    if content_col not in df.columns:
        return df.copy(), df.iloc[0:0].copy()

    fixed, detail = _correct_content(df, content_col)
    is_suspect = detail != ""
    suspect = df.loc[is_suspect].copy()
    pos = suspect.columns.get_loc(content_col) + 1
    suspect.insert(pos, CORRECTED_CONTENT_COL, fixed[is_suspect])
    suspect.insert(pos + 1, CORRECTION_DETAIL_COL, detail[is_suspect])
    return df.loc[~is_suspect].copy(), suspect


def _strip_diacritics(word: str) -> str:
    """'được' -> 'duoc': bỏ mọi dấu (thanh + mũ/móc/trăng) và đ -> d."""
    decomposed = unicodedata.normalize("NFD", word)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).replace("đ", "d")


def build_token_stats(texts) -> dict:
    """Thống kê token trên TOÀN BỘ dữ liệu (mọi file) cho `classify_token`:
    `counts` {token lowercase: số lần}, `accented` {khung không dấu: (dạng có dấu
    phổ biến nhất, số lần)}, `vocab` (xem `utils_text.build_syllable_vocab`).
    `accented` và `vocab` chỉ gồm âm tiết có trong lib/vi_VN.dic, để gợi ý sửa
    luôn là âm tiết có thật."""
    syllables = load_vietnamese_syllables()
    texts = [str(t) for t in texts]
    counts = Counter(w for t in texts for w in _TOKEN_RE.findall(t.lower()) if not w.isdigit())
    accented: dict = {}
    for w, n in counts.items():
        if not w.isascii() and w in syllables:
            base = _strip_diacritics(w)
            if n > accented.get(base, ("", 0))[1]:
                accented[base] = (w, n)
    vocab = {w: n for w, n in build_syllable_vocab(texts).items() if w in syllables}
    return {"counts": counts, "accented": accented, "vocab": vocab}


def classify_token(token: str, stats: dict) -> tuple[str, str] | None:
    """(loại, gợi ý sửa) nếu `token` (lowercase) không phải tiếng Việt chuẩn,
    None nếu là âm tiết có trong lib/vi_VN.dic. Gợi ý '' = không đoán được.

    Thứ tự (khớp trước thắng): teencode dict (gợi ý mọi ứng viên, ' / ') ->
    spelling_errors -> whitelist ('giữ nguyên') -> lẫn chữ số ('200k', 'ip13') ->
    thiếu/sai dấu ('hang' -> 'hàng', 'duoc' -> 'được', xem DIACRITIC_RATIO) ->
    [có trong vi_VN.dic: None] -> tiếng Anh (lib/english_10000.txt) -> 'âm tiết lạ' (đúng luật ghép vần nhưng không
    có trong vi_VN.dic: 'ngừi', 'rùi', cả từ thật bị từ điển thiếu như 'sạc',
    'xịn'; không gợi ý) -> lặp ký tự ('nhaa' -> 'nha') -> sửa chính tả tự động
    (`suggest_spelling_fix`) -> 'ngoài từ điển' (tiếng Anh, thương hiệu, viết
    tắt chưa biết...). Token trong dict/whitelist VẪN liệt kê để duyệt lại.
    """
    candidates = load_teencode_dict().get(token)
    if candidates:
        return "teencode/viết tắt", " / ".join(c["value"] for c in candidates)
    if token in load_suspect_teencode_terms():
        return "teencode nghi vấn", ""
    fixed = load_spelling_errors_dict().get(token)
    if fixed:
        return "sai chính tả (từ điển)", fixed
    if token in load_spelling_whitelist():
        return "ngoại lai (whitelist)", "giữ nguyên"
    if any(ch.isdigit() for ch in token):
        return "lẫn chữ số", ""
    in_dict = token in load_vietnamese_syllables()
    well_formed = is_vietnamese_syllable(token)
    if token.isascii() or not well_formed:  # token đã có dấu + đúng luật ghép vần thì không phải 'thiếu dấu'
        accented, n = stats["accented"].get(_strip_diacritics(token), (None, 0))
        if accented and accented != token and (not in_dict or n >= DIACRITIC_RATIO * stats["counts"][token]):
            return DIACRITIC_KIND, accented
    if in_dict:
        return None
    if token.isascii() and token in load_english_words():
        return "tiếng Anh", ""
    if well_formed:  # 'sạc' (1149 lần) mà đoán sửa thì thành 'sạch' -> không gợi ý
        return "âm tiết lạ (ngoài vi_VN.dic)", ""
    collapsed = re.sub(r"(.)\1+", r"\1", token)
    if collapsed != token and stats["vocab"].get(collapsed, 0) >= 5:  # chặn 'app' -> 'ap'
        return "lặp ký tự", collapsed
    fixed = suggest_spelling_fix(token, stats["vocab"])
    if fixed:
        return "sai chính tả", fixed
    return "ngoài từ điển", ""


def list_nonstandard_token_reviews(
    df: pd.DataFrame,
    stats: dict,
    content_col: str = CONTENT_COL,
) -> pd.DataFrame:
    """Bước 9+10, 18, 12, 11 — KHÔNG sửa câu: trả về các dòng có >= 1 token
    không phải tiếng Việt chuẩn (xem `classify_token`) để con người kiểm tra.
    Thêm `SOURCE_ROW_COL` ở đầu, và `SUSPECT_TOKENS_COL` + `TOKEN_DETAIL_COL`
    ngay sau `content_col`. `stats` = `build_token_stats` trên mọi file.
    Không có `content_col`: trả về df rỗng. Hàm thuần, giữ index gốc."""
    if content_col not in df.columns:
        return df.iloc[0:0].copy()
    cache: dict = {}

    def _scan(value) -> list:
        if pd.isna(value):
            return []
        found = []
        for tok in dict.fromkeys(w.lower() for w in _TOKEN_RE.findall(str(value))):
            if tok.isdigit():
                continue
            if tok not in cache:
                cache[tok] = classify_token(tok, stats)
            if cache[tok]:
                found.append((tok, *cache[tok]))
        return found

    found = df[content_col].map(_scan)
    has = found.map(bool)
    suspect = df.loc[has].copy()
    pos = suspect.columns.get_loc(content_col) + 1
    suspect.insert(pos, SUSPECT_TOKENS_COL, found[has].map(lambda f: ", ".join(t for t, _, _ in f)))
    suspect.insert(pos + 1, TOKEN_DETAIL_COL, found[has].map(
        lambda f: "; ".join(f"{t} -> {s} [{kind}]" if s else f"{t} [{kind}]" for t, kind, s in f)
    ))
    suspect.insert(0, SOURCE_ROW_COL, suspect.index + 2)
    return suspect


def vote_suggestion(sources: dict, decider: str | None = None) -> tuple[str, int]:
    """{nguồn: gợi ý ('' = không ý kiến)} -> (gợi ý nhiều phiếu nhất, số phiếu);
    hoà phiếu thì nguồn đứng trước trong `sources` thắng. Gợi ý của SOURCE_RULE
    dạng 'nhé / nhà' (teencode đa nghĩa) tính 1 phiếu cho mỗi ứng viên. Nếu
    `decider` có ý kiến thì gợi ý của nó thắng luôn (số phiếu = số nguồn trùng)."""
    votes: Counter = Counter()
    rank: dict = {}
    for i, (source, suggestion) in enumerate(sources.items()):
        for s in suggestion.split(" / ") if source == SOURCE_RULE else [suggestion]:
            if s:
                votes[s] += 1
                rank.setdefault(s, i)
    if not votes:
        return "", 0
    if sources.get(decider):
        return sources[decider], votes[sources[decider]]
    best = max(votes, key=lambda s: (votes[s], -rank[s]))
    return best, votes[best]


def _decider(kind: str) -> str | None:
    """Nhóm thiếu dấu: model dấu (theo ngữ cảnh) quyết định — luật/ViLexNorm
    không theo ngữ cảnh nên sai ở 'hình ảnh minh họa', 'giao qua'."""
    return SOURCE_ACCENT if kind == DIACRITIC_KIND else None


def _ordered_sources(kind: str, rule: str, token: str, context: dict) -> dict:
    """Nguồn theo thứ tự ưu tiên khi hoà phiếu: nhóm thiếu dấu tin model dấu
    (có ngữ cảnh) trước; còn lại tin luật/từ điển trước."""
    vilexnorm = load_vilexnorm_map().get(token)
    sources = {SOURCE_RULE: rule, SOURCE_VILEXNORM: vilexnorm.most_common(1)[0][0] if vilexnorm else "", **context}
    if kind == DIACRITIC_KIND and SOURCE_ACCENT in sources:
        sources = {SOURCE_ACCENT: sources.pop(SOURCE_ACCENT), **sources}
    return sources


def _row_decisions(suspect: pd.DataFrame, stats: dict, context_rows: dict) -> list:
    """Với mỗi dòng của `suspect`: [(token, loại, nguồn, gợi ý đồng thuận, số phiếu)]."""
    cache: dict = {}
    rows = []
    for i, tokens in enumerate(suspect[SUSPECT_TOKENS_COL]):
        row = []
        for tok in tokens.split(", "):
            if tok not in cache:
                cache[tok] = classify_token(tok, stats)
            kind, rule = cache[tok]
            context = {src: ctx[i].get(tok, "") for src, ctx in context_rows.items()}
            sources = _ordered_sources(kind, rule, tok, context)
            row.append((tok, kind, sources, *vote_suggestion(sources, _decider(kind))))
        rows.append(row)
    return rows


def annotate_suggestions(suspect: pd.DataFrame, stats: dict, context_rows: dict | None = None) -> pd.DataFrame:
    """Viết lại `TOKEN_DETAIL_COL` của 1 df từ `list_nonstandard_token_reviews`:
    'tok -> gợi ý đồng thuận [loại] (số phiếu/số nguồn có ý kiến: nguồn=gợi ý; ...)'.
    `context_rows` = {nguồn: [ {token: gợi ý} cho từng dòng của `suspect` ]} —
    gợi ý theo ngữ cảnh câu của các model. Hàm thuần, giữ index."""
    details = []
    for row in _row_decisions(suspect, stats, context_rows or {}):
        parts = []
        for tok, kind, sources, best, votes in row:
            opinions = "; ".join(f"{src}={sug}" for src, sug in sources.items() if sug)
            parts.append(f"{tok} -> {best} [{kind}] ({votes}/{sum(map(bool, sources.values()))}: {opinions})"
                         if best else f"{tok} [{kind}]")
        details.append(" | ".join(parts))
    result = suspect.copy()
    result[TOKEN_DETAIL_COL] = details
    return result


def row_replacements(
    suspect: pd.DataFrame,
    stats: dict,
    context_rows: dict | None = None,
    min_votes: int = MIN_VOTES,
    min_restorations: int = MIN_RESTORATIONS,
) -> list[dict]:
    """Với mỗi dòng của `suspect`: {token: từ thay} cho token có gợi ý đồng thuận
    khác chính nó, khác KEEP, đủ `min_votes` phiếu (cùng cách bỏ phiếu như
    `annotate_suggestions`, nên theo ngữ cảnh từng câu), không thuộc
    `NO_AUTO_REPLACE`. Phép chỉ thêm dấu ('hang' -> 'hàng') chỉ giữ khi dòng có
    >= `min_restorations` phép như vậy. Hàm thuần."""
    out = []
    for row in _row_decisions(suspect, stats, context_rows or {}):
        repl = {
            tok: best for tok, _, _, best, votes in row
            if best and best not in (KEEP, tok) and votes >= min_votes and tok not in NO_AUTO_REPLACE
        }
        restored = [t for t, new in repl.items() if _strip_diacritics(new.lower()) == t]
        if len(restored) < min_restorations:
            repl = {t: new for t, new in repl.items() if t not in restored}
        out.append(repl)
    return out


def apply_replacements(text: str, replacements: dict) -> tuple[str, dict]:
    """(câu mới, {token: từ thay đã áp}). Thay từng token (khớp không phân biệt
    hoa/thường, giữ kiểu hoa của token gốc) theo `replacements` {token lowercase:
    từ thay}; phần còn lại giữ nguyên. Không đổi thành 'không' khi token đứng
    ngay sau số ('200 k', '2 kg')."""
    applied: dict = {}

    def _sub(m: re.Match) -> str:
        tok = m.group().lower()
        new = replacements.get(tok)
        if not new or (new == "không" and re.search(r"\d\s*$", text[:m.start()])):
            return m.group()
        applied[tok] = new
        return _match_case(m.group(), new)

    return _TOKEN_RE.sub(_sub, text) if replacements else text, applied


def format_replaced(applied: dict) -> str:
    """'ko -> không; mn -> mọi người'."""
    return "; ".join(f"{t} -> {n}" for t, n in applied.items())


def criteria_columns(df: pd.DataFrame, content_col: str = CONTENT_COL) -> list[str]:
    """Các cột tiêu chí do T1.6 tách từ 'Tiêu chí đánh giá' (cột văn bản, trừ nội
    dung, cột gốc 'Tiêu chí đánh giá', emoji)."""
    skip = {content_col, CRITERIA_COL, EMOJIS_COL, EMOJI_SENTIMENT_COL}
    return [c for c in text_columns(df, content_col) if c not in skip]


def token_frequency_table(
    suspects: dict,
    stats: dict,
    contexts: dict | None = None,
    content_col: str = CONTENT_COL,
) -> pd.DataFrame:
    """Gộp các df của `list_nonstandard_token_reviews` ({tên file: df}) thành
    bảng 1 dòng / token: Token, Loại, Gợi ý đồng thuận + Số nguồn đồng ý, gợi ý
    của từng nguồn, Số lần (toàn dữ liệu), Số câu, File, Ví dụ (câu đầu tiên
    chứa token) — sắp xếp Số câu giảm dần, để duyệt cấp từ vựng rồi dựng file
    ánh xạ trong dictionary/. `contexts` = {tên file: context_rows của
    `annotate_suggestions`}: mỗi model lấy gợi ý xuất hiện nhiều nhất của token
    trên mọi câu để bỏ phiếu, cột ghi 3 lựa chọn nhiều nhất kèm số câu, vd
    'giữ nguyên (161), quá (38)' — từ phụ thuộc ngữ cảnh ('qua', 'con') phải
    xem phân bố này / Chi tiết token theo câu, không chỉ Gợi ý đồng thuận."""
    rows: dict = {}
    model_votes: dict = defaultdict(lambda: defaultdict(Counter))  # nguồn -> token -> Counter(gợi ý)
    for name, df in suspects.items():
        context_rows = (contexts or {}).get(name, {})
        for i, (tokens, text) in enumerate(zip(df[SUSPECT_TOKENS_COL], df[content_col])):
            for tok in tokens.split(", "):
                row = rows.setdefault(tok, {"Số câu": 0, "File": [], "Ví dụ": text})
                row["Số câu"] += 1
                if name not in row["File"]:
                    row["File"].append(name)
                for source, per_row in context_rows.items():
                    if per_row[i].get(tok):
                        model_votes[source][tok][per_row[i][tok]] += 1
    count_col = "Số lần (toàn dữ liệu)"
    records = []
    for tok, row in rows.items():
        kind, rule = classify_token(tok, stats)
        top = {src: votes[tok].most_common(1)[0] if votes.get(tok) else ("", 0) for src, votes in model_votes.items()}
        sources = _ordered_sources(kind, rule, tok, {src: s for src, (s, _) in top.items()})
        best, n_votes = vote_suggestion(sources, _decider(kind))
        record = {"Token": tok, "Loại": kind, CONSENSUS_COL: best, VOTES_COL: n_votes}
        for src, sug in sources.items():
            record[f"Gợi ý {src}"] = (
                ", ".join(f"{v} ({n})" for v, n in model_votes[src][tok].most_common(3)) if src in top else sug
            )
        record.update({count_col: stats["counts"][tok], "Số câu": row["Số câu"],
                       "File": ", ".join(row["File"]), "Ví dụ": row["Ví dụ"]})
        records.append(record)
    table = pd.DataFrame(records)
    tail = [count_col, "Số câu", "File", "Ví dụ"]
    table = table[[c for c in table.columns if c not in tail] + tail]
    return table.sort_values(["Số câu", count_col, "Token"], ascending=[False, False, True], ignore_index=True)


def mark_protected_tokens(df: pd.DataFrame, content_col: str = CONTENT_COL) -> pd.DataFrame:
    """Bước 18 — Đánh dấu token tiếng Anh/từ mượn cần bảo vệ ('ship', 'size',
    'pin', 'case', 'fullbox'...) vào cột `PROTECTED_TOKENS_COL` để
    `restore_diacritics` / `fix_spelling_errors` bỏ qua. TODO: implement."""
    raise NotImplementedError


def restore_diacritics(df: pd.DataFrame, content_col: str = CONTENT_COL) -> pd.DataFrame:
    """Bước 12 — Khôi phục dấu cho câu viết không dấu, bỏ qua protected
    tokens. TODO: implement (có thể cần model riêng)."""
    raise NotImplementedError


def normalize_emotional_slang(df: pd.DataFrame, content_col: str = CONTENT_COL) -> pd.DataFrame:
    """Bước 20 — Tiếng lóng cảm xúc ('xịn xò', 'phèn', 'đỉnh', 'keo'). KHÔNG
    thay bằng từ trung tính làm mất cường độ cảm xúc: ánh xạ sang từ chuẩn
    cùng sắc thái, hoặc giữ nguyên nếu đã phổ biến. TODO: implement (cần từ
    điển riêng trong dictionary/)."""
    raise NotImplementedError
