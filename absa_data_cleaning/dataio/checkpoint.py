"""
dataio/checkpoint.py
=====================
Giai đoạn 0 — lưu checkpoint sau mỗi giai đoạn (xem
config.settings.CHECKPOINT_VERSIONS) và ghi log số dòng bị xoá/sửa ở từng
bước. Bảng log dùng trực tiếp cho phần mô tả dataset trong luận văn.
"""

from pathlib import Path

import pandas as pd


def save_checkpoint(df: pd.DataFrame, product: str, version: str) -> Path:
    """Ghi `df` ra data/interim/<version>/<product>.xlsx (v7_final ->
    data/processed/) và trả về đường dẫn đã ghi.

    TODO: implement — bỏ tz ở cột datetime trước khi ghi .xlsx (xem
    scripts/legacy/run_t16.py).
    """
    raise NotImplementedError


def append_step_log(version: str, step: str, product: str, rows_before: int, rows_after: int, rows_modified: int) -> None:
    """Ghi thêm 1 dòng vào log số dòng xoá/sửa (vd logs/cleaning_log.csv).

    TODO: implement (hoặc dùng core.report.CleaningReport).
    """
    raise NotImplementedError
