"""
run_t219.py — chạy TOÀN BỘ chuỗi T1.1 -> T2.19 trên dữ liệu tính lại TỪ ĐẦU
(từ data/raw/), ghi kết quả ra data/interim/.

Nối tiếp run_t218.py: dùng `pipelines.build_reviewed_t218.build_reviewed_t218_dataframe`
để tính lại T1.1 -> T2.18 trong bộ nhớ (tự gộp các file *_Checked.xlsx đã có),
rồi chạy T2.19 `split_spelling_error_reviews` (transforms/tang2_content_quality.py):
TÁCH RIÊNG các dòng có lỗi chính tả được ghi nhận (từ điển
dictionary/spelling_errors.txt + bộ kiểm tra âm tiết tiếng Việt, xem
docstring `fix_spelling_errors`) ra 1 file CHUNG Suspect_Spelling_Errors.xlsx
(có thêm cột 'Sản phẩm' + 'Dòng Excel gốc', giống các file Suspect_* khác).
Trong file đó:
  - 'Nội dung tự do'     : văn gốc, giữ nguyên để đối chiếu.
  - 'Nội dung sau xử lý' : đề xuất đã sửa — CHỈNH TRỰC TIẾP ô này nếu muốn.
  - 'Chi tiết sửa'       : 'từ sai -> từ đúng' để quét nhanh.

Cách kiểm duyệt: mở Suspect_Spelling_Errors.xlsx, sửa 'Nội dung sau xử lý'
(hoặc xoá dòng / để trống ô / chép lại văn gốc để TỪ CHỐI đề xuất), lưu lại
thành Suspect_Spelling_Errors_Checked.xlsx (giữ nguyên các cột), rồi chạy
Merge_Suspect_Spelling_Errors_Checked.py. KHÁC các bước trước: dòng không có
trong file Checked KHÔNG bị xoá, chỉ giữ văn gốc.

{name}_t2.19.xlsx ở bước này chứa ĐỦ dòng, các dòng nghi sai chính tả vẫn giữ
văn gốc cho tới khi có Checked.

Đây chỉ là script chạy tay tạm thời, KHÔNG phải một phần của pipeline chính:
    python run_t219.py
"""

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from pipelines.build_reviewed_t214 import PRODUCT_COL, SOURCE_ROW_COL
from pipelines.build_reviewed_t218 import build_reviewed_t218_dataframe
from pipelines.build_reviewed_t219 import SUSPECT_SPELLING_ERRORS_CHECKED_PATH, apply_spelling_review
from transforms.tang2_content_quality import split_spelling_error_reviews

DATA_INTERIM_DIR.mkdir(parents=True, exist_ok=True)
SUSPECT_PATH = DATA_INTERIM_DIR / "Suspect_Spelling_Errors.xlsx"

all_suspect_rows = []

for name in PRODUCT_FILES:
    before = build_reviewed_t218_dataframe(name)
    kept, suspect = split_spelling_error_reviews(before)

    out_path = DATA_INTERIM_DIR / f"{name}_t2.19.xlsx"
    apply_spelling_review(kept, suspect, SUSPECT_SPELLING_ERRORS_CHECKED_PATH, name).to_excel(out_path, index=False)

    if not suspect.empty:
        tagged = suspect.copy()
        tagged.insert(0, SOURCE_ROW_COL, tagged.index + 2)
        tagged.insert(0, PRODUCT_COL, name)
        all_suspect_rows.append(tagged)

    excel_rows = [int(i) + 2 for i in suspect.index]
    print(f"=== {name} -> {out_path} ({len(suspect)}/{len(before)} dong nghi sai chinh ta) ===")
    print(f"    dong Excel: {excel_rows[:20]}{' ...' if len(excel_rows) > 20 else ''}")

if all_suspect_rows:
    suspect_df = pd.concat(all_suspect_rows, ignore_index=True)
    suspect_df.to_excel(SUSPECT_PATH, index=False)
    print(f"=== {SUSPECT_PATH} ({len(suspect_df)} dong nghi sai chinh ta tu {len(all_suspect_rows)} san pham) ===")
else:
    print("=== Khong co dong nao nghi sai chinh ta — khong tao Suspect_Spelling_Errors.xlsx ===")
