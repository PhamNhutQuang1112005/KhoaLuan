"""
Merge_Suspect_Teencode_Abbreviation_Checked.py — hoà lại các dòng nghi vấn
teencode/viết tắt đã được RÀ SOÁT THỦ CÔNG
(data/interim/Suspect_Teencode_Abbreviation_Checked.xlsx) vào đúng file sản
phẩm tương ứng (data/interim/{name}_t2.18.xlsx).

BỐI CẢNH: run_t218.py (T2.17+T2.18 normalize_teencode_and_abbreviations)
chuẩn hoá teencode/từ viết tắt theo dictionary/teencode_abbreviation.txt, rồi
TÁCH RIÊNG (split_suspect_teencode_reviews) các dòng chứa từ trong
dictionary/suspect_teencode_terms.txt (từ nghi vấn — không đủ tự tin thêm
dạng chuẩn vào từ điển) ra 1 file CHUNG Suspect_Teencode_Abbreviation.xlsx để
con người rà soát thủ công. Sau khi rà soát bằng Excel (có thể sửa trực tiếp
'Nội dung tự do' nếu muốn tự chuẩn hoá tay, hoặc chỉ đơn giản quyết định giữ
dòng nào), LƯU LẠI dưới tên
data/interim/Suspect_Teencode_Abbreviation_Checked.xlsx theo ĐÚNG QUY ƯỚC
(giống hệt Suspect_Duplicate_Content_Checked.xlsx): XOÁ HẲN những dòng KHÔNG
muốn giữ, chỉ CÒN LẠI những dòng muốn hoà trở lại vào data (KHÔNG thêm cột
đánh dấu nào khác — file chỉ còn 8 cột gốc + 'Sản phẩm' + 'Dòng Excel gốc').

VÌ SAO DÙNG build_reviewed_t216_dataframe THAY VÌ ĐỌC {name}_t2.16.xlsx TRÊN
ĐĨA: cùng lý do run_t216.py/Merge_Suspect_Duplicate_Content_Checked.py không
đọc thẳng {name}_t2.14.xlsx — tránh phụ thuộc thứ tự chạy/rà soát trước đó đã
hoàn tất hay chưa (xem docstring pipelines/build_reviewed_t214.py). Script
này PHẢI dùng ĐÚNG `build_reviewed_t216_dataframe` (pipelines/build_reviewed_t218.py)
rồi tự áp lại normalize_teencode_and_abbreviations + split_suspect_teencode_reviews
để tái tạo lại chính xác `kept`/`suspect` với index KHỚP với lúc run_t218.py
tạo ra Suspect_Teencode_Abbreviation.xlsx.

Thuật toán cho từng sản phẩm (`name` trong PRODUCT_FILES) — giống hệt
Merge_Suspect_Duplicate_Content_Checked.py, chỉ đổi bước tách:
  1. build_reviewed_t216_dataframe(name) -> normalize_teencode_and_abbreviations
     -> split_suspect_teencode_reviews để có `kept` (index gốc) và `suspect`
     (dùng đối chiếu ở bước 4).
  2. Lọc các dòng trong Suspect_Teencode_Abbreviation_Checked.xlsx có cột
     'Sản phẩm' == name.
  3. Khôi phục index gốc bằng cột 'Dòng Excel gốc' (= index gốc + 2), bỏ 2
     cột phụ trợ 'Sản phẩm' / 'Dòng Excel gốc'.
  4. Validate: mọi index khôi phục ở bước 3 PHẢI nằm trong `suspect.index`
     của đúng sản phẩm đó, và KHÔNG được trùng lặp.
  5. pd.concat([kept, các dòng đã duyệt]).sort_index().
  6. Ghi đè data/interim/{name}_t2.18.xlsx.

Bước 2-5 dùng chung `merge_checked_rows` (pipelines/build_reviewed_t214.py).

In ra console SỐ DÒNG đã hoà lại cho mỗi sản phẩm qua core.diff_report.

Đây chỉ là script chạy tay tạm thời, KHÔNG phải một phần của pipeline chính,
CHỈ chạy SAU KHI đã có data/interim/Suspect_Teencode_Abbreviation_Checked.xlsx
(rà soát thủ công từ data/interim/Suspect_Teencode_Abbreviation.xlsx do
run_t218.py sinh ra):
    python Merge_Suspect_Teencode_Abbreviation_Checked.py
"""

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from core.diff_report import print_row_diff
from pipelines.build_reviewed_t214 import merge_checked_rows
from pipelines.build_reviewed_t218 import build_reviewed_t216_dataframe
from transforms.tang2_content_quality import (
    normalize_teencode_and_abbreviations,
    split_suspect_teencode_reviews,
)

CHECKED_PATH = DATA_INTERIM_DIR / "Suspect_Teencode_Abbreviation_Checked.xlsx"
# Phai khop CHINH XAC voi ten cot ma run_t218.py da dung khi tach/gan nhan
# sang Suspect_Teencode_Abbreviation.xlsx.
PRODUCT_COL = "Sản phẩm"
SOURCE_ROW_COL = "Dòng Excel gốc"

if not CHECKED_PATH.exists():
    raise FileNotFoundError(
        f"Khong tim thay {CHECKED_PATH}. Hay ra soat "
        f"data/interim/Suspect_Teencode_Abbreviation.xlsx (do run_t218.py sinh "
        f"ra) va luu lai dung ten file nay truoc khi chay script."
    )

for name in PRODUCT_FILES:
    t216 = build_reviewed_t216_dataframe(name)
    normalized = normalize_teencode_and_abbreviations(t216)
    kept, suspect = split_suspect_teencode_reviews(normalized)

    out_path = DATA_INTERIM_DIR / f"{name}_t2.18.xlsx"
    merged = merge_checked_rows(kept, suspect, CHECKED_PATH, name, "T2.17+T2.18")
    merged.to_excel(out_path, index=False)

    print(f"=== {name} -> {out_path} ===")
    print_row_diff(
        kept,
        merged,
        label=f"{name}][Merge_Suspect_Teencode_Abbreviation_Checked",
        excel_row_offset=2,
        max_list=20,
    )
