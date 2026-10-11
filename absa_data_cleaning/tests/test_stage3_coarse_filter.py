"""Test 2 hàm Giai đoạn 3 bổ sung (các hàm còn lại đã có ở test_stage_text_transforms.py)."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from transforms.stage3_coarse_filter import drop_exact_duplicates_across_files, split_non_vietnamese_reviews

C, A = "Nội dung tự do", "Tác giả"


def test_across_files_keeps_first_file_and_respects_author():
    a = pd.DataFrame({C: ["Hàng đẹp", "Ổn"], A: ["u*1", "ẩn danh"], "text_norm": ["hàng đẹp", "ổn"]})
    b = pd.DataFrame({C: ["HÀNG ĐẸP", "Ổn", "Hàng đẹp"], A: ["u*1", "ẩn danh", "u*2"],
                      "text_norm": ["hàng đẹp", "ổn", "hàng đẹp"]})
    out = drop_exact_duplicates_across_files({"a": a, "b": b})
    assert len(out["a"]) == 2
    assert list(out["b"].index) == [1, 2]  # (u*1, 'hàng đẹp') bị xoá; ẩn danh và u*2 giữ


def test_non_vietnamese_split():
    df = pd.DataFrame({C: ["Hàng đẹp", "hang dep lam", "great quality very good", "good", "ok", "质量很好", None]})
    kept, suspect = split_non_vietnamese_reviews(df)
    assert list(kept.index) == [0, 1, 4, 6]
    assert list(suspect.index) == [2, 3, 5]  # không xoá tự động dòng nào
