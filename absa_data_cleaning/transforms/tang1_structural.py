"""
transforms/tang1_structural.py
================================
TẦNG 1 — LỖI CẤU TRÚC DỮ LIỆU (8 mục theo taxonomy).

Mỗi hàm dưới đây là 1 HÀM THUẦN: nhận vào pd.DataFrame, trả về pd.DataFrame mới
(không sửa inplace, không side-effect I/O). Khi triển khai thật, gắn decorator
`@register_step(...)` từ core.registry lên từng hàm để hệ thống nhận diện.

Danh sách 8 mục (mã taxonomy T1.1 .. T1.8):
  T1.1  Sai / lệch cột dữ liệu (Field Misalignment)          — Nghiêm trọng
  T1.2  Thiếu cột bắt buộc                                    — Thấp
  T1.3  Dòng trống / bản ghi rỗng hoàn toàn                    — Nghiêm trọng
  T1.4  Giá trị NULL / NaN / None                              — Trung bình
  T1.5  Sai kiểu dữ liệu (Data Type)                           — Trung bình
  T1.6  Dữ liệu bị dồn nhiều trường vào một ô                   — Nghiêm trọng
  T1.7  Ký tự xuống dòng / tab làm phá cấu trúc trường          — Trung bình
  T1.8  Encoding lỗi / ký tự bị lỗi (mojibake)                  — Thấp
"""

import re

import pandas as pd

AUTHOR_COL = "Tác giả"
CONTENT_COL = "Nội dung tự do"
ANON_LABEL = "ẩn danh"

_VIETNAMESE_DIACRITIC_RE = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]",
    re.IGNORECASE,
)


def fix_field_misalignment(
    df: pd.DataFrame,
    author_col: str = AUTHOR_COL,
    content_col: str = CONTENT_COL,
    anon_label: str = ANON_LABEL,
    min_words: int = 2,
) -> pd.DataFrame:
    """T1.1 — Phát hiện & sửa trường hợp nội dung review lọt sang cột 'Tác giả'
    (khi người dùng để trống tên hiển thị).

    Ví dụ thực tế đã ghi nhận: phone #1911 — 'Tác giả' chứa nội dung review
    thật, 'Nội dung tự do' rỗng.

    Heuristic (kiểm chứng trên toàn bộ 10 file hiện có trong data/raw/):
    username thật trên các sàn TMĐT này luôn là 1 token thuần ASCII/số/gạch
    dưới (vd 'ha_lucsi', 'a*****9'), không bao giờ chứa dấu tiếng Việt.
    'Tác giả' được coi là chứa nội dung review (bị lệch cột) khi:
      - có >= `min_words` từ (giống câu review, không phải username), HOẶC
      - chỉ 1 token nhưng có chứa dấu tiếng Việt (vd 'đẹp' — không có username
        thật nào trong dữ liệu chứa dấu).
    Trường hợp 1 token, không dấu, không đạt `min_words` (vd 'ok') được coi là
    mơ hồ và CỐ TÌNH bỏ qua để tránh sửa nhầm username thật.

    Khi khớp:
      - Nếu 'Nội dung tự do' đang rỗng: chuyển hẳn nội dung 'Tác giả' sang đó.
      - Nếu 'Nội dung tự do' đã có sẵn nội dung (cả 2 cột cùng bị lệch, vd
        buds #766, watch #789): nối 'Tác giả' vào TRƯỚC nội dung sẵn có, cách
        nhau bằng '\\n'.
      Sau đó gán lại 'Tác giả' = `anon_label`.

    Hàm thuần: không sửa `df` gốc, không I/O.
    """
    if author_col not in df.columns or content_col not in df.columns:
        return df.copy()

    out = df.copy()
    author = out[author_col].astype("string")
    content = out[content_col].astype("string")

    author_stripped = author.str.strip()
    word_count = author_stripped.str.split().str.len()
    has_diacritics = author_stripped.str.contains(_VIETNAMESE_DIACRITIC_RE, na=False)
    author_is_review = author.notna() & (word_count.ge(min_words) | has_diacritics)

    content_empty = content.isna() | (content.str.strip() == "")
    misaligned_empty = author_is_review & content_empty
    misaligned_filled = author_is_review & ~content_empty

    out.loc[misaligned_empty, content_col] = author_stripped[misaligned_empty]
    out.loc[misaligned_filled, content_col] = (
        author_stripped[misaligned_filled] + "\n" + content[misaligned_filled].str.strip()
    )
    out.loc[author_is_review, author_col] = anon_label
    return out


def validate_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    """T1.2 — Kiểm tra đủ 8 cột bắt buộc. Ghi nhận: hiện tại (5 file đã kiểm tra)
    CHƯA phát sinh lỗi này, nhưng cần giữ làm bước validate bắt buộc mỗi lần
    crawl thêm ngành hàng mới.

    TODO: implement — raise lỗi rõ ràng (không âm thầm bỏ qua) nếu thiếu cột.
    """
    raise NotImplementedError


def drop_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    """T1.3 — Loại bỏ dòng trống / bản ghi rỗng hoàn toàn.

    TODO: implement.
    """
    raise NotImplementedError


def handle_null_values(df: pd.DataFrame) -> pd.DataFrame:
    """T1.4 — Chuẩn hoá giá trị NULL/NaN/None (quyết định: giữ None hay điền
    giá trị mặc định tuỳ cột — vd 'Tiêu chí đánh giá' có thể hợp lệ khi rỗng).

    TODO: implement, cần quyết định chính sách theo từng cột.
    """
    raise NotImplementedError


def fix_data_types(df: pd.DataFrame) -> pd.DataFrame:
    """T1.5 — Ép kiểu dữ liệu đúng (VD: Số sao -> numeric, Thời gian -> datetime).

    TODO: implement.
    """
    raise NotImplementedError


def split_merged_fields(df: pd.DataFrame) -> pd.DataFrame:
    """T1.6 — Tách trường hợp nhiều trường bị dồn vào 1 ô (VD 'Tiêu chí đánh giá'
    chứa nhiều tiêu chí phân tách bằng '\\n' như 'Hiệu suất: mượt\\nThiết kế: oki').

    Lưu ý: đây là hiện tượng THẤY RÕ trong dữ liệu mẫu (cột 'Tiêu chí đánh giá'
    của phone_2127) — cần xử lý trước khi tách theo từng khía cạnh (aspect) sau này.

    TODO: implement.
    """
    raise NotImplementedError


def normalize_line_breaks(df: pd.DataFrame) -> pd.DataFrame:
    """T1.7 — Xử lý ký tự xuống dòng/tab phá cấu trúc trường (khác với T1.6:
    ở đây là newline làm hỏng định dạng ô Excel, không nhất thiết mang nghĩa
    "nhiều trường trong 1 ô").

    TODO: implement.
    """
    raise NotImplementedError


def fix_encoding_issues(df: pd.DataFrame) -> pd.DataFrame:
    """T1.8 — Phát hiện & sửa lỗi encoding (mojibake).

    TODO: implement.
    """
    raise NotImplementedError
