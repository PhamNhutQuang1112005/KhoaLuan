"""
scripts/run_stage5.py — chạy Giai đoạn 5 (lọc review quá ngắn) trên đầu ra Giai đoạn 4
(data/interim/v4_char_cleaned/<tên>_step17_stage4_refresh_text_norm.xlsx), ghi ra
data/interim/v5_length_filtered/ và in diff theo số dòng Excel:

    step6  split_short_reviews   review <= 4 từ VÀ 'Tiêu chí đánh giá' rỗng (+ file suspect_short_reviews)

Không xoá mất dòng: dòng ngắn được lưu ra file suspect để kiểm duyệt thủ công (giữ lại câu ngắn có
khía cạnh rõ như "giao nhanh, pin trâu"; nếu loại nhầm thì merge lại theo review_id). Kết quả cuối mỗi
file: <tên>_step6_stage5_filter_short_reviews.xlsx (= v5_length_filtered).

    python scripts/run_stage5.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from core.diff_report import print_row_diff
from transforms.stage5_short_filter import split_short_reviews

IN_DIR = DATA_INTERIM_DIR / "v4_char_cleaned"
OUT_DIR = DATA_INTERIM_DIR / "v5_length_filtered"
TAG = "step6_stage5_filter_short_reviews"
SUSPECT_TAG = "step6_stage5_suspect_short_reviews"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in PRODUCT_FILES:
        src = IN_DIR / f"{name}_step17_stage4_refresh_text_norm.xlsx"
        if not src.exists():
            print(f"\n[bo qua] {name}: chua co {src} — chay scripts/run_stage4.py truoc")
            continue
        df = pd.read_excel(src)
        kept, short = split_short_reviews(df)
        short.to_excel(OUT_DIR / f"{name}_{SUSPECT_TAG}.xlsx", index=False)
        print(f"[{name}] {SUSPECT_TAG}: {len(short)} dong can kiem duyet thu cong")
        out_path = OUT_DIR / f"{name}_{TAG}.xlsx"
        kept.to_excel(out_path, index=False)
        print(f"=== {name} [{TAG}] split_short_reviews -> {out_path} ===")
        print_row_diff(df, kept, label=f"{name} {TAG}", excel_row_offset=2, max_list=20)


if __name__ == "__main__":
    main()
