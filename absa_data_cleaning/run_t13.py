"""
run_t13.py — chạy nối tiếp T1.1 (sửa lệch cột Tác giả <-> Nội dung tự do) rồi
T1.2+T1.3 (đã GỘP CHUNG trong `drop_empty_rows` — xem transforms/tang1_structural.py:
xoá dòng rỗng hoàn toàn VÀ dòng thiếu 'Nội dung tự do', trường bắt buộc) trên
toàn bộ file trong data/raw/ (xem PRODUCT_FILES trong config/settings.py), ghi
kết quả ra data/interim/.

Trước đây có 2 bước T1.2 (validate_required_columns) và T1.3 (drop_empty_rows)
tách rời; do 2 điều kiện gần như luôn trùng nhau trên dữ liệu thực tế, giờ chỉ
còn 1 lượt gọi `drop_empty_rows` duy nhất (T1.2 gọi lại chính hàm này).

In ra console SỐ DÒNG CỤ THỂ đã bị SỬA (T1.1) và đã bị XOÁ (T1.2+T1.3), theo
đúng số dòng khi mở file .xlsx gốc bằng Excel (excel_row_offset=2).

Đây chỉ là script chạy tay tạm thời, KHÔNG phải một phần của pipeline chính.
    python run_t13.py
"""

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from core.diff_report import print_row_diff
from dataio.file_registry import raw_path
from transforms.tang1_structural import drop_empty_rows, fix_field_misalignment

DATA_INTERIM_DIR.mkdir(parents=True, exist_ok=True)

for name in PRODUCT_FILES:
    raw = pd.read_excel(raw_path(name))

    after_t11 = fix_field_misalignment(raw)
    after_t13 = drop_empty_rows(after_t11)

    out_path = DATA_INTERIM_DIR / f"{name}_t1.3.xlsx"
    after_t13.to_excel(out_path, index=False)

    print(f"=== {name} -> {out_path} ===")
    print_row_diff(raw, after_t11, label=f"{name}][T1.1", excel_row_offset=2)
    print_row_diff(after_t11, after_t13, label=f"{name}][T1.2+T1.3", excel_row_offset=2)
