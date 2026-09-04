"""
pipelines/pipeline_tang4.py
==============================
Lắp ráp thứ tự chạy các step thuộc Tầng 4 (nhất quán & khả năng sử dụng liên file).

LƯU Ý: đây là tầng DUY NHẤT cần dữ liệu của TẤT CẢ sản phẩm cùng lúc (xem
transforms/tang4_consistency.py) — khác cách gọi run_step theo từng product
riêng lẻ ở Tầng 1-3. core/pipeline.py cần hỗ trợ chế độ "cross-file step" khi
triển khai thật.

Thứ tự đề xuất:
    T4.51 filter_out_of_scope_products        (lọc phạm vi sản phẩm trước tiên)
 -> T4.52 filter_out_of_scope_language_reviews
 -> T4.45 detect_cross_file_duplicate
 -> T4.46 detect_review_under_multiple_products
 -> T4.48 flag_unidentifiable_product
 -> T4.49 flag_partial_crawl_errors
 -> T4.47 flag_review_metadata_conflict
 -> T4.50 drop_rows_missing_critical_info      (chạy sau cùng, có thể loại dòng)

TODO: implement run(), lưu ý xử lý dict[str, DataFrame] thay vì DataFrame đơn.
"""

from typing import Iterable

from core.pipeline import Pipeline

STEP_ORDER = [
    "T4.51", "T4.52",
    "T4.45", "T4.46",
    "T4.48", "T4.49",
    "T4.47",
    "T4.50",
]


def run(pipeline: Pipeline, products: Iterable[str]):
    raise NotImplementedError
