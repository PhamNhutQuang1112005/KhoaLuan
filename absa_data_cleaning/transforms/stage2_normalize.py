"""
transforms/stage2_normalize.py
================================
GIAI ĐOẠN 2 — CHUẨN HOÁ NỀN AN TOÀN (tự động).

  5. `normalize_unicode_and_html` — (bổ sung) chuẩn hoá Unicode về NFC, thống
     nhất vị trí dấu thanh ('hoà'/'hòa', 'thuỷ'/'thủy'), loại thẻ HTML. Bỏ qua
     bước này thì 2 chuỗi trông giống hệt vẫn bị coi là khác -> hỏng mọi bước
     so khớp phía sau.
  6. `strip_extra_whitespace`     — Bước 16: khoảng trắng thừa (lượt 1).
     Lượt 2 ở Giai đoạn 4, lượt 3 ở kiểm tra cuối (Giai đoạn 7).
  7. `add_text_norm_column`       — Bước 17: tạo cột làm việc `text_norm` viết
     thường để so khớp từ điển, GIỮ NGUYÊN bản gốc. (Hạ chữ thường trong dữ
     liệu huấn luyện cuối cùng là quyết định riêng — ablation, vì PhoBERT
     phân biệt hoa thường.)

Đầu vào = đầu ra Giai đoạn 1 (v1_structured). Bước 5 và 6 áp lên MỌI cột văn
bản tự do: `content_col`, cột gốc 'Tiêu chí đánh giá' và các cột tiêu chí đã
tách ở T1.6 (`split_merged_fields`) — xem `text_columns`. Không đụng
review_raw, tác giả, URL, thời gian... `text_norm` chỉ lấy từ `content_col`.

Checkpoint sau giai đoạn: v2_normalized.
"""

import pandas as pd

from config.settings import STANDARD_SCHEMA
from transforms import utils_text
from transforms.stage0_prepare import REVIEW_ID_COL, REVIEW_RAW_COL
from transforms.stage1_structure import CONTENT_COL, CRITERIA_COL, MOVED_CRITERIA_COL

TEXT_NORM_COL = "text_norm"

# Cột KHÔNG phải văn bản review: schema gốc (trừ 2 cột chữ bên dưới), cột phụ
# của GĐ0/GĐ1/GĐ2. Mọi cột còn lại trong df = cột tiêu chí do T1.6 tách ra.
_NON_TEXT_COLS = (
    set(STANDARD_SCHEMA) | {REVIEW_ID_COL, REVIEW_RAW_COL, MOVED_CRITERIA_COL, TEXT_NORM_COL}
) - {CONTENT_COL, CRITERIA_COL}


def text_columns(df: pd.DataFrame, content_col: str = CONTENT_COL) -> list[str]:
    """Các cột văn bản cần chuẩn hoá có mặt trong `df`: `content_col`, cột
    'Tiêu chí đánh giá' gốc, và mọi cột tiêu chí đã tách ở T1.6 (cột không
    thuộc schema gốc / cột phụ)."""
    non_text = _NON_TEXT_COLS - {content_col}
    return [c for c in df.columns if c == content_col or c not in non_text]


def _map_text(df: pd.DataFrame, fn, cols: list[str]) -> pd.DataFrame:
    """Áp `fn(str) -> str` lên các ô chuỗi của `cols`; ô NA / không phải chuỗi
    giữ nguyên, kết quả rỗng thành `pd.NA` (nhất quán với T1.2+T1.3)."""
    out = df.copy()
    for col in cols:
        s = out[col]

        def _apply(v):
            if not isinstance(v, str):
                return v
            r = fn(v)
            return r if r.strip() else pd.NA

        out[col] = s.map(_apply).astype(s.dtype)
    return out


def normalize_unicode_and_html(df: pd.DataFrame, content_col: str = CONTENT_COL) -> pd.DataFrame:
    """Bước 5 — NFC + thống nhất vị trí dấu thanh + bỏ thẻ HTML trên
    `content_col` và các cột tiêu chí đã tách (dùng `utils_text.normalize_unicode`)."""
    return _map_text(df, utils_text.normalize_unicode, text_columns(df, content_col))


def strip_extra_whitespace(df: pd.DataFrame, content_col: str = CONTENT_COL) -> pd.DataFrame:
    """Bước 16 — Khoảng trắng thừa/nhiều khoảng trắng liên tiếp, trên
    `content_col` và các cột tiêu chí đã tách (dùng
    `utils_text.strip_extra_whitespace`). Gọi lại ở Giai đoạn 4 và kiểm tra cuối."""
    return _map_text(df, utils_text.strip_extra_whitespace, text_columns(df, content_col))


def add_text_norm_column(df: pd.DataFrame, content_col: str = CONTENT_COL) -> pd.DataFrame:
    """Bước 17 — Thêm cột `TEXT_NORM_COL` = `content_col` viết thường, dùng để
    so khớp từ điển / exact-duplicate. KHÔNG sửa `content_col`. Đặt ngay sau
    `content_col`; nếu cột đã có thì tính lại (idempotent)."""
    out = df.copy()
    norm = (
        out[content_col].astype("string").str.lower()
        if content_col in out.columns
        else pd.Series(pd.NA, index=out.index, dtype="string")
    )
    if TEXT_NORM_COL in out.columns:
        out[TEXT_NORM_COL] = norm
    else:
        pos = out.columns.get_loc(content_col) + 1 if content_col in out.columns else len(out.columns)
        out.insert(pos, TEXT_NORM_COL, norm)
    return out
