"""
run_t216.py — chạy T2.15+T2.16 trên dữ liệu tính lại TỪ ĐẦU (từ data/raw/),
ghi kết quả ra data/interim/.

KHÁC VỚI PHIÊN BẢN BAN ĐẦU: script này KHÔNG còn đọc thẳng
data/interim/{name}_t2.14.xlsx trên đĩa (vốn ngầm giả định run_t212.py ->
Merge_Short_Reviews_Checked.py -> run_t214.py -> Merge_Suspect_URL_Spam_Checked.py
đã chạy ĐÚNG THỨ TỰ và ĐÃ XONG cả 2 vòng rà soát thủ công — nếu lỡ chạy
run_t216.py trước khi 1 trong 2 vòng đó hoàn tất, kết quả sẽ dựa trên dữ liệu
THIẾU mà không có cảnh báo gì). Thay vào đó, dùng
`pipelines.build_reviewed_t214.build_reviewed_t214_dataframe` để tính lại
TOÀN BỘ chuỗi T1.1 -> T2.14 từ data/raw/ NGAY TRONG BỘ NHỚ mỗi lần chạy (xem
docstring file đó để biết lý do kỹ thuật) — tự gộp
Short_reviews_Checked.xlsx / Suspect_URL_Spam_Checked.xlsx NẾU đã tồn tại, và
IN CẢNH BÁO RÕ RÀNG nếu 1 trong 2 file đó CHƯA có (khi đó kết quả T2.15/T2.16
là TẠM THỜI — cần chạy lại run_t216.py sau khi rà soát xong).

Bước xử lý (cho từng sản phẩm `name` trong PRODUCT_FILES):
  T2.15 drop_exact_duplicates (transforms/tang2_content_quality.py) — XOÁ HẲN
  (tự động, KHÔNG cần rà soát thủ công) các dòng trùng lặp TUYỆT ĐỐI theo
  'Nội dung tự do' + 'Tác giả' (dấu hiệu chắc chắn của lỗi crawl trùng cùng 1
  review nhiều lần — xem docstring hàm để biết lý do vì sao mục này KHÔNG đi
  theo hướng "chỉ tách" như đa số các mục 2.1 khác).

  T2.16 split_near_duplicate_reviews — GIỐNG TINH THẦN T2.11+T2.12/T2.13+T2.14:
  KHÔNG tự động xoá, chỉ TÁCH RIÊNG cặp dòng NGHI VẤN gần trùng nội dung
  ('Nội dung tự do' có similarity >= NEAR_DUPLICATE_SIMILARITY_THRESHOLD, xem
  config/settings.py) GIỮA 2 TÁC GIẢ KHÁC NHAU, gộp CHUNG với dòng nghi vấn từ
  TẤT CẢ sản phẩm khác vào 1 file `Suspect_Duplicate_Content.xlsx` duy nhất
  (có thêm cột 'Sản phẩm' + 'Dòng Excel gốc') — con người tự rà soát thủ công
  nhóm này sau, lưu lại thành `Suspect_Duplicate_Content_Checked.xlsx` (đúng
  quy ước như Suspect_URL_Spam_Checked.xlsx — XOÁ HẲN dòng không muốn giữ, chỉ
  còn lại dòng muốn hoà trở lại), rồi chạy
  Merge_Suspect_Duplicate_Content_Checked.py để hoà lại vào {name}_t2.16.xlsx.

  LƯU Ý 'Dòng Excel gốc' ở đây tính theo vị trí dòng trong DataFrame do
  `build_reviewed_t214_dataframe(name)` TRẢ VỀ (index giữ nguyên xuyên suốt từ
  lúc đọc raw/ — các hàm transforms đều là hàm thuần giữ nguyên index gốc).
  `build_reviewed_t214_dataframe` PHỤ THUỘC DUY NHẤT vào data/raw/ + 2 file đã
  duyệt (nếu có) nên gọi lại nhiều lần (vd từ Merge_Suspect_Duplicate_Content_Checked.py
  sau này) LUÔN cho index giống hệt, miễn là data/raw/ và 2 file Checked đó
  không đổi giữa 2 lần chạy.

  KHÔNG SỬA run_t212.py/run_t214.py/Merge_Short_Reviews_Checked.py/
  Merge_Suspect_URL_Spam_Checked.py — các script đó vẫn hoạt động độc lập như
  cũ (đọc/ghi {name}_t2.12.xlsx/{name}_t2.14.xlsx trên đĩa) cho ai muốn chạy
  từng bước riêng lẻ; run_t216.py chỉ không CÒN PHỤ THUỘC chúng phải chạy
  trước nữa.

In ra console SỐ DÒNG CỤ THỂ đã bị XOÁ/TÁCH, theo đúng số dòng khi mở file
.xlsx bằng Excel (excel_row_offset=2).

Đây chỉ là script chạy tay tạm thời, KHÔNG phải một phần của pipeline chính,
CHỈ cần có data/raw/ (2 file Checked là TUỲ CHỌN — thiếu vẫn chạy được, chỉ in
cảnh báo kết quả tạm thời):
    python run_t216.py
"""

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from core.diff_report import print_row_diff
from pipelines.build_reviewed_t214 import build_reviewed_t214_dataframe
from transforms.tang2_content_quality import (
    drop_exact_duplicates,
    split_near_duplicate_reviews,
)

DATA_INTERIM_DIR.mkdir(parents=True, exist_ok=True)
SUSPECT_PATH = DATA_INTERIM_DIR / "Suspect_Duplicate_Content.xlsx"
PRODUCT_COL = "Sản phẩm"
SOURCE_ROW_COL = "Dòng Excel gốc"

all_suspect_rows = []

for name in PRODUCT_FILES:
    before = build_reviewed_t214_dataframe(name)
    after_t215 = drop_exact_duplicates(before)
    kept, suspect = split_near_duplicate_reviews(after_t215)

    out_path = DATA_INTERIM_DIR / f"{name}_t2.16.xlsx"
    kept.to_excel(out_path, index=False)

    if not suspect.empty:
        tagged_suspect = suspect.copy()
        tagged_suspect.insert(0, SOURCE_ROW_COL, tagged_suspect.index + 2)
        tagged_suspect.insert(0, PRODUCT_COL, name)
        all_suspect_rows.append(tagged_suspect)

    print(f"=== {name} -> {out_path} ===")
    print_row_diff(before, after_t215, label=f"{name}][T2.15 (xoa trung lap tuyet doi)", excel_row_offset=2, max_list=20)
    print_row_diff(after_t215, kept, label=f"{name}][T2.16 (tach ra Suspect_Duplicate_Content)", excel_row_offset=2, max_list=20)

if all_suspect_rows:
    suspect_df = pd.concat(all_suspect_rows, ignore_index=True)
    suspect_df.to_excel(SUSPECT_PATH, index=False)
    print(f"=== {SUSPECT_PATH} ({len(suspect_df)} dong nghi van gan trung noi dung tu {len(all_suspect_rows)} san pham) ===")
else:
    print("=== Khong co dong nao nghi van gan trung noi dung — khong tao Suspect_Duplicate_Content.xlsx ===")
