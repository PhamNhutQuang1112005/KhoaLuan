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

import pandas as pd

AUTHOR_COL = "Tác giả"
CONTENT_COL = "Nội dung tự do"
ANON_LABEL = "ẩn danh"


def fix_field_misalignment(
    df: pd.DataFrame,
    author_col: str = AUTHOR_COL,
    content_col: str = CONTENT_COL,
    anon_label: str = ANON_LABEL,
    min_words: int = 3,
) -> pd.DataFrame:
    """T1.1 — Phát hiện & sửa trường hợp nội dung review lọt sang cột 'Tác giả'
    (khi người dùng để trống tên hiển thị).

    Ví dụ thực tế đã ghi nhận: phone_2127 #1911 — 'Tác giả' chứa nội dung review
    thật, 'Nội dung tự do' rỗng.

    Heuristic (kiểm chứng trên 5 file: tên tác giả sạch gần như luôn là 1 token,
    dài <= 30 ký tự): một dòng bị lệch cột khi
      - 'Nội dung tự do' rỗng / NaN, VÀ
      - 'Tác giả' có >= `min_words` từ (giống câu review, không phải username).
    Với dòng khớp: chuyển giá trị 'Tác giả' sang 'Nội dung tự do', gán lại
    'Tác giả' = `anon_label`. Trên bộ dữ liệu hiện tại: 17 dòng, 0 dương tính giả.

    Hàm thuần: không sửa `df` gốc, không I/O.
    """
    if author_col not in df.columns or content_col not in df.columns:
        return df.copy()

    out = df.copy()
    author = out[author_col].astype("string")
    content = out[content_col].astype("string")

    content_empty = content.isna() | (content.str.strip() == "")
    author_is_review = author.str.split().str.len().ge(min_words)
    misaligned = content_empty & author_is_review & author.notna()

    out.loc[misaligned, content_col] = author[misaligned].str.strip()
    out.loc[misaligned, author_col] = anon_label
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
