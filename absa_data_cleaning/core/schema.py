"""
core/schema.py
==============
Định nghĩa cấu trúc dữ liệu chuẩn cho 1 bản ghi review (8 cột).

Đây là phần "hình dạng dữ liệu" dùng chung giữa OOP layer (core/, dataio/) và
FP layer (transforms/). Dùng dataclass để:
- Có kiểu dữ liệu tường minh (hỗ trợ Tầng 1, mục T1.5 — sai kiểu dữ liệu).
- Dễ validate schema (T1.2 — thiếu cột bắt buộc).
- Vẫn có thể chuyển đổi qua lại với pandas DataFrame khi cần xử lý hàng loạt
  (xem README mục 7 — chưa chốt DataFrame vs dataclass).

KHÔNG chứa logic làm sạch — chỉ chứa định nghĩa cấu trúc + validate cấu trúc cơ bản.
"""

from dataclasses import dataclass, fields
from datetime import datetime
from typing import Optional


@dataclass
class ReviewRecord:
    """Một dòng dữ liệu chuẩn hoá theo schema 8 cột."""

    author: Optional[str]
    review_time: Optional[str]  # TODO: quyết định giữ str hay parse sang datetime (T3.39)
    product_variant: Optional[str]
    rating_criteria: Optional[str]
    content: Optional[str]
    star_rating: Optional[float]
    product_url: Optional[str]
    crawl_time: Optional[str]

    @classmethod
    def field_names_vn(cls) -> list[str]:
        """Trả về tên cột tiếng Việt tương ứng thứ tự trong file Excel gốc.

        TODO: đồng bộ với config.settings.STANDARD_SCHEMA — cân nhắc sinh tự động
        từ 1 nguồn duy nhất thay vì khai báo lặp ở 2 nơi.
        """
        return [
            "Tác giả",
            "Thời gian",
            "Loại hàng (phân loại)",
            "Tiêu chí đánh giá",
            "Nội dung tự do",
            "Số sao",
            "URL sản phẩm",
            "Thời điểm cào",
        ]

    @classmethod
    def from_row(cls, row: dict) -> "ReviewRecord":
        """Dựng ReviewRecord từ 1 dict (1 dòng DataFrame / 1 dòng Excel).

        TODO: implement mapping tên cột VN -> tên field, xử lý cột thiếu (T1.2),
        xử lý lệch cột (T1.1) TRƯỚC khi gọi hàm này (đây chỉ là bước dựng đối tượng
        sau khi dữ liệu đã ở đúng cột).
        """
        raise NotImplementedError

    def validate_schema(self) -> list[str]:
        """Kiểm tra các trường bắt buộc, trả về danh sách lỗi (rỗng nếu hợp lệ).

        TODO: implement theo taxonomy Tầng 1 (T1.2, T1.4, T1.5) và Tầng 3
        (T3.37, T3.38, T3.41, T3.42).
        """
        raise NotImplementedError


def dataframe_columns_match_schema(columns: list[str]) -> bool:
    """Kiểm tra 1 danh sách tên cột (từ DataFrame) có khớp STANDARD_SCHEMA không.

    Dùng ở bước đọc file đầu vào (dataio/excel_reader.py) để validate sớm (T1.2).
    TODO: implement.
    """
    raise NotImplementedError
