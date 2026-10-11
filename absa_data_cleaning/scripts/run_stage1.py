"""
scripts/run_stage1.py — chạy lần lượt từng hàm Giai đoạn 1 trên toàn bộ file
trong data/raw/ (xem PRODUCT_FILES trong config/settings.py), mỗi bước ghi
kết quả ra data/interim/v1_structured/<tên>_<bước>_stage1_<xử lý gì>.xlsx và in diff theo số dòng
Excel (giống run_t11.py):

    step1 fix_field_misalignment   step2 drop_empty_rows
    step3 fix_data_types           step4 split_merged_fields

Tên file: <data gốc>_<bước>_<stage>_<xử lý gì>, vd phone_step2_stage1_drop_empty_rows.xlsx.

Bấm Run trực tiếp hoặc:
    python scripts/run_stage1.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from core.diff_report import print_row_diff
from dataio.file_registry import raw_path
from transforms.stage1_structure import (
    drop_empty_rows,
    fix_data_types,
    fix_field_misalignment,
    split_merged_fields,
)

OUT_DIR = DATA_INTERIM_DIR / "v1_structured"
STEPS = [
    ("step1_stage1_fix_field_misalignment", fix_field_misalignment, None),
    ("step2_stage1_drop_empty_rows", drop_empty_rows, None),
    ("step3_stage1_fix_data_types", fix_data_types, 0),  # đổi kiểu cả cột -> diff gọn, không liệt kê từng dòng
    ("step4_stage1_split_merged_fields", split_merged_fields, None),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in PRODUCT_FILES:
        df = pd.read_excel(raw_path(name))
        print(f"\n########## {name}: {len(df)} dong ##########")
        for tag, fn, max_list in STEPS:
            result = fn(df)
            out_path = OUT_DIR / f"{name}_{tag}.xlsx"
            export = result.copy()
            for col in export.select_dtypes(include="datetimetz").columns:
                export[col] = export[col].dt.tz_localize(None)  # openpyxl không ghi được tz
            export.to_excel(out_path, index=False)
            print(f"=== {name} [{tag}] {fn.__name__} -> {out_path} ===")
            print_row_diff(df, result, label=f"{name} {tag}", excel_row_offset=2, max_list=max_list or 20)
            df = result


if __name__ == "__main__":
    main()
