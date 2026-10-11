"""
transforms/stage4_char_noise.py
=================================
GIAI ĐOẠN 4 — LÀM SẠCH NHIỄU KÝ TỰ TRONG CÂU. Thứ tự:

  12. Bước 14 `handle_inline_emoji`              — emoji xen giữa câu.
  13. Bước 15 `remove_meaningless_special_chars` — ký tự đặc biệt vô nghĩa.
  14. Bước 13 `normalize_repeated_characters`    — lặp ký tự ('đẹppppp', '!!!!!').
      Sau 14 & 15 (emoji, ký tự đặc biệt cũng hay lặp), TRƯỚC teencode
      ('khôngggg' phải rút gọn mới khớp từ điển).
  15. Bước 16 — khoảng trắng lượt 2: gọi lại
      `stage2_normalize.strip_extra_whitespace`. Đầu vào của stage 4 là đầu ra
      của stage 3.
  (+) Bước 17 — làm mới `text_norm` (content đã đổi sau các bước trên).

Mỗi bước 14/15/13 có file suspect đi kèm: `changed_rows(before, after)` liệt kê
dòng bị đổi (nội dung gốc + `CLEANED_CONTENT_COL`) để người kiểm duyệt đối
chiếu; dữ liệu vẫn đi tiếp bản đã làm sạch, sửa nhầm thì merge lại theo review_id.

Checkpoint sau giai đoạn: v4_char_cleaned.
"""

import re
import unicodedata

import pandas as pd

from dataio.dictionary_loader import load_emoji_dict
from transforms.stage1_structure import CONTENT_COL
from transforms.stage2_normalize import _map_text
from transforms.utils_text import _EMOJI_CHAR_RE

EMOJIS_COL = "emojis"
EMOJI_SENTIMENT_COL = "emoji_sentiment"
CLEANED_CONTENT_COL = "Nội dung đã làm sạch"

# Từ có chữ lặp hợp lệ — không được rút gọn ở `normalize_repeated_characters`.
REPEATED_CHAR_WHITELIST = {"good", "free", "xoong"}

# Dấu câu còn mang nghĩa; mọi ký tự khác không phải chữ/số/khoảng trắng/dấu
# kết hợp/ký hiệu tiền tệ bị coi là rác ở `remove_meaningless_special_chars`.
_MEANINGFUL_PUNCT = set(".,!?:;'\"()-/%+&@#$=*…")

_EMOJI_RUN_RE = re.compile(_EMOJI_CHAR_RE.pattern + "+")
_LETTER_RUN_RE = re.compile(r"([^\W\d_])\1{2,}", re.IGNORECASE)
_PUNCT_RUN_RE = re.compile(r"([!?,:;\-*=+/])\1+")
_DOT_RUN_RE = re.compile(r"\.{3,}")
_WORD_RE = re.compile(r"\w+")


# Ký tự bổ nghĩa đi kèm emoji (VS16, ZWJ, keycap, màu da, giới tính) — bỏ qua khi tra từ điển.
_EMOJI_MODIFIERS = set("\ufe0f\u200d\u20e3\u2640\u2642") | {chr(c) for c in range(0x1F3FB, 0x1F400)}


def _emoji_units(run: str) -> list:
    """Tách 1 chuỗi emoji liền nhau thành các đơn vị (cờ = 2 ký tự ghép lại)."""
    chars = [c for c in run if c not in _EMOJI_MODIFIERS]
    units, i = [], 0
    while i < len(chars):
        if 0x1F1E6 <= ord(chars[i]) <= 0x1F1FF and i + 1 < len(chars):
            units.append(chars[i] + chars[i + 1])
            i += 2
        else:
            units.append(chars[i])
            i += 1
    return units


def _run_to_words(run: str, emo: dict) -> str:
    """Emoji -> nghĩa nối '_' (vd 'rất_thích'); emoji liền nhau cùng nghĩa chỉ giữ 1; chưa biết -> bỏ."""
    words = []
    for u in _emoji_units(run):
        if u in emo and (not words or words[-1] != emo[u][0]):
            words.append(emo[u][0])
    return f" {' '.join(words)} " if words else " "


def _row_sentiment(runs: list, emo: dict):
    sents = [emo[u][1] for r in runs for u in _emoji_units(r) if u in emo]
    if not sents:
        return pd.NA
    score = sents.count("pos") - sents.count("neg")
    return "pos" if score > 0 else "neg" if score < 0 else "neu"


