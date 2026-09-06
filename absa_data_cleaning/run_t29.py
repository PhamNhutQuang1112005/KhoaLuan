"""
run_t29.py — chạy nối tiếp T1.1 -> T1.2+T1.3 -> T1.5 -> T2.9+T2.10 trên toàn bộ
file trong data/raw/ (xem PRODUCT_FILES trong config/settings.py), ghi kết quả
ra data/interim/.

Thứ tự các bước (KẾ THỪA đúng chuỗi T1.1 -> T1.3 -> T1.5 giống run_t15.py; CỐ
TÌNH KHÔNG chạy T1.6 split_merged_fields — T2.9+T2.10 chỉ động tới cột 'Nội
dung tự do', không liên quan gì tới việc tách cột 'Tiêu chí đánh giá'):
  1. T1.1 fix_field_misalignment  — sửa lệch cột 'Tác giả' <-> 'Nội dung tự do'.
  2. T1.2+T1.3 drop_empty_rows    — xoá dòng rỗng hoàn toàn / dòng trống ĐỒNG
     THỜI cả 'Tiêu chí đánh giá' và 'Nội dung tự do'.
  3. T1.5 fix_data_types          — ép 'Thời gian' / 'Thời điểm cào' sang
     datetime chuẩn.
  4. T2.9+T2.10 drop_emoji_or_special_char_only_reviews (transforms/tang2_content_quality.py)
     — xoá dòng có 'Nội dung tự do' CHỈ gồm emoji và/hoặc ký tự đặc biệt,
     không mang thông tin hữu ích nào khác. Chạy SAU CÙNG vì cần 'Nội dung tự
     do' đã được T1.1 lấp đầy đúng cho các dòng vốn bị lệch cột, và không phụ
     thuộc kết quả của T1.5.

In ra console SỐ DÒNG CỤ THỂ đã bị SỬA/XOÁ ở mỗi bước, theo đúng số dòng khi mở
file .xlsx gốc bằng Excel (excel_row_offset=2); riêng T1.5 dùng `max_list` vì
động tới gần như toàn bộ dòng còn lại; T1.2+T1.3 cũng dùng `max_list=1` để in
gọn "từ dòng #đầu -> #cuối (N dòng)" thay vì liệt kê từng dòng.

Đây chỉ là script chạy tay tạm thời, KHÔNG phải một phần của pipeline chính.
    python run_t29.py
"""

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from core.diff_report import print_row_diff
from dataio.file_registry import raw_path
from transforms.tang1_structural import (
    SCRAPED_AT_COL,
    drop_empty_rows,
    fix_data_types,
    fix_field_misalignment,
)
from transforms.tang2_content_quality import drop_emoji_or_special_char_only_reviews

DATA_INTERIM_DIR.mkdir(parents=True, exist_ok=True)

for name in PRODUCT_FILES:
    raw = pd.read_excel(raw_path(name))

    after_t11 = fix_field_misalignment(raw)
    after_t13 = drop_empty_rows(after_t11)
    after_t15 = fix_data_types(after_t13)
    after_t29 = drop_emoji_or_special_char_only_reviews(after_t15)

    out_path = DATA_INTERIM_DIR / f"{name}_t2.9.xlsx"
    # .xlsx (openpyxl) khong ho tro datetime co tz -> bo nhan tz truoc khi ghi
    # (chi anh huong output Excel, KHONG anh huong gia tri after_t29 tra ve).
    export_df = after_t29.copy()
    export_df[SCRAPED_AT_COL] = export_df[SCRAPED_AT_COL].dt.tz_localize(None)
    export_df.to_excel(out_path, index=False)

    print(f"=== {name} -> {out_path} ===")
    print_row_diff(raw, after_t11, label=f"{name}][T1.1", excel_row_offset=2)
    print_row_diff(after_t11, after_t13, label=f"{name}][T1.2+T1.3", excel_row_offset=2, max_list=1)
    print_row_diff(after_t13, after_t15, label=f"{name}][T1.5", excel_row_offset=2, max_list=20)
    print_row_diff(after_t15, after_t29, label=f"{name}][T2.9+T2.10", excel_row_offset=2, max_list=20)
