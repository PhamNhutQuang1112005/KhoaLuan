"""
pipelines/pipeline_tang3.py
==============================
Lắp ráp thứ tự chạy các step thuộc Tầng 3 (chuẩn hoá metadata).

Thứ tự đề xuất: chuẩn hoá tên/định dạng trước, validate giá trị sau.
    T3.36 normalize_rating_criteria      (tách trước, dựa trên T1.6 đã chạy ở Tầng 1)
 -> T3.33 normalize_product_variant
 -> T3.34 normalize_product_name
 -> T3.35 normalize_variant_naming
 -> T3.43 unify_product_naming_across_records
 -> T3.39 normalize_review_time_format
 -> T3.40 flag_anomalous_timestamps
 -> T3.37 validate_rating_value
 -> T3.38 handle_missing_rating
 -> T3.41 validate_username
 -> T3.42 validate_product_url
 -> T3.44 flag_mismatched_product_assignment   (cần metadata đã chuẩn hoá ở trên)

TODO: implement run(), tương tự pipeline_tang1.py.
"""

from typing import Iterable

from core.pipeline import Pipeline

STEP_ORDER = [
    "T3.36", "T3.33", "T3.34", "T3.35", "T3.43",
    "T3.39", "T3.40",
    "T3.37", "T3.38",
    "T3.41", "T3.42",
    "T3.44",
]


def run(pipeline: Pipeline, products: Iterable[str]):
    raise NotImplementedError
