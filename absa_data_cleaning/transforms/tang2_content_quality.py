"""
transforms/tang2_content_quality.py
=====================================
TẦNG 2 — CHẤT LƯỢNG & NHIỄU CỦA NỘI DUNG REVIEW (24 mục theo taxonomy).

Chia 3 nhóm con (giữ nguyên theo taxonomy để dễ đối chiếu):
  2.1 Nội dung không có giá trị      (T2.9  .. T2.16) — T2.9+T2.10 ĐÃ GỘP
      CHUNG thành `drop_emoji_or_special_char_only_reviews` (cùng 1 tiêu chí
      "nội dung chỉ toàn emoji/ký tự đặc biệt, không mang thông tin").
  2.2 Nhiễu biểu diễn                 (T2.17 .. T2.27)
  2.3 Nội dung cần giữ lại, KHÔNG xoá (T2.28 .. T2.32)

LƯU Ý QUAN TRỌNG cho nhóm 2.3: các hàm trong nhóm này không phải hàm "làm sạch"
theo nghĩa loại bỏ, mà là hàm NHẬN DIỆN/ĐÁNH DẤU để đảm bảo các bước ở nhóm 2.1/2.2
không vô tình xoá mất tín hiệu cảm xúc quan trọng (phủ định, nhấn mạnh, tiếng lóng...).
Cân nhắc thiết kế: mỗi hàm 2.3 trả về DataFrame có thêm cột cờ đánh dấu (flag),
không xoá dữ liệu.
"""

import pandas as pd

from transforms.utils_text import is_emoji_or_special_char_only

CONTENT_COL = "Nội dung tự do"


# --- 2.1 Nội dung không có giá trị ------------------------------------------

def drop_emoji_or_special_char_only_reviews(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
) -> pd.DataFrame:
    """T2.9 + T2.10 (GỘP CHUNG) — Xoá HẲN dòng nếu `content_col` ('Nội dung
    tự do'), sau khi strip khoảng trắng, CHỈ gồm emoji và/hoặc ký tự đặc biệt
    (không có bất kỳ chữ/số nào mang thông tin) — dùng
    `utils_text.is_emoji_or_special_char_only`.

    Vì sao gộp T2.9 (chỉ emoji) và T2.10 (chỉ ký tự đặc biệt) làm 1: cả 2 cùng
    chung 1 tiêu chí "nội dung không mang giá trị thông tin gì cho ABSA" —
    khác biệt duy nhất là LOẠI ký tự (emoji hay dấu câu/ký hiệu), còn quyết
    định xử lý (xoá dòng) là NHƯ NHAU; nội dung trộn lẫn cả 2 loại (vd
    '!!! 😊') cũng bị xoá, không cần tách riêng 2 lượt quét cho cùng 1 dòng
    (giống cách T1.2 gộp với T1.3 ở transforms/tang1_structural.py).

    Dòng có nội dung rỗng/NaN hoàn toàn KHÔNG bị xoá ở đây (không phải "chỉ
    emoji/ký tự đặc biệt" — đơn giản là không có nội dung) — đó là phạm vi
    của T1.3 (`tang1_structural.drop_empty_rows`), PHẢI chạy TRƯỚC bước này.

    Nếu `content_col` không tồn tại trong `df`: trả về bản sao nguyên vẹn,
    không xoá dòng nào (không đủ thông tin để đánh giá).

    Hàm thuần: không sửa `df` gốc, không I/O. Giữ nguyên index gốc của các
    dòng còn lại (để truy vết đúng số dòng đã xoá qua core.diff_report).
    """
    if content_col not in df.columns:
        return df.copy()

    content = df[content_col]
    only_noise = content.apply(
        lambda value: False if pd.isna(value) else is_emoji_or_special_char_only(value)
    )
    return df.loc[~only_noise].copy()


def flag_meaningless_short_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """T2.11 — Review chỉ có vài ký tự vô nghĩa. TODO: implement."""
    raise NotImplementedError


def flag_uninformative_short_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """T2.12 — Review quá ngắn nhưng không chứa thông tin hữu ích.
    Khác T2.11: ở đây review có thể là câu hoàn chỉnh nhưng không mang thông tin
    (VD chỉ 'ok', 'tốt'). TODO: implement, cân nhắc ngưỡng số từ + danh sách stop-phrase.
    """
    raise NotImplementedError


def flag_url_or_ads_only_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """T2.13 — Review chỉ chứa URL/quảng cáo. TODO: implement (dùng utils_text.contains_url)."""
    raise NotImplementedError


def flag_spam_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """T2.14 — Review spam (lặp mẫu, quảng cáo shop khác...). TODO: implement."""
    raise NotImplementedError


def drop_exact_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """T2.15 — Loại review trùng lặp hoàn toàn (trong cùng 1 file/sản phẩm).
    TODO: implement (dựa trên cột 'Nội dung tự do' + có thể + 'Tác giả').
    """
    raise NotImplementedError


def flag_near_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """T2.16 — Đánh dấu review gần trùng lặp (near-duplicate), dùng ngưỡng
    similarity_threshold (xem config/settings.py, config/pipeline_config.yaml).
    TODO: implement (dùng utils_text.text_similarity).
    """
    raise NotImplementedError


