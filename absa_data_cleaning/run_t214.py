"""
run_t214.py — chạy T2.13+T2.14 trên dữ liệu SAU KHI đã merge review ngắn được
duyệt thủ công, ghi kết quả ra data/interim/.

BỐI CẢNH: khác với run_t29.py/run_t212.py (chạy lại toàn bộ chuỗi từ
data/raw/), script này KHÔNG đụng tới data/raw/ hay Short_reviews.xlsx.
Input là data/interim/{name}_t2.12.xlsx — file ĐÃ được run_t212.py sinh ra
RỒI Merge_Short_Reviews_Checked.py ghi đè lại sau khi hoà (concat) các review
ngắn đã rà soát thủ công vào. PHẢI chạy Merge_Short_Reviews_Checked.py xong
trước khi chạy script này.

Bước xử lý (cho từng sản phẩm `name` trong PRODUCT_FILES):
  T2.13+T2.14 split_url_hotline_or_spam_reviews (transforms/tang2_content_quality.py)
  — GIỐNG TINH THẦN T2.11+T2.12: KHÔNG tự động xoá, chỉ TÁCH RIÊNG dòng khi
  'Nội dung tự do' HOẶC 'Tiêu chí đánh giá' có chứa URL hoặc số điện thoại
  (kiểm tra CẢ 2 cột — dùng CHUNG 1 bộ lọc regex cho cả 2 mục T2.13 và
  T2.14, xem docstring hàm để biết lý do vì sao KHÔNG áp dụng nguyên tắc "cả
  2 cột cùng rỗng" như T2.9+T2.10/T2.11+T2.12, và vì sao CỐ TÌNH KHÔNG bắt
  theo từ khoá 'zalo'/'ib'/'hotline' đứng riêng — dễ tách nhầm review thật
  nhắc tới các từ này mà không phải quảng cáo) ra khỏi từng file sản phẩm,
  gộp CHUNG với review nghi vấn từ TẤT CẢ sản phẩm khác vào 1 file
  `Suspect_URL_Spam.xlsx` duy nhất (có thêm cột 'Sản phẩm' + 'Dòng Excel
  gốc') — con người tự rà soát thủ công nhóm này sau, lưu lại thành
  `Suspect_URL_Spam_Checked.xlsx` (đúng quy ước như Short_reviews_Checked.xlsx
  — XOÁ HẲN dòng không muốn giữ, chỉ còn lại dòng muốn hoà trở lại), rồi chạy
  Merge_Suspect_URL_Spam_Checked.py để hoà lại vào {name}_t2.14.xlsx.

  LƯU Ý 'Dòng Excel gốc' ở đây tính theo vị trí dòng trong CHÍNH file
  {name}_t2.12.xlsx (đọc lại từ đĩa, index 0-based reset bởi pd.read_excel),
  KHÔNG phải số dòng trong file raw gốc — vì input của bước này không còn là
  data/raw/ nữa. Merge_Suspect_URL_Spam_Checked.py cũng đọc lại đúng file
  {name}_t2.12.xlsx này để khôi phục index nên vẫn khớp nhau.

In ra console SỐ DÒNG CỤ THỂ đã bị TÁCH, theo đúng số dòng khi mở file .xlsx
bằng Excel (excel_row_offset=2).

Đây chỉ là script chạy tay tạm thời, KHÔNG phải một phần của pipeline chính,
CHỈ chạy SAU KHI đã có data/interim/{name}_t2.12.xlsx (đã merge xong):
    python run_t214.py
"""

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from core.diff_report import print_row_diff
from transforms.tang2_content_quality import split_url_hotline_or_spam_reviews

DATA_INTERIM_DIR.mkdir(parents=True, exist_ok=True)
SUSPECT_PATH = DATA_INTERIM_DIR / "Suspect_URL_Spam.xlsx"
PRODUCT_COL = "Sản phẩm"
SOURCE_ROW_COL = "Dòng Excel gốc"

all_suspect_rows = []

for name in PRODUCT_FILES:
    in_path = DATA_INTERIM_DIR / f"{name}_t2.12.xlsx"
    if not in_path.exists():
        raise FileNotFoundError(
            f"Khong tim thay {in_path}. Hay chay run_t212.py roi "
            f"Merge_Short_Reviews_Checked.py truoc (T2.13+T2.14 chay tren du "
            f"lieu SAU KHI da hoa lai review ngan duoc duyet thu cong)."
        )

    before = pd.read_excel(in_path)
    kept, suspect = split_url_hotline_or_spam_reviews(before)

    out_path = DATA_INTERIM_DIR / f"{name}_t2.14.xlsx"
    kept.to_excel(out_path, index=False)

    if not suspect.empty:
        tagged_suspect = suspect.copy()
        tagged_suspect.insert(0, SOURCE_ROW_COL, tagged_suspect.index + 2)
        tagged_suspect.insert(0, PRODUCT_COL, name)
        all_suspect_rows.append(tagged_suspect)

    print(f"=== {name} -> {out_path} ===")
    print_row_diff(before, kept, label=f"{name}][T2.13+T2.14 (tach ra Suspect_URL_Spam)", excel_row_offset=2, max_list=20)

if all_suspect_rows:
    suspect_df = pd.concat(all_suspect_rows, ignore_index=True)
    suspect_df.to_excel(SUSPECT_PATH, index=False)
    print(f"=== {SUSPECT_PATH} ({len(suspect_df)} dong nghi van URL/spam tu {len(all_suspect_rows)} san pham) ===")
else:
    print("=== Khong co dong nao nghi van URL/spam — khong tao Suspect_URL_Spam.xlsx ===")
