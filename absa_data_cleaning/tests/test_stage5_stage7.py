"""Test Giai đoạn 7: gần trùng giữa file (21b) và kiểm tra cuối. (8b, GĐ5 đã có ở test_stage_text_transforms.py)"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from transforms.stage7_final_dedup import final_check, split_cross_file_near_duplicates

C, A, T = "Nội dung tự do", "Tác giả", "text_norm"


def test_cross_file_flags_both_sides_regardless_of_author_not_same_file():
    a = pd.DataFrame({C: ["x", "y", "z"], A: ["u1", "u2", "u3"],
                      T: ["giao hàng nhanh, đóng gói đẹp", "giao hàng nhanh, đóng gói đẹp!", "pin trâu lắm"]})
    b = pd.DataFrame({C: ["x", "y"], A: ["u1", "u9"], T: ["giao hàng nhanh đóng gói đẹp", None]})
    kept, suspect = split_cross_file_near_duplicates({"a": a, "b": b}, similarity_threshold=0.9)
    assert list(kept["a"].index) == [2] and list(kept["b"].index) == [1]  # a0,a1 chỉ trùng nhau => cùng file, nhưng cùng khớp b0
    assert sorted(zip(suspect["Nguồn file"], suspect["Dòng Excel đầu vào"])) == [("a", 2), ("a", 3), ("b", 2)]


def test_cross_file_same_file_pair_not_flagged():
    a = pd.DataFrame({C: ["x", "y"], A: ["u1", "u2"], T: ["hàng rất đẹp nhé", "hàng rất đẹp nhé"]})
    kept, suspect = split_cross_file_near_duplicates({"a": a})
    assert len(kept["a"]) == 2 and suspect.empty


def test_final_check():
    df = pd.DataFrame({C: ["  hàng   đẹp ", "ổn"], "Tiêu chí đánh giá": [None, None]})
    out = final_check(df, expected_rows=2)
    assert list(out[C]) == ["hàng đẹp", "ổn"] and list(out[T]) == ["hàng đẹp", "ổn"]
    with pytest.raises(ValueError):
        final_check(df, expected_rows=3)
    with pytest.raises(ValueError):
        final_check(pd.DataFrame({C: ["ok", None], "Tiêu chí đánh giá": [None, None]}))
