"""
scripts/run_stage0.py — chạy Giai đoạn 0 trên toàn bộ file trong data/raw/
(xem PRODUCT_FILES trong config/settings.py): gán `review_id` + `review_raw`,
ghi checkpoint ra data/interim/v0_raw/<tên>_step0_stage0_assign_review_id.xlsx.

Tên file đầu ra: <data gốc>_<bước>_<stage>_<xử lý gì>.

Bấm Run trực tiếp hoặc:
    python scripts/run_stage0.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from dataio.file_registry import raw_path
from transforms.stage0_prepare import REVIEW_ID_COL, REVIEW_RAW_COL, assign_review_id

OUT_DIR = DATA_INTERIM_DIR / "v0_raw"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in PRODUCT_FILES:
        raw = pd.read_excel(raw_path(name))
        out = assign_review_id(raw, name)
        assert out[REVIEW_ID_COL].is_unique and len(out) == len(raw)

        out_path = OUT_DIR / f"{name}_step0_stage0_assign_review_id.xlsx"
        out.to_excel(out_path, index=False)
        print(f"{name}: {len(out)} dong, {out[REVIEW_ID_COL].iloc[0]} .. {out[REVIEW_ID_COL].iloc[-1]} -> {out_path}")


if __name__ == "__main__":
    main()
