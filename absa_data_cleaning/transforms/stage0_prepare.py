"""
transforms/stage0_prepare.py
==============================
GIAI ĐOẠN 0 — CHUẨN BỊ (bắt buộc làm trước mọi bước).

  - Gán `review_id` duy nhất cho mọi dòng + giữ nguyên cột `review_raw`.
    Tách file -> kiểm duyệt -> merge lại chỉ an toàn khi merge theo ID, không
    merge theo nội dung hay số thứ tự dòng.
  - Lưu checkpoint sau mỗi giai đoạn (v0_raw, v1_structured, ...) + log số
    dòng xoá/sửa từng bước: xem `dataio.checkpoint.save_checkpoint` và
    `core.report.CleaningReport`.

LƯU Ý: các script Merge_*_Checked.py (scripts/legacy/) hiện vẫn merge theo
'Dòng Excel gốc' (vị trí dòng) — chưa chuyển sang `review_id`.

Checkpoint sau giai đoạn: v0_raw.
"""

import pandas as pd

from transforms.stage1_structure import CONTENT_COL

REVIEW_ID_COL = "review_id"
REVIEW_RAW_COL = "review_raw"


def assign_review_id(df: pd.DataFrame, product: str, content_col: str = CONTENT_COL) -> pd.DataFrame:
    """Thêm cột `REVIEW_ID_COL` (duy nhất, ổn định giữa các lần chạy — vd
    '<product>_<số thứ tự dòng raw>') và `REVIEW_RAW_COL` (bản sao nguyên văn
    `content_col` trước mọi xử lý). Chạy NGAY trên data/raw/.

    ID = '<product>_<thứ tự dòng, bắt đầu từ 1, đệm 5 chữ số>' (vd 'phone_00001')
    — tính theo VỊ TRÍ dòng trong `df`, không theo index, nên cùng 1 file raw
    luôn sinh cùng bộ ID. 2 cột mới được chèn lên đầu bảng.

    Raise ValueError nếu `df` đã có `REVIEW_ID_COL` (tránh gán lại ID ở dữ
    liệu đã qua xử lý — ID phải sinh 1 lần duy nhất trên raw). Nếu
    `content_col` không tồn tại: `REVIEW_RAW_COL` toàn NA.

    Hàm thuần: không sửa `df` gốc, giữ nguyên index.
    """
    if REVIEW_ID_COL in df.columns:
        raise ValueError(f"df da co cot '{REVIEW_ID_COL}' — chi gan ID 1 lan tren du lieu raw.")

    out = df.copy()
    raw = out[content_col] if content_col in out.columns else pd.Series(pd.NA, index=out.index)
    out.insert(0, REVIEW_RAW_COL, raw)
    out.insert(0, REVIEW_ID_COL, [f"{product}_{i:05d}" for i in range(1, len(out) + 1)])
    return out
