"""
tests/test_tang1_structural.py
================================
Mẫu test cho transforms/tang1_structural.py — minh hoạ cách kiểm chứng 1 hàm
thuần bằng case thật đã ghi nhận trong taxonomy (cột "Bằng chứng / Ví dụ cụ thể").

Ưu điểm của việc tách hàm thuần (FP) ở transforms/: test không cần dựng Pipeline,
Reader, Writer gì cả — chỉ cần 1 DataFrame nhỏ làm input.

Mỗi test gọi `print_row_diff` (core/diff_report.py) sau khi biến đổi để in ra
console SỐ DÒNG CỤ THỂ đã được thêm/xoá/sửa — chạy `pytest -s` để xem output này.

TODO: viết test thật sau khi implement transforms/tang1_structural.py. Dưới đây
chỉ là bộ khung minh hoạ, dùng lại đúng case đã ghi trong taxonomy
(phone_2127 #1911 — 'Tác giả' chứa nội dung review, 'Nội dung tự do' rỗng).
"""

import pandas as pd

from core.diff_report import print_row_diff
from transforms.tang1_structural import fix_field_misalignment


def test_moves_review_text_from_author_to_content_when_content_empty():
    df = pd.DataFrame(
        {
            "Tác giả": ["Biết thế không xinh gái nữa, làm anh nào cũng tưởng 😊🥸"],
            "Nội dung tự do": [None],
        }
    )

    result = fix_field_misalignment(df)
    print_row_diff(df, result, label="test_moves_review_text_from_author_to_content_when_content_empty")

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
    print_row_diff(df, result, label="test_leaves_normal_rows_untouched")

    pd.testing.assert_frame_equal(result, df)


def test_prepends_author_to_content_when_both_columns_are_misaligned():
    # Case thật: buds #766 — cả 'Tác giả' lẫn 'Nội dung tự do' đều chứa review
    # (khác dòng, cùng bị lệch) -> nối 'Tác giả' vào TRƯỚC nội dung sẵn có.
    df = pd.DataFrame(
        {
            "Tác giả": ["Tốt. Đeo dễ chịu. Chất lượng âm ở mức khá"],
            "Nội dung tự do": ["Được tặng kèm cân điện tử"],
        }
    )

    result = fix_field_misalignment(df)
    print_row_diff(df, result, label="test_prepends_author_to_content_when_both_columns_are_misaligned")

    assert result.loc[0, "Nội dung tự do"] == (
        "Tốt. Đeo dễ chịu. Chất lượng âm ở mức khá\nĐược tặng kèm cân điện tử"
    )
    assert result.loc[0, "Tác giả"] == "ẩn danh"


def test_moves_short_review_with_diacritics_when_content_empty():
    # Case thật: phone — 'Tác giả' chỉ 1 từ nhưng có dấu tiếng Việt ('đẹp'),
    # không phải username (username thật luôn thuần ASCII/số/gạch dưới).
    df = pd.DataFrame({"Tác giả": ["đẹp"], "Nội dung tự do": [None]})

    result = fix_field_misalignment(df)
    print_row_diff(df, result, label="test_moves_short_review_with_diacritics_when_content_empty")

    assert result.loc[0, "Nội dung tự do"] == "đẹp"
    assert result.loc[0, "Tác giả"] == "ẩn danh"


def test_moves_two_word_review_when_content_empty():
    # Case thật: phone — 'Tác giả' = 'Tạm ổn' (2 từ), dưới ngưỡng cũ (3 từ)
    # nên trước đây bị bỏ sót.
    df = pd.DataFrame({"Tác giả": ["Tạm ổn"], "Nội dung tự do": [None]})

    result = fix_field_misalignment(df)
    print_row_diff(df, result, label="test_moves_two_word_review_when_content_empty")

    assert result.loc[0, "Nội dung tự do"] == "Tạm ổn"
    assert result.loc[0, "Tác giả"] == "ẩn danh"


def test_leaves_ambiguous_single_word_without_diacritics_untouched():
    # Case thật: pin — 'Tác giả' = 'ok', 1 từ, không dấu: mơ hồ (có thể là
    # username thật) -> cố tình KHÔNG sửa.
    df = pd.DataFrame({"Tác giả": ["ok"], "Nội dung tự do": [None]})

    result = fix_field_misalignment(df)
    print_row_diff(df, result, label="test_leaves_ambiguous_single_word_without_diacritics_untouched")

    pd.testing.assert_frame_equal(result, df)


def test_does_not_mutate_input():
    df = pd.DataFrame(
        {
            "Tác giả": ["Sản phẩm được đóng gói rất cẩn thận, shipper giao nhanh"],
            "Nội dung tự do": [None],
        }
    )
    df_copy = df.copy()

    result = fix_field_misalignment(df)
    print_row_diff(df_copy, result, label="test_does_not_mutate_input")

    pd.testing.assert_frame_equal(df, df_copy)


def test_missing_columns_returns_copy_unchanged():
    df = pd.DataFrame({"Tác giả": ["abc"]})

    result = fix_field_misalignment(df)
    print_row_diff(df, result, label="test_missing_columns_returns_copy_unchanged")

    pd.testing.assert_frame_equal(result, df)
    assert result is not df
