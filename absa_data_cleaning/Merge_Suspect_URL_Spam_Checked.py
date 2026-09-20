"""
Merge_Suspect_URL_Spam_Checked.py — hoà lại các dòng nghi vấn URL/SĐT đã
được RÀ SOÁT THỦ CÔNG (data/interim/Suspect_URL_Spam_Checked.xlsx) vào đúng
file sản phẩm tương ứng (data/interim/{name}_t2.14.xlsx).

BỐI CẢNH: run_t214.py (T2.13+T2.14 split_url_hotline_or_spam_reviews) tách
các dòng có URL/SĐT ở 'Nội dung tự do' hoặc 'Tiêu chí đánh giá' ra khỏi từng
file sản phẩm, gộp CHUNG vào 1 file data/interim/Suspect_URL_Spam.xlsx để con
người rà soát thủ công (xem transforms/tang2_content_quality.py, hàm
split_url_hotline_or_spam_reviews — tránh xoá nhầm review thật chỉ vì nhắc
tới URL/SĐT/zalo/ib mà không thực sự là quảng cáo). Sau khi rà soát bằng
Excel, LƯU LẠI dưới tên data/interim/Suspect_URL_Spam_Checked.xlsx theo ĐÚNG
QUY ƯỚC (giống hệt Short_reviews_Checked.xlsx): XOÁ HẲN những dòng KHÔNG
muốn giữ (đúng là spam/URL rác), chỉ CÒN LẠI những dòng muốn hoà trở lại vào
data (KHÔNG thêm cột đánh dấu nào khác — file chỉ còn 10 cột gốc y hệt
Suspect_URL_Spam.xlsx).

VÌ SAO ĐỌC LẠI {name}_t2.12.xlsx thay vì regenerate từ data/raw/ (khác với
Merge_Short_Reviews_Checked.py): run_t214.py đã đổi input sang đọc trực tiếp
{name}_t2.12.xlsx (không chạy lại từ raw nữa — xem docstring run_t214.py),
nên {name}_t2.12.xlsx CHÍNH LÀ nguồn index tham chiếu ổn định (file cố định
trên đĩa, đọc lại nhiều lần luôn cho cùng thứ tự dòng/index 0-based). Chỉ cần
đọc lại đúng file này rồi chạy lại split_url_hotline_or_spam_reviews là có
lại `kept`/`suspect` với ĐÚNG index như lúc run_t214.py tạo ra
Suspect_URL_Spam.xlsx — không cần chạy lại toàn bộ pipeline T1.1->T2.12 như
Merge_Short_Reviews_Checked.py.

Thuật toán cho từng sản phẩm (`name` trong PRODUCT_FILES):
  1. Đọc lại data/interim/{name}_t2.12.xlsx, chạy split_url_hotline_or_spam_reviews
     để có `kept` (index gốc theo file t2.12) và `suspect` (dùng đối chiếu ở
     bước 4).
  2. Lọc các dòng trong Suspect_URL_Spam_Checked.xlsx có cột 'Sản phẩm' == name.
  3. Khôi phục index gốc bằng cột 'Dòng Excel gốc' (= index gốc + 2, do
     run_t214.py cộng thêm khi tách), rồi bỏ 2 cột phụ trợ 'Sản phẩm' /
     'Dòng Excel gốc' (không thuộc schema chuẩn 8 cột).
  4. Validate: mọi index khôi phục ở bước 3 PHẢI nằm trong `suspect.index`
     của đúng sản phẩm đó, và KHÔNG được trùng lặp — tránh hoà nhầm dòng nếu
     cột 'Sản phẩm'/'Dòng Excel gốc' bị sửa tay nhầm khi rà soát trong Excel.
  5. pd.concat([kept, các dòng đã duyệt]).sort_index() — sort_index() để dòng
     được hoà lại đúng VỊ TRÍ XEN KẼ ban đầu theo thứ tự dòng trong
     {name}_t2.12.xlsx, không dồn hết xuống cuối file.
  6. Ghi đè data/interim/{name}_t2.14.xlsx.

In ra console SỐ DÒNG đã hoà lại cho mỗi sản phẩm qua core.diff_report.

Đây chỉ là script chạy tay tạm thời, KHÔNG phải một phần của pipeline chính,
CHỈ chạy SAU KHI đã có data/interim/Suspect_URL_Spam_Checked.xlsx (rà soát
thủ công từ data/interim/Suspect_URL_Spam.xlsx do run_t214.py sinh ra):
    python Merge_Suspect_URL_Spam_Checked.py
"""

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from core.diff_report import print_row_diff
from transforms.tang2_content_quality import split_url_hotline_or_spam_reviews

CHECKED_PATH = DATA_INTERIM_DIR / "Suspect_URL_Spam_Checked.xlsx"
# Phai khop CHINH XAC voi ten cot ma run_t214.py da dung khi tach/gan nhan
# sang Suspect_URL_Spam.xlsx.
PRODUCT_COL = "Sản phẩm"
SOURCE_ROW_COL = "Dòng Excel gốc"

if not CHECKED_PATH.exists():
    raise FileNotFoundError(
        f"Khong tim thay {CHECKED_PATH}. Hay ra soat "
        f"data/interim/Suspect_URL_Spam.xlsx (do run_t214.py sinh ra) va luu "
        f"lai dung ten file nay truoc khi chay script."
    )

checked = pd.read_excel(CHECKED_PATH)

unknown_products = set(checked[PRODUCT_COL].unique()) - set(PRODUCT_FILES)
if unknown_products:
    raise ValueError(
        f"Cot '{PRODUCT_COL}' trong {CHECKED_PATH} co gia tri khong hop le: "
        f"{sorted(unknown_products)}. San pham hop le: {sorted(PRODUCT_FILES)}."
    )

for name in PRODUCT_FILES:
    in_path = DATA_INTERIM_DIR / f"{name}_t2.12.xlsx"
    if not in_path.exists():
        raise FileNotFoundError(
            f"Khong tim thay {in_path}. Hay chay run_t212.py roi "
            f"Merge_Short_Reviews_Checked.py truoc khi chay script nay."
        )

    before = pd.read_excel(in_path)
    kept, suspect = split_url_hotline_or_spam_reviews(before)

    out_path = DATA_INTERIM_DIR / f"{name}_t2.14.xlsx"
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

    invalid_idx = approved.index.difference(suspect.index)
    if not invalid_idx.empty:
        raise ValueError(
            f"[{name}] {len(invalid_idx)} dong trong {CHECKED_PATH} co "
            f"'{SOURCE_ROW_COL}' khong khop bat ky dong nghi van URL/spam nao "
            f"da tach cho san pham nay (index goc: {sorted(invalid_idx)[:10]}...). "
            f"Kiem tra lai cot '{PRODUCT_COL}'/'{SOURCE_ROW_COL}' co bi sua "
            f"nham khi ra soat khong."
        )

    merged = pd.concat([kept, approved]).sort_index()
    merged.to_excel(out_path, index=False)

    print(f"=== {name} -> {out_path} ===")
    print_row_diff(
        kept,
        merged,
        label=f"{name}][Merge_Suspect_URL_Spam_Checked",
        excel_row_offset=2,
        max_list=20,
    )
