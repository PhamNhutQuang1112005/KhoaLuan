"""
dataio/excel_reader.py
=======================
Implementation cụ thể của core.io_base.Reader cho file .xlsx.
"""

from pathlib import Path

import pandas as pd

from core.io_base import Reader
from core.schema import dataframe_columns_match_schema


class ExcelReader(Reader):
    """Đọc file Excel thô (sheet 'Reviews') theo schema 8 cột chuẩn."""

    def __init__(self, sheet_name: str = "Reviews") -> None:
        self.sheet_name = sheet_name

    def read(self, source: Path) -> pd.DataFrame:
        """Đọc `source`, validate schema cơ bản, trả về DataFrame.

        TODO khi implement:
        1. pd.read_excel(source, sheet_name=self.sheet_name)
        2. Kiểm tra dataframe_columns_match_schema(df.columns) -> nếu False,
           raise lỗi rõ ràng (liên quan Tầng 1, mục T1.2).
        3. KHÔNG sửa dữ liệu ở đây (không strip, không dropna...) — chỉ đọc thô.
           Việc làm sạch thuộc về transforms/, không phải I/O layer.
        """
        raise NotImplementedError
