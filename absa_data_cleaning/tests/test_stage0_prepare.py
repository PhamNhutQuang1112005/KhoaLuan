"""
tests/test_stage0_prepare.py
==============================
Test cho transforms/stage0_prepare.py (Giai đoạn 0 — gán review_id).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest

from transforms.stage0_prepare import REVIEW_ID_COL, REVIEW_RAW_COL, assign_review_id


def _df():
    return pd.DataFrame(
        {"Tác giả": ["a", "b", "c"], "Nội dung tự do": ["Hàng đẹp", None, "giao nhanh"]},
        index=[10, 5, 7],
    )


def test_assigns_unique_sequential_ids_by_position():
    result = assign_review_id(_df(), "phone")

    assert list(result[REVIEW_ID_COL]) == ["phone_00001", "phone_00002", "phone_00003"]
    assert result[REVIEW_ID_COL].is_unique


def test_ids_are_stable_across_runs():
    assert assign_review_id(_df(), "phone")[REVIEW_ID_COL].equals(assign_review_id(_df(), "phone")[REVIEW_ID_COL])


def test_review_raw_copies_content_and_new_columns_come_first():
    result = assign_review_id(_df(), "ao")

    assert list(result.columns[:2]) == [REVIEW_ID_COL, REVIEW_RAW_COL]
    assert result[REVIEW_RAW_COL].iloc[0] == "Hàng đẹp"
    assert pd.isna(result[REVIEW_RAW_COL].iloc[1])
    assert result[REVIEW_RAW_COL].iloc[2] == "giao nhanh"


def test_keeps_original_index_and_does_not_mutate_input():
    df = _df()
    result = assign_review_id(df, "ao")

    assert list(result.index) == [10, 5, 7]
    assert REVIEW_ID_COL not in df.columns


def test_missing_content_col_gives_na_review_raw():
    result = assign_review_id(pd.DataFrame({"Tác giả": ["a"]}), "vo")

    assert result[REVIEW_RAW_COL].isna().all()


def test_raises_when_review_id_already_present():
    with pytest.raises(ValueError):
        assign_review_id(assign_review_id(_df(), "phone"), "phone")


def test_empty_dataframe():
    result = assign_review_id(pd.DataFrame({"Nội dung tự do": []}), "pin")

    assert result.empty
    assert REVIEW_ID_COL in result.columns


if __name__ == "__main__":  # bấm Run trực tiếp file này
    sys.exit(pytest.main([__file__, "-v", "--rootdir", str(Path(__file__).resolve().parent.parent)]))
