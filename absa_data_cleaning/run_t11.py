"""
run_t11.py — chạy thử riêng bước T1.1 (sửa lệch cột Tác giả <-> Nội dung tự do)
trên toàn bộ file trong data/raw/ (xem PRODUCT_FILES trong config/settings.py),
ghi kết quả ra data/interim/.

Đây chỉ là script chạy tay tạm thời, KHÔNG phải một phần của pipeline chính.
    python run_t11.py
"""

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from dataio.file_registry import raw_path
from transforms.tang1_structural import fix_field_misalignment

DATA_INTERIM_DIR.mkdir(parents=True, exist_ok=True)

for name in PRODUCT_FILES:
    df = pd.read_excel(raw_path(name))
    fixed = fix_field_misalignment(df)

    changed = (df["Tác giả"].fillna("") != fixed["Tác giả"].fillna("")).sum()
    out_path = DATA_INTERIM_DIR / f"{name}_t1.1.xlsx"
    fixed.to_excel(out_path, index=False)

    print(f"{name}: {changed} dong da sua -> {out_path}")
