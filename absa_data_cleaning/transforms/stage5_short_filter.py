"""
transforms/stage5_short_filter.py
===================================
GIAI ĐOẠN 5 — LỌC REVIEW QUÁ NGẮN.

  16. Bước 6: review <= 4 từ — kiểm duyệt thủ công (`split_short_reviews`,
      taxonomy T2.11 + T2.12 -> Short_reviews.xlsx). Số từ chỉ đếm đúng SAU
      khi đã bỏ emoji, ký tự rác, ký tự lặp (Giai đoạn 4). Lọc TRƯỚC Giai đoạn
      6 để không tốn công sửa teencode cho review sẽ bị loại. Khi duyệt tay,
      giữ câu ngắn nhưng có khía cạnh rõ ("giao nhanh, pin trâu").

Checkpoint sau giai đoạn: v5_length_filtered.
"""

import pandas as pd

from transforms.stage1_structure import CONTENT_COL, CRITERIA_COL, _criteria_is_blank_series

# QUYẾT ĐỊNH THIẾT KẾ (thay cho heuristic gõ bừa/khớp stop-phrase cũ): thay vì
# tự động ĐOÁN và XOÁ review ngắn theo heuristic (dễ bắt nhầm/bỏ sót — vd
# heuristic cũ không có từ điển nên không phủ hết biến thể chính tả, và có
# nguy cơ xoá nhầm review ngắn nhưng hữu ích), MỌI review <= ngưỡng số từ dưới
# đây được TÁCH RIÊNG ra 1 nhóm để con người rà soát thủ công (xem
# `split_short_reviews`) — tránh lãng phí dữ liệu do máy quyết định sai.
SHORT_REVIEW_MAX_WORDS = 4


def is_short_review(text, max_words: int = SHORT_REVIEW_MAX_WORDS) -> bool:
    """T2.11 + T2.12 — True nếu `text` (sau khi strip khoảng trắng) có
    <= `max_words` từ (đếm bằng `str.split()` theo khoảng trắng).

    Chuỗi rỗng/toàn khoảng trắng/None trả về False (phạm vi T1.3, không phải
    T2.11/T2.12).
    """
    if text is None:
        return False
    stripped = str(text).strip()
    if not stripped:
        return False
    return len(stripped.split()) <= max_words


def split_short_reviews(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
    criteria_col: str = CRITERIA_COL,
    max_words: int = SHORT_REVIEW_MAX_WORDS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """T2.11 + T2.12 (ĐÃ ĐỔI CÁCH XỬ LÝ — không còn tự động XOÁ) — TÁCH dòng
    thành 2 nhóm (kept_df, short_df) thay vì xoá hẳn, để con người tự rà soát
    thủ công nhóm review ngắn thay vì để heuristic quyết định (tránh lãng phí
    dữ liệu do bắt nhầm/bỏ sót).

    Một dòng thuộc nhóm `short_df` khi CẢ 2 điều kiện sau ĐỒNG THỜI đúng:
      1. `content_col` ('Nội dung tự do'), sau khi strip khoảng trắng, có
         <= `max_words` từ — xem `is_short_review`.
      2. `criteria_col` ('Tiêu chí đánh giá') CŨNG rỗng (không có giá trị).

    Vì sao cần điều kiện 2: nhất quán với nguyên tắc T1.2+T1.3 (xem
    `stage1_structure.drop_empty_rows`) — 1 dòng chỉ thực sự cần tách riêng
    khi CẢ 2 trường bắt buộc đều rỗng/ngắn. Nếu `criteria_col` CÓ giá trị (vd
    'Pin: tốt') thì dòng vẫn hữu ích cho ABSA dù 'Nội dung tự do' ngắn -> GIỮ
    NGUYÊN trong `kept_df`, không tách.

    Dòng có nội dung rỗng/NaN hoàn toàn KHÔNG bị tách ở đây — đó là phạm vi
    của T1.3 (`stage1_structure.drop_empty_rows`), PHẢI chạy TRƯỚC bước này.

    Nếu `content_col` không tồn tại trong `df`: trả về (df.copy(), df rỗng
    cùng cột) — không đủ thông tin để tách. Nếu `criteria_col` không tồn tại:
    coi như rỗng ở mọi dòng (xem `_criteria_is_blank_series`).

    Hàm thuần: không sửa `df` gốc, không I/O. Giữ nguyên index gốc của các
    dòng ở cả 2 DataFrame trả về (để truy vết đúng số dòng qua
    core.diff_report / khi ghép nhiều file lại ở run_t212.py).
    """
    if content_col not in df.columns:
        return df.copy(), df.iloc[0:0].copy()

    content = df[content_col]
    content_is_short = content.apply(
        lambda value: False if pd.isna(value) else is_short_review(value, max_words)
    )
    criteria_blank = _criteria_is_blank_series(df, criteria_col)

    should_split = content_is_short & criteria_blank
    return df.loc[~should_split].copy(), df.loc[should_split].copy()
