"""
dataio/excel_writer.py
========================
Implementation cụ thể của core.io_base.Writer.

Có 2 lựa chọn định dạng output trung gian — để ngỏ, quyết định khi triển khai:
- ExcelWriter: giữ định dạng .xlsx đồng nhất với input, dễ mở tay kiểm tra.
- CsvWriter: nhẹ hơn, phù hợp nếu số dòng lớn lên nhiều sau khi gộp nhiều ngành hàng.
"""

from pathlib import Path

import pandas as pd

from core.io_base import Writer


class ExcelWriter(Writer):
    def write(self, df: pd.DataFrame, destination: Path) -> None:
        """Ghi DataFrame ra file .xlsx tại `destination`.

        TODO: implement — tạo thư mục cha nếu chưa có (destination.parent.mkdir(
        parents=True, exist_ok=True)), rồi df.to_excel(destination, index=False).
        """
        raise NotImplementedError


class CsvWriter(Writer):
    def write(self, df: pd.DataFrame, destination: Path) -> None:
        """Ghi DataFrame ra file .csv tại `destination`.

        TODO: implement tương tự ExcelWriter, chú ý encoding utf-8-sig để mở
        đúng dấu tiếng Việt trong Excel.
        """
        raise NotImplementedError
