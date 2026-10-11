"""
scripts/run_stage2.py — chạy lần lượt từng hàm Giai đoạn 2 trên đầu ra Giai
đoạn 1 (data/interim/v1_structured/<tên>_step4_stage1_split_merged_fields.xlsx, sinh bởi run_stage1.py),
mỗi bước ghi ra data/interim/v2_normalized/<tên>_<bước>_stage2_<xử lý gì>.xlsx và in diff theo
số dòng Excel:

    step_extra normalize_unicode_and_html   step16 strip_extra_whitespace
    step17     add_text_norm_column

Bước step_extra/step16 áp lên cả nội dung lẫn các cột tiêu chí đã tách ở T1.6.

Bấm Run trực tiếp hoặc:
    python scripts/run_stage2.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from core.diff_report import print_row_diff
from transforms.stage2_normalize import (
    add_text_norm_column,
    normalize_unicode_and_html,
    strip_extra_whitespace,
    text_columns,
)

IN_DIR = DATA_INTERIM_DIR / "v1_structured"
OUT_DIR = DATA_INTERIM_DIR / "v2_normalized"
STEPS = [
    ("step_extra_stage2_normalize_unicode_html", normalize_unicode_and_html),
    ("step16_stage2_strip_whitespace", strip_extra_whitespace),
    ("step17_stage2_add_text_norm", add_text_norm_column),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in PRODUCT_FILES:
        src = IN_DIR / f"{name}_step4_stage1_split_merged_fields.xlsx"
        if not src.exists():
            print(f"\n[bo qua] {name}: chua co {src} — chay scripts/run_stage1.py truoc")
            continue
        df = pd.read_excel(src)
        print(f"\n########## {name}: {len(df)} dong, cot van ban: {text_columns(df)} ##########")
        for tag, fn in STEPS:
            result = fn(df)
            out_path = OUT_DIR / f"{name}_{tag}.xlsx"
            result.to_excel(out_path, index=False)
            print(f"=== {name} [{tag}] {fn.__name__} -> {out_path} ===")
            print_row_diff(df, result, label=f"{name} {tag}", excel_row_offset=2, max_list=20)
            df = result


if __name__ == "__main__":
    main()
