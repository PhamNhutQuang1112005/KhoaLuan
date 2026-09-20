"""
run_t218.py — chạy TOÀN BỘ chuỗi T1.1 -> T2.18 trên dữ liệu tính lại TỪ ĐẦU
(từ data/raw/), ghi kết quả ra data/interim/.

Đây là bản nối dài của run_t216.py (KHÔNG sửa file đó — xem lý do trong
chính docstring của nó): dùng `pipelines.build_reviewed_t218.build_reviewed_t216_dataframe`
để tính lại TOÀN BỘ chuỗi T1.1 -> T2.16 trong bộ nhớ (tự gộp
Short_reviews_Checked.xlsx / Suspect_URL_Spam_Checked.xlsx /
Suspect_Duplicate_Content_Checked.xlsx NẾU đã tồn tại, in CẢNH BÁO nếu chưa —
xem docstring `pipelines/build_reviewed_t214.py` + `pipelines/build_reviewed_t218.py`),
rồi chạy tiếp:

  T2.17 + T2.18 normalize_teencode_and_abbreviations (transforms/tang2_content_quality.py)
  — chuẩn hoá teencode ('ko' -> 'không') VÀ mở rộng từ viết tắt ('sp' -> 'sản
  phẩm') trong 'Nội dung tự do', dùng từ điển
  dictionary/teencode_abbreviation.txt (GỘP CHUNG 2 mục vì dùng chung 1 từ
  điển — xem docstring hàm). Sau đó `split_suspect_teencode_reviews` TÁCH
  RIÊNG (KHÔNG đoán) các dòng có chứa từ trong
  dictionary/suspect_teencode_terms.txt (từ nghi vấn — không đủ tự tin thêm
  dạng chuẩn vào từ điển, vd đa nghĩa/dễ nhầm với từ khác) ra 1 file CHUNG
  Suspect_Teencode_Abbreviation.xlsx (có thêm cột 'Sản phẩm' + 'Dòng Excel
  gốc', giống hệt quy ước Suspect_Duplicate_Content.xlsx) — con người tự rà
  soát thủ công nhóm này sau, lưu lại thành
  Suspect_Teencode_Abbreviation_Checked.xlsx (XOÁ HẲN dòng không muốn giữ,
  chỉ còn lại dòng muốn hoà trở lại), rồi chạy
  Merge_Suspect_Teencode_Abbreviation_Checked.py để hoà lại vào {name}_t2.18.xlsx.

In ra console SỐ DÒNG CỤ THỂ đã bị SỬA/TÁCH, theo đúng số dòng khi mở file
.xlsx bằng Excel (excel_row_offset=2).

Đây chỉ là script chạy tay tạm thời, KHÔNG phải một phần của pipeline chính,
CHỈ cần có data/raw/ (3 file Checked của T2.11-T2.16 + file Checked của
T2.17+T2.18 đều TUỲ CHỌN — thiếu vẫn chạy được, chỉ in cảnh báo kết quả tạm
thời):
    python run_t218.py
"""

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from core.diff_report import print_row_diff
from pipelines.build_reviewed_t218 import build_reviewed_t216_dataframe
from transforms.tang2_content_quality import (
    normalize_teencode_and_abbreviations,
    split_suspect_teencode_reviews,
)

DATA_INTERIM_DIR.mkdir(parents=True, exist_ok=True)
SUSPECT_PATH = DATA_INTERIM_DIR / "Suspect_Teencode_Abbreviation.xlsx"
PRODUCT_COL = "Sản phẩm"
SOURCE_ROW_COL = "Dòng Excel gốc"

all_suspect_rows = []

for name in PRODUCT_FILES:
    before = build_reviewed_t216_dataframe(name)
    normalized = normalize_teencode_and_abbreviations(before)
    kept, suspect = split_suspect_teencode_reviews(normalized)

    out_path = DATA_INTERIM_DIR / f"{name}_t2.18.xlsx"
    kept.to_excel(out_path, index=False)

    if not suspect.empty:
        tagged_suspect = suspect.copy()
        tagged_suspect.insert(0, SOURCE_ROW_COL, tagged_suspect.index + 2)
        tagged_suspect.insert(0, PRODUCT_COL, name)
        all_suspect_rows.append(tagged_suspect)

    print(f"=== {name} -> {out_path} ===")
    print_row_diff(before, normalized, label=f"{name}][T2.17+T2.18 (chuan hoa teencode/viet tat)", excel_row_offset=2, max_list=20)
    print_row_diff(normalized, kept, label=f"{name}][T2.17+T2.18 (tach ra Suspect_Teencode_Abbreviation)", excel_row_offset=2, max_list=20)

if all_suspect_rows:
    suspect_df = pd.concat(all_suspect_rows, ignore_index=True)
    suspect_df.to_excel(SUSPECT_PATH, index=False)
    print(f"=== {SUSPECT_PATH} ({len(suspect_df)} dong nghi van teencode/viet tat tu {len(all_suspect_rows)} san pham) ===")
else:
    print("=== Khong co dong nao nghi van teencode/viet tat — khong tao Suspect_Teencode_Abbreviation.xlsx ===")
