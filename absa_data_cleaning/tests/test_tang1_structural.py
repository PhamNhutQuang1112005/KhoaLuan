"""
tests/test_tang1_structural.py
================================
Mẫu test cho transforms/tang1_structural.py — minh hoạ cách kiểm chứng 1 hàm
thuần bằng case thật đã ghi nhận trong taxonomy (cột "Bằng chứng / Ví dụ cụ thể").

Ưu điểm của việc tách hàm thuần (FP) ở transforms/: test không cần dựng Pipeline,
Reader, Writer gì cả — chỉ cần 1 DataFrame nhỏ làm input.

TODO: viết test thật sau khi implement transforms/tang1_structural.py. Dưới đây
chỉ là bộ khung minh hoạ, dùng lại đúng case đã ghi trong taxonomy
(phone_2127 #1911 — 'Tác giả' chứa nội dung review, 'Nội dung tự do' rỗng).
"""

import pandas as pd

from transforms.tang1_structural import fix_field_misalignment


def test_moves_review_text_from_author_to_content_when_content_empty():
    df = pd.DataFrame(
        {
            "Tác giả": ["Biết thế không xinh gái nữa, làm anh nào cũng tưởng 😊🥸"],
            "Nội dung tự do": [None],
        }
    )

    result = fix_field_misalignment(df)

    assert result.loc[0, "Nội dung tự do"] == "Biết thế không xinh gái nữa, làm anh nào cũng tưởng 😊🥸"
    assert result.loc[0, "Tác giả"] == "ẩn danh"


def test_leaves_normal_rows_untouched():
    df = pd.DataFrame(
        {
            "Tác giả": ["nganmom_13", "2b_kidstore"],
            "Nội dung tự do": ["Máy đẹp nguyên kiện, 10 điểm uy tín", None],
        }
    )

    result = fix_field_misalignment(df)

    pd.testing.assert_frame_equal(result, df)


def test_does_not_touch_multiword_author_when_content_present():
    # Tên hiển thị nhiều từ nhưng nội dung vẫn có -> không phải lệch cột T1.1.
    df = pd.DataFrame(
        {
            "Tác giả": ["Tốt. Đeo dễ chịu. Chất lượng âm ở mức khá"],
            "Nội dung tự do": ["Được tặng kèm cân điện tử"],
        }
    )

    result = fix_field_misalignment(df)

    pd.testing.assert_frame_equal(result, df)


def test_does_not_mutate_input():
    df = pd.DataFrame(
        {
            "Tác giả": ["Sản phẩm được đóng gói rất cẩn thận, shipper giao nhanh"],
            "Nội dung tự do": [None],
        }
    )
    df_copy = df.copy()

    fix_field_misalignment(df)

    pd.testing.assert_frame_equal(df, df_copy)


def test_missing_columns_returns_copy_unchanged():
    df = pd.DataFrame({"Tác giả": ["abc"]})

    result = fix_field_misalignment(df)

    pd.testing.assert_frame_equal(result, df)
    assert result is not df