# --- 2.2 Nhiễu biểu diễn ------------------------------------------------------

def normalize_teencode(df: pd.DataFrame) -> pd.DataFrame:
    """T2.17 — Chuẩn hoá teencode (vd 'ko' -> 'không'). TODO: implement,
    cần từ điển teencode -> chuẩn (xây riêng, không hardcode trong hàm)."""
    raise NotImplementedError


def expand_abbreviations(df: pd.DataFrame) -> pd.DataFrame:
    """T2.18 — Mở rộng từ viết tắt. TODO: implement."""
    raise NotImplementedError


def fix_spelling_errors(df: pd.DataFrame) -> pd.DataFrame:
    """T2.19 — Sửa lỗi chính tả. TODO: implement (cân nhắc dùng thư viện/spellchecker
    tiếng Việt, hoặc để lại cho annotation guideline xử lý thủ công nếu quá phức tạp)."""
    raise NotImplementedError


def restore_diacritics(df: pd.DataFrame) -> pd.DataFrame:
    """T2.20 — Xử lý review viết không dấu. TODO: implement (bài toán thêm dấu
    tiếng Việt — có thể cần model riêng, đánh giá độ ưu tiên trước khi làm)."""
    raise NotImplementedError


def normalize_repeated_characters(df: pd.DataFrame) -> pd.DataFrame:
    """T2.21 — Chuẩn hoá lặp ký tự kéo dài (vd 'đẹppppp' -> 'đẹp'). TODO: implement."""
    raise NotImplementedError


def handle_inline_emoji(df: pd.DataFrame) -> pd.DataFrame:
    """T2.22 — Xử lý emoji/emoticon xen giữa câu (chuẩn hoá vị trí/tách khỏi từ,
    KHÔNG xoá — xem thêm T2.32 ở nhóm 2.3). TODO: implement."""
    raise NotImplementedError


def remove_meaningless_special_chars(df: pd.DataFrame) -> pd.DataFrame:
    """T2.23 — Loại ký tự đặc biệt không mang ý nghĩa. TODO: implement."""
    raise NotImplementedError


def strip_extra_whitespace(df: pd.DataFrame) -> pd.DataFrame:
    """T2.24 — Khoảng trắng thừa/nhiều khoảng trắng liên tiếp.
    TODO: implement (dùng utils_text.strip_extra_whitespace)."""
    raise NotImplementedError


def normalize_casing(df: pd.DataFrame) -> pd.DataFrame:
    """T2.25 — Chuẩn hoá chữ hoa/chữ thường không nhất quán. TODO: implement,
    cân nhắc KHÔNG lowercase toàn bộ nếu viết hoa mang tín hiệu cảm xúc (liên hệ T2.30)."""
    raise NotImplementedError


def flag_code_switching(df: pd.DataFrame) -> pd.DataFrame:
    """T2.26 — Đánh dấu review có tiếng Anh xen tiếng Việt (code-switching).
    TODO: implement — quyết định giữ hay dịch, ghi rõ trong annotation guideline."""
    raise NotImplementedError


def flag_out_of_scope_language(df: pd.DataFrame) -> pd.DataFrame:
    """T2.27 — Đánh dấu/loại review bằng ngôn ngữ ngoài phạm vi nghiên cứu
    (xem config.settings.ALLOWED_LANGUAGES). TODO: implement (dùng language detection)."""
    raise NotImplementedError


# --- 2.3 Nội dung cần giữ lại — KHÔNG được xoá -------------------------------
# Các hàm dưới đây chỉ ĐÁNH DẤU (thêm cột flag), không xoá dữ liệu.

def flag_negation_words(df: pd.DataFrame) -> pd.DataFrame:
    """T2.28 — Đánh dấu review chứa từ phủ định ('không', 'chẳng', 'đâu có'...).
    TODO: implement."""
    raise NotImplementedError


def flag_intensifiers(df: pd.DataFrame) -> pd.DataFrame:
    """T2.29 — Đánh dấu từ nhấn mạnh ('rất', 'cực kỳ', 'siêu'...). TODO: implement."""
    raise NotImplementedError


def flag_exclamatory_sentences(df: pd.DataFrame) -> pd.DataFrame:
    """T2.30 — Đánh dấu câu cảm thán. TODO: implement."""
    raise NotImplementedError


def flag_meaningful_slang(df: pd.DataFrame) -> pd.DataFrame:
    """T2.31 — Đánh dấu tiếng lóng có ý nghĩa cảm xúc (cần từ điển riêng,
    KHÁC với teencode ở T2.17 vốn chỉ là biến thể chính tả). TODO: implement."""
    raise NotImplementedError


def flag_expressive_emoji(df: pd.DataFrame) -> pd.DataFrame:
    """T2.32 — Đánh dấu emoji có giá trị biểu đạt cảm xúc (không xoá ở bước làm sạch,
    dành cho bước gán nhãn/aspect sau này quyết định dùng hay không). TODO: implement."""
    raise NotImplementedError
