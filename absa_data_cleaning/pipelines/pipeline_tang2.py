"""
pipelines/pipeline_tang2.py
==============================
Lắp ráp thứ tự chạy các step thuộc Tầng 2 (chất lượng & nhiễu nội dung).

Nguyên tắc thứ tự đề xuất:
1. Chạy nhóm 2.3 (flag_*, T2.28-T2.32) TRƯỚC TIÊN để đánh dấu nội dung cần giữ,
   trước khi các bước biến đổi/loại bỏ ở 2.1, 2.2 có thể ảnh hưởng đến chúng.
2. Nhóm 2.2 (nhiễu biểu diễn, T2.17-T2.27) chạy tiếp theo — đây là các phép
   biến đổi văn bản (chuẩn hoá), không xoá dòng.
3. Nhóm 2.1 (nội dung không giá trị, T2.9-T2.16) chạy sau cùng — đây là nhóm
   duy nhất có thể XOÁ DÒNG, nên cần chạy sau khi văn bản đã được chuẩn hoá
   (tránh xoá nhầm review chỉ vì chưa chuẩn hoá nên trông "vô nghĩa").

TODO: implement run(), tương tự pipeline_tang1.py.
"""

from typing import Iterable

from core.pipeline import Pipeline

STEP_ORDER = [
    # 2.3 — đánh dấu, không xoá
    "T2.28", "T2.29", "T2.30", "T2.31", "T2.32",
    # 2.2 — chuẩn hoá biểu diễn
    "T2.17", "T2.18", "T2.19", "T2.20", "T2.21", "T2.22",
    "T2.23", "T2.24", "T2.25", "T2.26", "T2.27",
    # 2.1 — lọc/xoá nội dung không giá trị (chạy sau cùng)
    "T2.9", "T2.10", "T2.11", "T2.12", "T2.13", "T2.14", "T2.15", "T2.16",
]


def run(pipeline: Pipeline, products: Iterable[str]):
    raise NotImplementedError
