"""
transforms/tang3_metadata.py
==============================
TẦNG 3 — LÀM SẠCH & CHUẨN HOÁ METADATA (12 mục theo taxonomy, T3.33 .. T3.44).

Khác với Tầng 2 (xử lý cột 'Nội dung tự do'), Tầng 3 xử lý các cột metadata:
'Loại hàng', 'Tiêu chí đánh giá', 'Số sao', 'Thời gian', 'Tác giả', 'URL sản phẩm'.
"""

import pandas as pd


def normalize_product_variant(df: pd.DataFrame) -> pd.DataFrame:
    """T3.33 — Chuẩn hoá 'Loại hàng' không nhất quán (vd viết hoa/thường, khoảng trắng).
    TODO: implement."""
    raise NotImplementedError


def normalize_product_name(df: pd.DataFrame) -> pd.DataFrame:
    """T3.34 — Chuẩn hoá tên sản phẩm không nhất quán. TODO: implement."""
    raise NotImplementedError


def normalize_variant_naming(df: pd.DataFrame) -> pd.DataFrame:
    """T3.35 — Chuẩn hoá tên biến thể sản phẩm không nhất quán. TODO: implement."""
    raise NotImplementedError


def normalize_rating_criteria(df: pd.DataFrame) -> pd.DataFrame:
    """T3.36 — Chuẩn hoá 'Tiêu chí đánh giá' không nhất quán (liên hệ T1.6 — cột
    này thường chứa nhiều tiêu chí gộp, cần tách trước rồi mới chuẩn hoá tên tiêu
    chí ở đây). TODO: implement.
    """
    raise NotImplementedError


def validate_rating_value(df: pd.DataFrame) -> pd.DataFrame:
    """T3.37 — Kiểm tra giá trị rating hợp lệ (khoảng 1-5, xem
    config.pipeline_config.yaml -> params.valid_range). TODO: implement."""
    raise NotImplementedError


def handle_missing_rating(df: pd.DataFrame) -> pd.DataFrame:
    """T3.38 — Xử lý giá trị rating bị thiếu (quyết định: loại dòng hay giữ lại
    với flag missing). TODO: implement."""
    raise NotImplementedError


def normalize_review_time_format(df: pd.DataFrame) -> pd.DataFrame:
    """T3.39 — Chuẩn hoá định dạng 'Thời gian' đánh giá (parse về datetime thống nhất).
    TODO: implement."""
    raise NotImplementedError


def flag_anomalous_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """T3.40 — Đánh dấu timestamp trùng hoặc bất thường (VD nhiều review cùng 1
    timestamp chính xác đến giây, hoặc thời gian nằm ngoài khoảng crawl hợp lý).
    TODO: implement."""
    raise NotImplementedError


def validate_username(df: pd.DataFrame) -> pd.DataFrame:
    """T3.41 — Kiểm tra username không hợp lệ/bị thiếu (liên hệ T1.1 — sau khi đã
    tách lại nội dung lệch cột, dòng còn thiếu Tác giả thật sự được gán 'ẩn danh').
    TODO: implement."""
    raise NotImplementedError


def validate_product_url(df: pd.DataFrame) -> pd.DataFrame:
    """T3.42 — Kiểm tra URL sản phẩm bị thiếu hoặc sai định dạng. TODO: implement."""
    raise NotImplementedError


def unify_product_naming_across_records(df: pd.DataFrame) -> pd.DataFrame:
    """T3.43 — Gộp các cách ghi tên khác nhau của cùng 1 sản phẩm về 1 tên chuẩn
    (cần bảng ánh xạ tên biến thể -> tên chuẩn, xây riêng ngoài code). TODO: implement."""
    raise NotImplementedError


def flag_mismatched_product_assignment(df: pd.DataFrame) -> pd.DataFrame:
    """T3.44 — Đánh dấu review bị gắn sai sản phẩm/biến thể (đối chiếu nội dung
    review với 'Loại hàng' khai báo — có thể cần rule đơn giản hoặc để dành cho
    bước Human Verification theo kế hoạch luận văn). TODO: implement."""
    raise NotImplementedError
