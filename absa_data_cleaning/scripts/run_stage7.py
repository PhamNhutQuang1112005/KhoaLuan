"""
scripts/run_stage7.py — chạy Giai đoạn 7 (khử trùng lặp lần cuối & kiểm tra) trên đầu ra Giai đoạn 5
(data/interim/v5_length_filtered/<tên>_step6_stage5_filter_short_reviews.xlsx; Giai đoạn 6 chỉ liệt kê
token nghi vấn, không sửa câu nên không có đầu ra dữ liệu), ghi ra data/interim/v7_final/ và in diff
theo số dòng Excel:

    step8b  split_near_duplicate_reviews     gần trùng trong file, khác tác giả (+ file suspect_near_duplicates)
    step21b split_cross_file_near_duplicates giữa các file (+ file suspect_cross_file_duplicates, gộp mọi sản phẩm)
    step24  final_check                      (sau drop_empty_rows) chạy lại bước 16, 17; không còn dòng trống; khớp số dòng
                                             -> data/processed/<tên>_step24_stage7_final_check.xlsx (= v7_final)

Không xoá mất dòng: cả 2 dòng của mỗi cặp nghi trùng vào file suspect để kiểm duyệt thủ công (giữ lại
1 bản; merge lại theo review_id). step21b cần mọi file cùng lúc nên chạy sau step8b của tất cả file.

    python scripts/run_stage7.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from config.settings import DATA_INTERIM_DIR, DATA_PROCESSED_DIR, PRODUCT_FILES
from core.diff_report import print_row_diff
from transforms.stage1_structure import drop_empty_rows
from transforms.stage2_normalize import TEXT_NORM_COL
from transforms.stage7_final_dedup import (
    final_check,
    split_cross_file_near_duplicates,
    split_near_duplicate_reviews,
)

IN_DIR = DATA_INTERIM_DIR / "v5_length_filtered"
OUT_DIR = DATA_INTERIM_DIR / "v7_final"
FINAL_DIR = DATA_PROCESSED_DIR


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    dfs = {}
    for name in PRODUCT_FILES:
        src = IN_DIR / f"{name}_step6_stage5_filter_short_reviews.xlsx"
        if not src.exists():
            print(f"\n[bo qua] {name}: chua co {src} — chay scripts/run_stage5.py truoc")
            continue
        dfs[name] = pd.read_excel(src)

    tag = "step8b_stage7_filter_near_duplicates"
    after = {}
    for name, df in dfs.items():
        kept, suspect = split_near_duplicate_reviews(df, content_col=TEXT_NORM_COL)
        suspect.to_excel(OUT_DIR / f"{name}_step8b_stage7_suspect_near_duplicates.xlsx", index=False)
        print(f"[{name}] step8b: {len(suspect)} dong can kiem duyet thu cong")
        kept.to_excel(OUT_DIR / f"{name}_{tag}.xlsx", index=False)
        print_row_diff(df, kept, label=f"{name} {tag}", excel_row_offset=2, max_list=20)
        after[name] = kept

    tag = "step21b_stage7_filter_cross_file_duplicates"
    kept_all, suspect = split_cross_file_near_duplicates(after)
    path = OUT_DIR / "step21b_stage7_suspect_cross_file_duplicates.xlsx"
    suspect.to_excel(path, index=False)
    print(f"\nstep21b: {len(suspect)} dong can kiem duyet thu cong -> {path}")
    for name, kept in kept_all.items():
        kept.to_excel(OUT_DIR / f"{name}_{tag}.xlsx", index=False)
        print_row_diff(after[name], kept, label=f"{name} {tag}", excel_row_offset=2, max_list=20)

    tag = "step24_stage7_final_check"
    total = 0
    for name, df in kept_all.items():
        # an toan: file v1 cu co the con dong trong (non: 1 dong) -> loai theo luat T1.2+T1.3 truoc khi kiem tra
        cleaned = drop_empty_rows(df)
        print_row_diff(df, cleaned, label=f"{name} drop_empty_rows", excel_row_offset=2, max_list=20)
        final = final_check(cleaned, expected_rows=len(cleaned))
        final.to_excel(FINAL_DIR / f"{name}_{tag}.xlsx", index=False)
        total += len(final)
        print(f"[{name}] {tag}: {len(final)} dong -> {FINAL_DIR / f'{name}_{tag}.xlsx'}")
    print(f"\nTong v7_final: {total} dong")


if __name__ == "__main__":
    main()
