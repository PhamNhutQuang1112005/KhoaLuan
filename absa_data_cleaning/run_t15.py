"""
run_t15.py — chạy nối tiếp T1.1 -> T1.2+T1.3 -> T1.5 trên toàn bộ file trong
data/raw/ (xem PRODUCT_FILES trong config/settings.py), ghi kết quả ra
data/interim/.

Thứ tự các bước (giống run_t13.py, cộng thêm T1.5 ở cuối):
  1. T1.1 fix_field_misalignment    — sửa lệch cột 'Tác giả' <-> 'Nội dung tự do'.
  2. T1.2+T1.3 drop_empty_rows      — xoá dòng rỗng hoàn toàn / thiếu 'Nội dung
     tự do' (trường bắt buộc). Phải chạy SAU T1.1 vì T1.1 có thể lấp đầy
     'Nội dung tự do' cho dòng vốn bị lệch cột (nên chưa nên xoá vội).
  3. T1.5 fix_data_types            — ép 'Thời gian' (giờ địa phương, tz-naive)
     và 'Thời điểm cào' (ISO 8601 UTC) sang datetime chuẩn. Chạy SAU CÙNG vì
     không phụ thuộc 2 bước trên, và ép kiểu sớm hơn chỉ tốn công parse lại
     cho các dòng rồi sẽ bị xoá ở bước 2.

In ra console SỐ DÒNG CỤ THỂ đã bị SỬA/XOÁ ở mỗi bước, theo đúng số dòng khi mở
file .xlsx gốc bằng Excel (excel_row_offset=2).

LƯU Ý: khác với T1.1/T1.3 (chỉ động tới vài dòng cụ thể), T1.5 ép kiểu dữ liệu
cho TOÀN BỘ dòng còn lại (chuyển từ chuỗi text sang datetime) — liệt kê hết
từng dòng sẽ rất dài và không còn nhiều ý nghĩa, nên dòng in của T1.5 dùng
`max_list` để chỉ hiện gọn "từ dòng #đầu -> #cuối (N dòng)".

Đây chỉ là script chạy tay tạm thời, KHÔNG phải một phần của pipeline chính.
    python run_t15.py
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

DATA_INTERIM_DIR.mkdir(parents=True, exist_ok=True)

for name in PRODUCT_FILES:
    raw = pd.read_excel(raw_path(name))

    after_t11 = fix_field_misalignment(raw)
    after_t13 = drop_empty_rows(after_t11)
    after_t15 = fix_data_types(after_t13)

    out_path = DATA_INTERIM_DIR / f"{name}_t1.5.xlsx"
    # .xlsx (openpyxl) khong ho tro datetime co tz -> bo nhan tz truoc khi ghi
    # (chi anh huong output Excel, KHONG anh huong gia tri after_t15 tra ve).
    export_df = after_t15.copy()
    export_df[SCRAPED_AT_COL] = export_df[SCRAPED_AT_COL].dt.tz_localize(None)
    export_df.to_excel(out_path, index=False)

    print(f"=== {name} -> {out_path} ===")
    print_row_diff(raw, after_t11, label=f"{name}][T1.1", excel_row_offset=2)
    print_row_diff(after_t11, after_t13, label=f"{name}][T1.2+T1.3", excel_row_offset=2)
    print_row_diff(after_t13, after_t15, label=f"{name}][T1.5", excel_row_offset=2, max_list=20)
