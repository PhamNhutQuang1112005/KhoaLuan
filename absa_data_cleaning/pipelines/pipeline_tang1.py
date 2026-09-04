"""
pipelines/pipeline_tang1.py
==============================
Lắp ráp thứ tự chạy các step thuộc Tầng 1 (lỗi cấu trúc), theo đúng phụ thuộc
logic: phải sửa lệch cột (T1.1) và validate schema (T1.2) TRƯỚC khi các bước
khác (dropna, ép kiểu...) chạy đúng.

Thứ tự đề xuất (có thể điều chỉnh qua config/pipeline_config.yaml -> depends_on):
    T1.1 fix_field_misalignment
 -> T1.2 validate_required_columns
 -> T1.6 split_merged_fields
 -> T1.7 normalize_line_breaks
 -> T1.8 fix_encoding_issues
 -> T1.5 fix_data_types
 -> T1.4 handle_null_values
 -> T1.3 drop_empty_rows        (chạy sau cùng — chỉ xoá khi chắc chắn là rỗng thật)

File này KHÔNG chứa logic — chỉ khai báo thứ tự, gọi lại core.pipeline.Pipeline.
"""

from typing import Iterable

from core.pipeline import Pipeline

STEP_ORDER = [
    "T1.1",
    "T1.2",
    "T1.6",
    "T1.7",
    "T1.8",
    "T1.5",
    "T1.4",
    "T1.3",
]


def run(pipeline: Pipeline, products: Iterable[str]):
    """Chạy toàn bộ Tầng 1 theo STEP_ORDER.

    TODO: implement — lặp STEP_ORDER, lấy step từ StepRegistry, gọi
    pipeline.run_step(step, products); dừng sớm và báo lỗi rõ ràng nếu 1 step
    thất bại (không âm thầm bỏ qua, vì Tầng 2-4 phụ thuộc dữ liệu đã có cấu trúc đúng).
    """
    raise NotImplementedError