def handle_inline_emoji(df: pd.DataFrame, content_col: str = CONTENT_COL) -> pd.DataFrame:
    """Bước 14 — Emoji giữ tín hiệu cảm xúc, KHÔNG xoá hẳn:
      - thay tại chỗ trong `content_col` bằng nghĩa tiếng Việt nối '_' theo
        `dictionary/emoji_meaning.txt` ('đẹp 😍' -> 'đẹp  rất_thích', dọn khoảng
        trắng ở bước 16 lượt 2); emoji chưa có trong từ điển chỉ bị bỏ khỏi câu;
      - `EMOJIS_COL`: các emoji gốc theo thứ tự xuất hiện (NA nếu không có);
      - `EMOJI_SENTIMENT_COL`: pos/neg/neu theo đa số emoji đã biết (NA nếu không có).
    """
    emo = load_emoji_dict()
    out = _map_text(df, lambda s: _EMOJI_RUN_RE.sub(lambda m: _run_to_words(m.group(), emo), s), [content_col])
    runs = df[content_col].map(lambda v: _EMOJI_RUN_RE.findall(v) if isinstance(v, str) else [])
    new_cols = {
        EMOJIS_COL: runs.map(lambda r: "".join(r) or pd.NA),
        EMOJI_SENTIMENT_COL: runs.map(lambda r: _row_sentiment(r, emo)),
    }
    pos = out.columns.get_loc(content_col) + 1
    for name, values in new_cols.items():
        if name in out.columns:
            out[name] = values
        else:
            out.insert(pos, name, values)
            pos += 1
    return out


def unknown_emojis(df: pd.DataFrame, content_col: str = CONTENT_COL) -> pd.Series:
    """Đếm emoji trong `content_col` CHƯA có trong từ điển (index = emoji), để bổ sung."""
    emo = load_emoji_dict()
    units = [
        u for v in df[content_col].dropna().astype(str)
        for r in _EMOJI_RUN_RE.findall(v) for u in _emoji_units(r) if u not in emo
    ]
    return pd.Series(units, dtype="object").value_counts()


_GLUE = "\x00"  # '_' nối 2 chữ (vd 'rất_thích' từ emoji) được giữ qua bước lọc
_GLUED_UNDERSCORE_RE = re.compile(r"(?<=[^\W_])_(?=[^\W_])")


def _keep_char(c: str) -> bool:
    return (
        c == _GLUE or c.isalnum() or c.isspace() or c in _MEANINGFUL_PUNCT
        or unicodedata.category(c) in ("Sc", "Mn", "Mc", "Me")
    )


def _drop_special(s: str) -> str:
    s = _GLUED_UNDERSCORE_RE.sub(_GLUE, s)
    return "".join(c if _keep_char(c) else " " for c in s).replace(_GLUE, "_")


def remove_meaningless_special_chars(df: pd.DataFrame, content_col: str = CONTENT_COL) -> pd.DataFrame:
    """Bước 15 — Thay ký tự đặc biệt vô nghĩa ('~', '^', '|', '[]', '•'...)
    bằng khoảng trắng; giữ chữ, số, dấu câu có nghĩa (`_MEANINGFUL_PUNCT`) và
    ký hiệu tiền tệ. Ô chỉ còn rác -> NA."""
    return _map_text(df, _drop_special, [content_col])


def _collapse_word(m: re.Match, whitelist: set) -> str:
    w = m.group()
    if w.lower() in whitelist:
        return w
    two = _LETTER_RUN_RE.sub(lambda r: r.group(1) * 2, w)  # 'gooood' -> 'good'
    return two if two.lower() in whitelist else _LETTER_RUN_RE.sub(r"\1", w)


def normalize_repeated_characters(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
    whitelist: set = REPEATED_CHAR_WHITELIST,
) -> pd.DataFrame:
    """Bước 13 — Rút gọn ký tự lặp kéo dài: chữ lặp >= 3 lần -> 1 ('đẹppppp' ->
    'đẹp'; chữ số không đụng, '1000000' giữ nguyên), bỏ qua từ trong
    `whitelist`; '!!!!!' -> '!', '....' -> '...'. Chữ lặp đúng 2 lần
    ('đẹpp') là mơ hồ nên giữ nguyên."""

    def fn(s: str) -> str:
        s = _WORD_RE.sub(lambda m: _collapse_word(m, whitelist), s)
        return _DOT_RUN_RE.sub("...", _PUNCT_RUN_RE.sub(r"\1", s))

    return _map_text(df, fn, [content_col])


def changed_rows(before: pd.DataFrame, after: pd.DataFrame, content_col: str = CONTENT_COL) -> pd.DataFrame:
    """File suspect cho bước 14/15/13: các dòng mà `content_col` bị đổi, lấy
    từ `before` (nội dung gốc) + cột `CLEANED_CONTENT_COL` (bản sau xử lý)
    ngay sau `content_col`. Giữ index gốc."""
    b, a = before[content_col], after[content_col].reindex(before.index)
    changed = b.astype(object).fillna("") != a.astype(object).fillna("")
    out = before.loc[changed].copy()
    out.insert(out.columns.get_loc(content_col) + 1, CLEANED_CONTENT_COL, a[changed])
    return out
