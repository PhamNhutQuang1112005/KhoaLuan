"""
Merge_Suspect_Duplicate_Content_Checked.py — hoà lại các dòng nghi vấn gần
trùng nội dung đã được RÀ SOÁT THỦ CÔNG
(data/interim/Suspect_Duplicate_Content_Checked.xlsx) vào đúng file sản phẩm
tương ứng (data/interim/{name}_t2.16.xlsx).

BỐI CẢNH: run_t216.py (T2.15 drop_exact_duplicates + T2.16
split_near_duplicate_reviews) trước tiên XOÁ HẲN các dòng trùng lặp TUYỆT ĐỐI
(T2.15 — không cần rà soát, xem docstring transforms/tang2_content_quality.py),
rồi TÁCH các cặp dòng NGHI VẤN gần trùng nội dung ('Nội dung tự do' có
similarity >= NEAR_DUPLICATE_SIMILARITY_THRESHOLD GIỮA 2 TÁC GIẢ KHÁC NHAU) ra
khỏi từng file sản phẩm, gộp CHUNG vào 1 file
data/interim/Suspect_Duplicate_Content.xlsx để con người rà soát thủ công (xem
transforms/tang2_content_quality.py, hàm split_near_duplicate_reviews — tránh
xoá nhầm 2 review THẬT chỉ vì tình cờ viết giống nhau khi cùng khen/chê 1 đặc
điểm phổ biến). Sau khi rà soát bằng Excel, LƯU LẠI dưới tên
data/interim/Suspect_Duplicate_Content_Checked.xlsx theo ĐÚNG QUY ƯỚC (giống
hệt Suspect_URL_Spam_Checked.xlsx): XOÁ HẲN những dòng KHÔNG muốn giữ (đúng là
review ảo/copy hàng loạt), chỉ CÒN LẠI những dòng muốn hoà trở lại vào data
(KHÔNG thêm cột đánh dấu nào khác — file chỉ còn 10 cột gốc y hệt
Suspect_Duplicate_Content.xlsx).

VÌ SAO DÙNG build_reviewed_t214_dataframe THAY VÌ ĐỌC {name}_t2.14.xlsx TRÊN
ĐĨA: run_t216.py (bản hiện tại) không còn ghi/đọc {name}_t2.14.xlsx nữa — nó
tính lại toàn bộ chuỗi T1.1 -> T2.14 TỪ data/raw/ NGAY TRONG BỘ NHỚ mỗi lần
chạy (xem pipelines/build_reviewed_t214.py để biết lý do: tránh phụ thuộc thứ
tự chạy run_t212.py/run_t214.py + 2 vòng rà soát thủ công trước đó có hoàn tất
hay chưa). Script này PHẢI dùng ĐÚNG cùng 1 hàm đó để tái tạo lại chính xác
`kept`/`suspect` với index KHỚP với lúc run_t216.py tạo ra
Suspect_Duplicate_Content.xlsx — `build_reviewed_t214_dataframe` là hàm phụ
thuộc DUY NHẤT vào data/raw/ + Short_reviews_Checked.xlsx +
Suspect_URL_Spam_Checked.xlsx trên đĩa, nên gọi lại ở 2 lần chạy khác nhau
(run_t216.py rồi tới script này) vẫn cho ra đúng cùng 1 kết quả/index, MIỄN LÀ
3 file đó không đổi giữa 2 lần chạy.

Thuật toán cho từng sản phẩm (`name` trong PRODUCT_FILES):
  1. Gọi lại build_reviewed_t214_dataframe(name), chạy drop_exact_duplicates
     rồi split_near_duplicate_reviews để có `kept` (index gốc) và `suspect`
     (dùng đối chiếu ở bước 4).
  2. Lọc các dòng trong Suspect_Duplicate_Content_Checked.xlsx có cột
     'Sản phẩm' == name.
  3. Khôi phục index gốc bằng cột 'Dòng Excel gốc' (= index gốc + 2, do
     run_t216.py cộng thêm khi tách), rồi bỏ 2 cột phụ trợ 'Sản phẩm' /
     'Dòng Excel gốc' (không thuộc schema chuẩn 8 cột).
  4. Validate: mọi index khôi phục ở bước 3 PHẢI nằm trong `suspect.index`
     của đúng sản phẩm đó, và KHÔNG được trùng lặp — tránh hoà nhầm dòng nếu
     cột 'Sản phẩm'/'Dòng Excel gốc' bị sửa tay nhầm khi rà soát trong Excel
     (NẾU Short_reviews_Checked.xlsx / Suspect_URL_Spam_Checked.xlsx đã thay
     đổi kể từ lúc run_t216.py chạy, `suspect.index` cũng sẽ khác đi và bước
     validate này sẽ báo lỗi rõ ràng thay vì hoà nhầm dòng).
  5. pd.concat([kept, các dòng đã duyệt]).sort_index() — sort_index() để dòng
     được hoà lại đúng VỊ TRÍ XEN KẼ ban đầu theo thứ tự dòng gốc.
  6. Ghi đè data/interim/{name}_t2.16.xlsx.

Bước 2-5 dùng chung `merge_checked_rows` (pipelines/build_reviewed_t214.py) —
đúng thuật toán mà build_reviewed_t214_dataframe cũng dùng cho 2 vòng rà soát
trước đó, tránh viết lại logic merge/validate 1 lần nữa ở đây.

In ra console SỐ DÒNG đã hoà lại cho mỗi sản phẩm qua core.diff_report.

Đây chỉ là script chạy tay tạm thời, KHÔNG phải một phần của pipeline chính,
CHỈ chạy SAU KHI đã có data/interim/Suspect_Duplicate_Content_Checked.xlsx (rà
soát thủ công từ data/interim/Suspect_Duplicate_Content.xlsx do run_t216.py
sinh ra):
    python Merge_Suspect_Duplicate_Content_Checked.py
"""

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from core.diff_report import print_row_diff
from pipelines.build_reviewed_t214 import build_reviewed_t214_dataframe, merge_checked_rows
from transforms.tang2_content_quality import (
    drop_exact_duplicates,
    split_near_duplicate_reviews,
)

CHECKED_PATH = DATA_INTERIM_DIR / "Suspect_Duplicate_Content_Checked.xlsx"
# Phai khop CHINH XAC voi ten cot ma run_t216.py da dung khi tach/gan nhan
# sang Suspect_Duplicate_Content.xlsx.
PRODUCT_COL = "Sản phẩm"
SOURCE_ROW_COL = "Dòng Excel gốc"

if not CHECKED_PATH.exists():
    raise FileNotFoundError(
        f"Khong tim thay {CHECKED_PATH}. Hay ra soat "
        f"data/interim/Suspect_Duplicate_Content.xlsx (do run_t216.py sinh "
        f"ra) va luu lai dung ten file nay truoc khi chay script."
    )

for name in PRODUCT_FILES:
    before = build_reviewed_t214_dataframe(name)
    after_t215 = drop_exact_duplicates(before)
    kept, suspect = split_near_duplicate_reviews(after_t215)

    out_path = DATA_INTERIM_DIR / f"{name}_t2.16.xlsx"
    merged = merge_checked_rows(kept, suspect, CHECKED_PATH, name, "T2.16")
    merged.to_excel(out_path, index=False)

    print(f"=== {name} -> {out_path} ===")
    print_row_diff(
        kept,
        merged,
        label=f"{name}][Merge_Suspect_Duplicate_Content_Checked",
        excel_row_offset=2,
        max_list=20,
    )
