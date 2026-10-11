"""
tests/test_stage2_normalize.py
================================
Test Giai đoạn 2. Đầu vào được dựng bằng cách chạy THẬT Giai đoạn 1 (kể cả
T1.6 tách tiêu chí) trên 1 DataFrame thô nhỏ, để kiểm tra stage 2 chạy đúng
trên cả cột 'Nội dung tự do' lẫn các cột tiêu chí đã tách.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from transforms.stage1_structure import (
    drop_empty_rows,
    fix_data_types,
    fix_field_misalignment,
    split_merged_fields,
)
from transforms.stage2_normalize import (
    TEXT_NORM_COL,
    add_text_norm_column,
    normalize_unicode_and_html,
    strip_extra_whitespace,
    text_columns,
)
from transforms.utils_text import normalize_unicode
from transforms.utils_text import strip_extra_whitespace as strip_ws

OLD_HOA = "hoà"  # 'hoà' — dấu thanh kiểu cũ
NEW_HOA = "hòa"  # 'hòa'
OLD_THUY = "thuỷ"  # 'thuỷ'
NEW_THUY = "thủy"  # 'thủy'


def _stage1_output() -> pd.DataFrame:
    raw = pd.DataFrame(
        {
            "Tác giả": ["a*****1", "b*****2", "c*****3", "d*****4"],
            "Thời gian": ["2025-12-17 01:38"] * 4,
            "Loại hàng (phân loại)": ["Đen  "] * 4,
            "Tiêu chí đánh giá": [
                f"Hiệu suất:  mượt   mà\nThiết kế: {OLD_HOA} nhã",
                "Hiệu suất: <b>nhanh</b>\nThiết kế: đẹp",
                "Hiệu suất: tốt\nThiết kế: ok",
                None,
            ],
            "Nội dung tự do": [
                f"Máy {OLD_HOA}   đẹp​  &amp; mượt <br>  rất {OLD_THUY}  chung",
                "  Giao nhanh  \n\n\n  đóng gói kỹ <3 giá < 5tr ",
                "ok",
                "Chỉ có nội dung",
            ],
            "Số sao": [5, 4, 5, 3],
            "URL sản phẩm": ["http://x.vn/a&amp;b"] * 4,
            "Thời điểm cào": ["2026-08-22T13:40:30.954Z"] * 4,
        }
    )
    df = fix_field_misalignment(raw)
    df = drop_empty_rows(df)
    df = fix_data_types(df)
    return split_merged_fields(df, min_rows=2)


def test_text_columns_include_split_criteria_but_not_metadata():
    df = _stage1_output()
    cols = text_columns(df)
    assert {"Nội dung tự do", "Tiêu chí đánh giá", "Hiệu suất", "Thiết kế"} <= set(cols)
    for meta in ("Tác giả", "Thời gian", "Số sao", "URL sản phẩm", "Thời điểm cào", "Loại hàng (phân loại)"):
        assert meta not in cols


def test_normalize_unicode_scalar_cases():
    assert normalize_unicode(OLD_HOA) == NEW_HOA
    assert normalize_unicode(OLD_THUY) == NEW_THUY
    assert normalize_unicode("quý") == "quý"  # 'quý' giữ nguyên
    assert normalize_unicode("toán") == "toán"  # 'toán' có âm cuối, giữ nguyên
    assert normalize_unicode("á") == "á"  # NFD -> NFC
    assert normalize_unicode("a<br>b <3 < 5tr") == "a\nb <3 < 5tr"
    assert normalize_unicode("A &amp; B") == "A & B"
    assert normalize_unicode(None) is None


def test_strip_whitespace_scalar_cases():
    assert strip_ws("  a   b\t c  ") == "a b c"
    assert strip_ws("x  \n\n\n  y") == "x\ny"
    assert strip_ws("a\r\nb") == "a\nb"


def test_normalize_applies_to_content_and_split_criteria_columns():
    df = _stage1_output()
    out = normalize_unicode_and_html(df)
    assert out.loc[0, "Thiết kế"] == f"{NEW_HOA} nhã"
    assert out.loc[1, "Hiệu suất"] == "nhanh"  # thẻ HTML ở cột đã tách
    assert out.loc[1, "Tiêu chí đánh giá"] == "Hiệu suất: nhanh\nThiết kế: đẹp"
    content = out.loc[0, "Nội dung tự do"]
    assert NEW_HOA in content and NEW_THUY in content and "&" in content and "​" not in content
    assert "<3 giá < 5tr" in out.loc[1, "Nội dung tự do"]
    # cột không phải văn bản review giữ nguyên
    assert out["URL sản phẩm"].tolist() == df["URL sản phẩm"].tolist()
    assert out["Tác giả"].tolist() == df["Tác giả"].tolist()


def test_strip_whitespace_applies_to_split_columns_and_keeps_na():
    df = normalize_unicode_and_html(_stage1_output())
    out = strip_extra_whitespace(df)
    assert out.loc[0, "Hiệu suất"] == "mượt mà"
    assert out.loc[1, "Nội dung tự do"] == "Giao nhanh\nđóng gói kỹ <3 giá < 5tr"
    assert pd.isna(out.loc[3, "Hiệu suất"]) and pd.isna(out.loc[3, "Thiết kế"])
    assert out["Loại hàng (phân loại)"].tolist() == df["Loại hàng (phân loại)"].tolist()  # không phải cột review
    assert out["Hiệu suất"].dtype == df["Hiệu suất"].dtype


def test_whitespace_only_cell_becomes_na():
    df = pd.DataFrame({"Nội dung tự do": ["​ ", "ok"]})
    out = strip_extra_whitespace(normalize_unicode_and_html(df))
    assert pd.isna(out.loc[0, "Nội dung tự do"]) and out.loc[1, "Nội dung tự do"] == "ok"


def test_text_norm_lowercases_without_touching_content():
    df = strip_extra_whitespace(normalize_unicode_and_html(_stage1_output()))
    out = add_text_norm_column(df)
    assert list(out.columns).index(TEXT_NORM_COL) == list(out.columns).index("Nội dung tự do") + 1
    assert out.loc[3, TEXT_NORM_COL] == "chỉ có nội dung"
    assert out["Nội dung tự do"].tolist() == df["Nội dung tự do"].tolist()
    assert add_text_norm_column(out).columns.tolist() == out.columns.tolist()  # idempotent


def test_pure_functions_do_not_mutate_input():
    df = _stage1_output()
    snapshot = df.copy()
    for fn in (normalize_unicode_and_html, strip_extra_whitespace, add_text_norm_column):
        fn(df)
    pd.testing.assert_frame_equal(df, snapshot)


def test_idempotent_and_chain_after_stage0_columns():
    df = _stage1_output()
    df.insert(0, "review_raw", df["Nội dung tự do"])
    once = strip_extra_whitespace(normalize_unicode_and_html(df))
    twice = strip_extra_whitespace(normalize_unicode_and_html(once))
    pd.testing.assert_frame_equal(once, twice)
    assert once["review_raw"].tolist() == df["review_raw"].tolist()  # review_raw nguyên văn
