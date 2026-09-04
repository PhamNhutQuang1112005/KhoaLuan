"""
core/io_base.py
===============
Abstract base class cho Reader / Writer — phần "khung OOP" quản lý việc
đọc dữ liệu vào và xuất dữ liệu ra sau mỗi bước xử lý.

Mục đích tách interface (ở đây) khỏi implementation cụ thể (ở dataio/):
- Cho phép thêm định dạng mới (CSV, Parquet, DB...) mà không đổi core/pipeline.py.
- Chuẩn hoá hành vi: mọi Reader/Writer đều nhận/trả cùng 1 kiểu dữ liệu
  (pandas.DataFrame — xem quyết định ở core/schema.py).
"""

from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd


class Reader(ABC):
    """Interface đọc dữ liệu đầu vào cho 1 step."""

    @abstractmethod
    def read(self, source: Path) -> pd.DataFrame:
        """Đọc dữ liệu từ `source`, trả về DataFrame theo schema chuẩn.

        Implementation cụ thể (VD ExcelReader) chịu trách nhiệm:
        - Validate schema cơ bản (gọi core.schema.dataframe_columns_match_schema).
        - KHÔNG làm sạch dữ liệu ở đây — chỉ đọc và chuẩn hoá format đọc vào.
        """
        raise NotImplementedError


class Writer(ABC):
    """Interface xuất dữ liệu sau khi xử lý xong 1 step."""

    @abstractmethod
    def write(self, df: pd.DataFrame, destination: Path) -> None:
        """Ghi `df` ra `destination`.

        Implementation cụ thể (VD ExcelWriter) chịu trách nhiệm tạo thư mục
        đích nếu chưa có, đặt tên file theo quy ước trong dataio/file_registry.py.
        """
        raise NotImplementedError
