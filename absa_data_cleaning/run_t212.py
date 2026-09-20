"""
run_t212.py — chạy nối tiếp T1.1 -> T1.2+T1.3 -> T1.5 -> T2.9+T2.10 ->
T2.11+T2.12 trên toàn bộ file trong data/raw/ (xem PRODUCT_FILES trong
config/settings.py), ghi kết quả ra data/interim/.

Thứ tự các bước (KẾ THỪA đúng chuỗi T1.1 -> T1.3 -> T1.5 -> T2.9+T2.10 giống
run_t29.py; CỐ TÌNH KHÔNG chạy T1.6 split_merged_fields — các bước Tầng 2 ở
đây chỉ động tới cột 'Nội dung tự do', không liên quan gì tới việc tách cột
'Tiêu chí đánh giá'):
  1. T1.1 fix_field_misalignment  — sửa lệch cột 'Tác giả' <-> 'Nội dung tự do'.
  2. T1.2+T1.3 drop_empty_rows    — xoá dòng rỗng hoàn toàn / dòng trống ĐỒNG
     THỜI cả 'Tiêu chí đánh giá' và 'Nội dung tự do'.
  3. T1.5 fix_data_types          — ép 'Thời gian' / 'Thời điểm cào' sang
     datetime chuẩn.
  4. T2.9+T2.10 drop_emoji_or_special_char_only_reviews — xoá dòng khi CẢ 2
     điều kiện đúng: 'Nội dung tự do' CHỈ gồm emoji và/hoặc ký tự đặc biệt,
     VÀ 'Tiêu chí đánh giá' CŨNG rỗng.
  5. T2.11+T2.12 split_short_reviews (transforms/tang2_content_quality.py) —
     KHÔNG còn tự động xoá bằng heuristic (gõ bừa/khớp cụm chung chung) như
     trước. Giờ TÁCH RIÊNG dòng khi CẢ 2 điều kiện đúng:
       - 'Nội dung tự do' có <= SHORT_REVIEW_MAX_WORDS từ (mặc định 5).
       - VÀ 'Tiêu chí đánh giá' CŨNG rỗng.
     ra khỏi file `{name}_t2.12.xlsx`, gộp CHUNG với review ngắn từ TẤT CẢ
     sản phẩm khác vào 1 file `Short_reviews.xlsx` duy nhất (có thêm cột
     'Sản phẩm' + 'Dòng Excel gốc' để biết đến từ file/dòng nào) — con người
     tự rà soát thủ công nhóm này sau, tránh lãng phí dữ liệu do heuristic
     bắt nhầm/bỏ sót.
     Cả bước 4 và 5: nếu 'Tiêu chí đánh giá' CÓ giá trị thì GIỮ LẠI dòng dù
     'Nội dung tự do' ngắn/không hữu ích — nhất quán với nguyên tắc T1.2+T1.3
     (chỉ tách/xoá khi cả 2 trường bắt buộc cùng không hữu ích). Cả 2 bước
     chạy SAU CÙNG vì thao tác trên 'Nội dung tự do' đã được T1.1 lấp đầy
     đúng, không phụ thuộc T1.5.

In ra console SỐ DÒNG CỤ THỂ đã bị SỬA/XOÁ ở mỗi bước, theo đúng số dòng khi mở
file .xlsx gốc bằng Excel (excel_row_offset=2); T1.5 và T2.11+T2.12 dùng
`max_list` vì có thể động tới khá nhiều dòng, in gọn "từ dòng #đầu -> #cuối
(N dòng)" thay vì liệt kê từng dòng.

Đây chỉ là script chạy tay tạm thời, KHÔNG phải một phần của pipeline chính.
    python run_t212.py
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
from transforms.tang2_content_quality import (
    drop_emoji_or_special_char_only_reviews,
    split_short_reviews,
)

DATA_INTERIM_DIR.mkdir(parents=True, exist_ok=True)
SHORT_REVIEWS_PATH = DATA_INTERIM_DIR / "Short_reviews.xlsx"
PRODUCT_COL = "Sản phẩm"
SOURCE_ROW_COL = "Dòng Excel gốc"

all_short_reviews = []

for name in PRODUCT_FILES:
    raw = pd.read_excel(raw_path(name))

    after_t11 = fix_field_misalignment(raw)
    after_t13 = drop_empty_rows(after_t11)
    after_t15 = fix_data_types(after_t13)
    after_t29 = drop_emoji_or_special_char_only_reviews(after_t15)
    kept, short = split_short_reviews(after_t29)

    out_path = DATA_INTERIM_DIR / f"{name}_t2.12.xlsx"
    # .xlsx (openpyxl) khong ho tro datetime co tz -> bo nhan tz truoc khi ghi
    # (chi anh huong output Excel, KHONG anh huong gia tri kept tra ve).
    export_df = kept.copy()
    export_df[SCRAPED_AT_COL] = export_df[SCRAPED_AT_COL].dt.tz_localize(None)
    export_df.to_excel(out_path, index=False)

    if not short.empty:
        tagged_short = short.copy()
        tagged_short[SCRAPED_AT_COL] = tagged_short[SCRAPED_AT_COL].dt.tz_localize(None)
        tagged_short.insert(0, SOURCE_ROW_COL, tagged_short.index + 2)
        tagged_short.insert(0, PRODUCT_COL, name)
        all_short_reviews.append(tagged_short)

    print(f"=== {name} -> {out_path} ===")
    print_row_diff(raw, after_t11, label=f"{name}][T1.1", excel_row_offset=2)
    print_row_diff(after_t11, after_t13, label=f"{name}][T1.2+T1.3", excel_row_offset=2, max_list=1)
    print_row_diff(after_t13, after_t15, label=f"{name}][T1.5", excel_row_offset=2, max_list=20)
    print_row_diff(after_t15, after_t29, label=f"{name}][T2.9+T2.10", excel_row_offset=2, max_list=20)
    print_row_diff(after_t29, kept, label=f"{name}][T2.11+T2.12 (tach ra Short_reviews)", excel_row_offset=2, max_list=20)

short_reviews_df = pd.concat(all_short_reviews, ignore_index=True)
short_reviews_df.to_excel(SHORT_REVIEWS_PATH, index=False)
print(f"=== {SHORT_REVIEWS_PATH} ({len(short_reviews_df)} dong review ngan tu {len(all_short_reviews)} san pham) ===")
