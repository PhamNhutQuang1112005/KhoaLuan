"""
transforms/tang4_consistency.py
==================================
TẦNG 4 — TÍNH NHẤT QUÁN & KHẢ NĂNG SỬ DỤNG DỮ LIỆU (8 mục, T4.45 .. T4.52).

ĐIỂM KHÁC BIỆT quan trọng so với Tầng 1-3: các hàm ở đây thường cần nhìn xuyên
suốt NHIỀU FILE cùng lúc (liên sản phẩm), không chỉ 1 DataFrame của 1 sản phẩm.
Vì vậy chữ ký hàm ở tầng này nhận vào 1 dict[str, DataFrame] (khoá = tên sản phẩm)
thay vì 1 DataFrame đơn — cần phản ánh điều này trong core/step_base.py khi
triển khai thật (StepMeta nên có cờ `cross_file: bool`).
"""

import pandas as pd


def detect_cross_file_duplicate(dfs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """T4.45 — Phát hiện duplicate giữa các file (VD cùng 1 review xuất hiện ở
    cả ipad_1168 và phone_2127 do lỗi crawl). TODO: implement."""
    raise NotImplementedError


def detect_review_under_multiple_products(
    dfs: dict[str, pd.DataFrame]
) -> dict[str, pd.DataFrame]:
    """T4.46 — Phát hiện 1 review xuất hiện nhiều lần dưới các sản phẩm khác nhau.
    TODO: implement."""
    raise NotImplementedError


def flag_review_metadata_conflict(df: pd.DataFrame) -> pd.DataFrame:
    """T4.47 — Đánh dấu review và metadata mâu thuẫn (VD nội dung khen ngợi nhưng
    Số sao = 1). Đây là 1 trong 2 mục 'Nghiêm trọng' của tầng 4.
    TODO: implement — có thể chỉ cần rule đơn giản (sentiment lexicon thô) ở giai
    đoạn làm sạch, phân tích sâu hơn để dành cho bước gán nhãn.
    """
    raise NotImplementedError


def flag_unidentifiable_product(df: pd.DataFrame) -> pd.DataFrame:
    """T4.48 — Đánh dấu sản phẩm/biến thể không xác định được. TODO: implement."""
    raise NotImplementedError


def flag_partial_crawl_errors(df: pd.DataFrame) -> pd.DataFrame:
    """T4.49 — Đánh dấu dữ liệu bị crawl lỗi một phần (VD nội dung bị cắt cụt).
    TODO: implement."""
    raise NotImplementedError


def drop_rows_missing_critical_info(df: pd.DataFrame) -> pd.DataFrame:
    """T4.50 — Loại bản ghi bị thiếu thông tin quan trọng (VD vừa thiếu nội dung
    vừa thiếu rating). Mục 'Nghiêm trọng' thứ 2 của tầng 4. TODO: implement.
    """
    raise NotImplementedError


def filter_out_of_scope_products(
    dfs: dict[str, pd.DataFrame]
) -> dict[str, pd.DataFrame]:
    """T4.51 — Loại dữ liệu ngoài phạm vi 5 nhóm sản phẩm nghiên cứu
    (xem config.settings.RESEARCH_PRODUCT_SCOPE). TODO: implement."""
    raise NotImplementedError


def filter_out_of_scope_language_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """T4.52 — Loại review không thuộc ngôn ngữ/phạm vi nghiên cứu (ở mức tổng thể,
    khác T2.27 vốn chỉ đánh dấu ở mức nội dung). TODO: implement."""
    raise NotImplementedError
