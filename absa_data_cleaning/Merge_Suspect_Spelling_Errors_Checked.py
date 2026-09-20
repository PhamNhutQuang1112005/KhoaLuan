"""
Merge_Suspect_Spelling_Errors_Checked.py — áp kết quả kiểm duyệt chính tả
(data/interim/Suspect_Spelling_Errors_Checked.xlsx) vào data/interim/{name}_t2.19.xlsx.

Quy ước file Checked + cách từ chối đề xuất: xem docstring run_t219.py và
pipelines/build_reviewed_t219.py. CHỈ chạy SAU KHI đã có file Checked:
    python Merge_Suspect_Spelling_Errors_Checked.py
"""

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from core.diff_report import print_row_diff
from pipelines.build_reviewed_t218 import build_reviewed_t218_dataframe
from pipelines.build_reviewed_t219 import SUSPECT_SPELLING_ERRORS_CHECKED_PATH, build_reviewed_t219_dataframe

if not SUSPECT_SPELLING_ERRORS_CHECKED_PATH.exists():
    raise FileNotFoundError(
        f"Khong tim thay {SUSPECT_SPELLING_ERRORS_CHECKED_PATH}. Hay ra soat "
        f"data/interim/Suspect_Spelling_Errors.xlsx (do run_t219.py sinh ra) "
        f"va luu lai dung ten file nay truoc khi chay script."
    )

for name in PRODUCT_FILES:
    before = build_reviewed_t218_dataframe(name)
    after = build_reviewed_t219_dataframe(name)
    out_path = DATA_INTERIM_DIR / f"{name}_t2.19.xlsx"
    after.to_excel(out_path, index=False)

    print(f"=== {name} -> {out_path} ===")
    print_row_diff(before, after, label=f"{name}][T2.19 (ap ban sua chinh ta da duyet)", excel_row_offset=2, max_list=20)
