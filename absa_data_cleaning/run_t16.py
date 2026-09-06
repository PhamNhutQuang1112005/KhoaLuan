"""
run_t16.py — chạy nối tiếp T1.1 -> T1.2+T1.3 -> T1.5 -> T1.6 trên toàn bộ file
trong data/raw/ (xem PRODUCT_FILES trong config/settings.py), ghi kết quả ra
data/interim/.

Thứ tự các bước (giống run_t15.py, cộng thêm T1.6 ở cuối, dùng ĐÚNG kết quả
cuối cùng của T1.1 -> T1.3 -> T1.5 làm đầu vào cho T1.6):
  1. T1.1 fix_field_misalignment — sửa lệch cột 'Tác giả' <-> 'Nội dung tự do'.
  2. T1.2+T1.3 drop_empty_rows   — xoá dòng rỗng hoàn toàn / thiếu 'Nội dung
     tự do' (trường bắt buộc).
  3. T1.5 fix_data_types         — ép 'Thời gian' / 'Thời điểm cào' sang
     datetime chuẩn.
  4. T1.6 split_merged_fields    — tách cột 'Tiêu chí đánh giá' (dạng nhiều
     dòng 'Tên tiêu chí: giá trị') thành mỗi tiêu chí 1 cột riêng. Chạy SAU
     CÙNG vì không phụ thuộc 3 bước trên, và tách sớm hơn chỉ tốn công cho
     các dòng rồi sẽ bị xoá ở bước 2.

In ra console SỐ DÒNG CỤ THỂ đã bị SỬA/XOÁ ở mỗi bước (T1.1/T1.2+T1.3), theo
đúng số dòng khi mở file .xlsx gốc bằng Excel (excel_row_offset=2); riêng T1.5
dùng `max_list` để in gọn vì động tới gần như toàn bộ dòng còn lại; T1.6 không
sửa/xoá dòng nào (chỉ THÊM CỘT MỚI) nên phần in của nó liệt kê tên các cột
tiêu chí vừa tách ra thay vì số dòng.

LƯU Ý: các tên cột tiêu chí là lấy NGUYÊN VĂN từ dữ liệu thô (vd 'Chất lượng'
và 'Chất lượng sản phẩm' vẫn là 2 cột riêng, một vài dòng lỗi định dạng có thể
sinh ra "tiêu chí" là cả 1 câu review) — T1.6 CỐ TÌNH không chuẩn hoá/gộp
nhóm theo khía cạnh (aspect), việc đó là bước xử lý ngữ nghĩa riêng sau này.

Đây chỉ là script chạy tay tạm thời, KHÔNG phải một phần của pipeline chính.
    python run_t16.py
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
    split_merged_fields,
)

DATA_INTERIM_DIR.mkdir(parents=True, exist_ok=True)

for name in PRODUCT_FILES:
    raw = pd.read_excel(raw_path(name))

    after_t11 = fix_field_misalignment(raw)
    after_t13 = drop_empty_rows(after_t11)
    after_t15 = fix_data_types(after_t13)
    after_t16 = split_merged_fields(after_t15)

    out_path = DATA_INTERIM_DIR / f"{name}_t1.6.xlsx"
    # .xlsx (openpyxl) khong ho tro datetime co tz -> bo nhan tz truoc khi ghi
    # (chi anh huong output Excel, KHONG anh huong gia tri after_t16 tra ve).
    export_df = after_t16.copy()
    export_df[SCRAPED_AT_COL] = export_df[SCRAPED_AT_COL].dt.tz_localize(None)
    export_df.to_excel(out_path, index=False)

    print(f"=== {name} -> {out_path} ===")
    print_row_diff(raw, after_t11, label=f"{name}][T1.1", excel_row_offset=2)
    print_row_diff(after_t11, after_t13, label=f"{name}][T1.2+T1.3", excel_row_offset=2)
    print_row_diff(after_t13, after_t15, label=f"{name}][T1.5", excel_row_offset=2, max_list=20)
    print_row_diff(after_t15, after_t16, label=f"{name}][T1.6", excel_row_offset=2)
