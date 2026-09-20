"""
Merge_Short_Reviews_Checked.py — hoà lại các dòng review ngắn đã được RÀ SOÁT
THỦ CÔNG (data/interim/Short_reviews_Checked.xlsx) vào đúng file sản phẩm
tương ứng (data/interim/{name}_t2.12.xlsx).

BỐI CẢNH: run_t212.py (T1.1 -> T1.2+T1.3 -> T1.5 -> T2.9+T2.10 -> T2.11+T2.12)
tách các review <= SHORT_REVIEW_MAX_WORDS từ (và 'Tiêu chí đánh giá' cũng
rỗng) ra khỏi từng file sản phẩm, gộp CHUNG vào 1 file
data/interim/Short_reviews.xlsx để con người rà soát thủ công (xem
transforms/tang2_content_quality.py, hàm split_short_reviews — tránh lãng phí
dữ liệu do heuristic tự động quyết định sai). Sau khi rà soát bằng Excel,
LƯU LẠI dưới tên data/interim/Short_reviews_Checked.xlsx theo ĐÚNG QUY ƯỚC:
XOÁ HẲN những dòng KHÔNG muốn giữ, chỉ CÒN LẠI những dòng muốn hoà trở lại
vào data (KHÔNG thêm cột đánh dấu nào khác — file chỉ còn 10 cột gốc y hệt
Short_reviews.xlsx).

VÌ SAO KHÔNG đọc lại {name}_t2.12.xlsx trên đĩa để merge: to_excel(index=False)
KHÔNG lưu lại index gốc của DataFrame, nên đọc lại file đó sẽ mất hoàn toàn vị
trí dòng ban đầu. Script này thay vào đó CHẠY LẠI TOÀN BỘ pipeline
T1.1 -> T2.9+T2.10 -> T2.11+T2.12 từ data/raw/ (giống hệt run_t212.py) để có
lại `kept`/`short` với ĐÚNG index gốc trong bộ nhớ, rồi mới hoà (concat) các
dòng đã duyệt vào theo index đó.

Thuật toán cho từng sản phẩm (`name` trong PRODUCT_FILES):
  1. Chạy lại pipeline T1.1 -> T1.2+T1.3 -> T1.5 -> T2.9+T2.10 ->
     split_short_reviews y hệt run_t212.py để có `kept` (đã tách review ngắn,
     index gốc) và `short` (index gốc của các dòng đã tách, dùng để đối chiếu
     ở bước 4).
  2. Lọc các dòng trong Short_reviews_Checked.xlsx có cột 'Sản phẩm' == name.
  3. Khôi phục index gốc bằng cột 'Dòng Excel gốc' (= index gốc + 2, do
     run_t212.py cộng thêm khi tách), rồi bỏ 2 cột phụ trợ 'Sản phẩm' /
     'Dòng Excel gốc' (không thuộc schema chuẩn 8 cột).
  4. Validate: mọi index khôi phục ở bước 3 PHẢI nằm trong `short.index` của
     đúng sản phẩm đó, và KHÔNG được trùng lặp — tránh hoà nhầm dòng nếu cột
     'Sản phẩm'/'Dòng Excel gốc' bị sửa tay nhầm khi rà soát trong Excel.
  5. pd.concat([kept, các dòng đã duyệt]).sort_index() — sort_index() để dòng
     được hoà lại đúng VỊ TRÍ XEN KẼ ban đầu theo thứ tự dòng gốc trong file
     raw, không dồn hết xuống cuối file.
  6. Ghi đè data/interim/{name}_t2.12.xlsx.

In ra console SỐ DÒNG đã hoà lại cho mỗi sản phẩm qua core.diff_report.

Đây chỉ là script chạy tay tạm thời, KHÔNG phải một phần của pipeline chính,
CHỈ chạy SAU KHI đã có data/interim/Short_reviews_Checked.xlsx (rà soát thủ
công từ data/interim/Short_reviews.xlsx do run_t212.py sinh ra):
    python Merge_Short_Reviews_Checked.py
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

CHECKED_PATH = DATA_INTERIM_DIR / "Short_reviews_Checked.xlsx"
# Phai khop CHINH XAC voi ten cot ma run_t212.py da dung khi tach/gan nhan
# sang Short_reviews.xlsx.
PRODUCT_COL = "Sản phẩm"
SOURCE_ROW_COL = "Dòng Excel gốc"

if not CHECKED_PATH.exists():
    raise FileNotFoundError(
        f"Khong tim thay {CHECKED_PATH}. Hay ra soat "
        f"data/interim/Short_reviews.xlsx (do run_t212.py sinh ra) va luu lai "
        f"dung ten file nay truoc khi chay script."
    )

checked = pd.read_excel(CHECKED_PATH)

unknown_products = set(checked[PRODUCT_COL].unique()) - set(PRODUCT_FILES)
if unknown_products:
    raise ValueError(
        f"Cot '{PRODUCT_COL}' trong {CHECKED_PATH} co gia tri khong hop le: "
        f"{sorted(unknown_products)}. San pham hop le: {sorted(PRODUCT_FILES)}."
    )

for name in PRODUCT_FILES:
    raw = pd.read_excel(raw_path(name))

    after_t11 = fix_field_misalignment(raw)
    after_t13 = drop_empty_rows(after_t11)
    after_t15 = fix_data_types(after_t13)
    after_t29 = drop_emoji_or_special_char_only_reviews(after_t15)
    kept, short = split_short_reviews(after_t29)
    # .xlsx (openpyxl) khong ho tro datetime co tz -> bo nhan tz truoc khi
    # ghep voi `approved` (da tz-naive san vi doc tu file .xlsx da tung xuat).
    kept[SCRAPED_AT_COL] = kept[SCRAPED_AT_COL].dt.tz_localize(None)

    out_path = DATA_INTERIM_DIR / f"{name}_t2.12.xlsx"
    approved = checked.loc[checked[PRODUCT_COL] == name].copy()

    if approved.empty:
        kept.to_excel(out_path, index=False)
        print(f"=== {name} -> {out_path}: khong co dong nao duoc duyet de hoa lai ===")
        continue

    approved.index = approved[SOURCE_ROW_COL] - 2
    approved = approved.drop(columns=[PRODUCT_COL, SOURCE_ROW_COL])

    duplicated_idx = approved.index[approved.index.duplicated()]
    if not duplicated_idx.empty:
        raise ValueError(
            f"[{name}] {CHECKED_PATH} co {len(duplicated_idx)} dong trung "
            f"'{SOURCE_ROW_COL}': {sorted(set(duplicated_idx))[:10]}... "
            f"Kiem tra lai co bi copy-paste nham dong khi ra soat khong."
        )

    invalid_idx = approved.index.difference(short.index)
    if not invalid_idx.empty:
        raise ValueError(
            f"[{name}] {len(invalid_idx)} dong trong {CHECKED_PATH} co "
            f"'{SOURCE_ROW_COL}' khong khop bat ky dong review ngan nao da "
            f"tach cho san pham nay (index goc: {sorted(invalid_idx)[:10]}...). "
            f"Kiem tra lai cot '{PRODUCT_COL}'/'{SOURCE_ROW_COL}' co bi sua "
            f"nham khi ra soat khong."
        )

    merged = pd.concat([kept, approved]).sort_index()
    merged.to_excel(out_path, index=False)

    print(f"=== {name} -> {out_path} ===")
    print_row_diff(
        kept,
        merged,
        label=f"{name}][Merge_Short_Reviews_Checked",
        excel_row_offset=2,
        max_list=20,
    )
