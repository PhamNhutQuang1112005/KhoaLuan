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
import pytest

from core.diff_report import print_row_diff
from transforms.tang1_structural import (
    drop_empty_rows,
    fix_data_types,
    fix_field_misalignment,
    split_merged_fields,
    validate_required_columns,
)


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


def test_drops_rows_where_content_is_none():
    df = pd.DataFrame(
        {
            "Tác giả": ["a_user1", "a_user2", "a_user3"],
            "Nội dung tự do": ["Máy đẹp, dùng ổn", None, "Giao hàng nhanh"],
        }
    )

    result = validate_required_columns(df)
    print_row_diff(df, result, label="test_drops_rows_where_content_is_none")

    assert list(result.index) == [0, 2]


def test_drops_rows_where_content_is_blank_string():
    df = pd.DataFrame(
        {
            "Tác giả": ["a_user1", "a_user2"],
            "Nội dung tự do": ["Sản phẩm tốt", "   "],
        }
    )

    result = validate_required_columns(df)
    print_row_diff(df, result, label="test_drops_rows_where_content_is_blank_string")

    assert list(result.index) == [0]


def test_keeps_rows_with_content_even_if_other_columns_are_empty():
    df = pd.DataFrame(
        {
            "Tác giả": [None],
            "Tiêu chí đánh giá": [None],
            "Nội dung tự do": ["Pin trâu, sạc nhanh"],
        }
    )

    result = validate_required_columns(df)
    print_row_diff(df, result, label="test_keeps_rows_with_content_even_if_other_columns_are_empty")

    pd.testing.assert_frame_equal(result, df)


def test_validate_required_columns_does_not_mutate_input():
    df = pd.DataFrame(
        {
            "Tác giả": ["a_user1", "a_user2"],
            "Nội dung tự do": ["Đóng gói cẩn thận", None],
        }
    )
    df_copy = df.copy()

    result = validate_required_columns(df)
    print_row_diff(df_copy, result, label="test_validate_required_columns_does_not_mutate_input")

    pd.testing.assert_frame_equal(df, df_copy)


def test_validate_required_columns_missing_content_col_returns_copy_unchanged():
    df = pd.DataFrame({"Tác giả": ["abc"]})

    result = validate_required_columns(df)
    print_row_diff(df, result, label="test_validate_required_columns_missing_content_col_returns_copy_unchanged")

    pd.testing.assert_frame_equal(result, df)
    assert result is not df


def test_drop_empty_rows_removes_completely_blank_row():
    # T1.3 gộp chung T1.2: dòng #1 rỗng hoàn toàn (mọi cột đều None/khoảng
    # trắng) -> bị loại dù không có cột nào riêng lẻ bắt buộc phải kiểm tra.
    df = pd.DataFrame(
        {
            "Tác giả": ["a_user1", None],
            "Nội dung tự do": ["Sản phẩm ổn", "   "],
        }
    )

    result = drop_empty_rows(df)
    print_row_diff(df, result, label="test_drop_empty_rows_removes_completely_blank_row")

    assert list(result.index) == [0]


def test_drop_empty_rows_removes_row_missing_only_content():
    # Dòng #1 vẫn còn 'Tác giả' (không rỗng hoàn toàn) nhưng thiếu 'Nội dung
    # tự do' -> vẫn bị loại vì đây là trường bắt buộc (phần gộp từ T1.2).
    df = pd.DataFrame(
        {
            "Tác giả": ["a_user1", "a_user2"],
            "Nội dung tự do": ["Sản phẩm ổn", None],
        }
    )

    result = drop_empty_rows(df)
    print_row_diff(df, result, label="test_drop_empty_rows_removes_row_missing_only_content")

    assert list(result.index) == [0]


def test_drop_empty_rows_keeps_rows_with_content():
    df = pd.DataFrame(
        {
            "Tác giả": ["a_user1", None],
            "Tiêu chí đánh giá": [None, None],
            "Nội dung tự do": ["Giao hàng nhanh", "Đóng gói cẩn thận"],
        }
    )

    result = drop_empty_rows(df)
    print_row_diff(df, result, label="test_drop_empty_rows_keeps_rows_with_content")

    pd.testing.assert_frame_equal(result, df)


def test_drop_empty_rows_normalizes_blank_criteria_to_na():
    # T1.2: 'Tieu chi danh gia' la cot bat buoc PHAI TON TAI nhung duoc phep
    # rong -> chi chuan hoa '' / '   ' ve pd.NA nhat quan, KHONG xoa dong.
    df = pd.DataFrame(
        {
            "Tác giả": ["a_user1", "a_user2"],
            "Tiêu chí đánh giá": ["", "   "],
            "Nội dung tự do": ["Sản phẩm ổn", "Giao hàng nhanh"],
        }
    )

    result = drop_empty_rows(df)
    print_row_diff(df, result, label="test_drop_empty_rows_normalizes_blank_criteria_to_na")

    assert list(result.index) == [0, 1]
    assert pd.isna(result.loc[0, "Tiêu chí đánh giá"])
    assert pd.isna(result.loc[1, "Tiêu chí đánh giá"])


def test_drop_empty_rows_leaves_populated_criteria_untouched():
    df = pd.DataFrame(
        {
            "Tiêu chí đánh giá": ["Thiết kế: đẹp"],
            "Nội dung tự do": ["Sản phẩm ổn"],
        }
    )

    result = drop_empty_rows(df)
    print_row_diff(df, result, label="test_drop_empty_rows_leaves_populated_criteria_untouched")

    pd.testing.assert_frame_equal(result, df)


def test_drop_empty_rows_does_not_mutate_input():
    df = pd.DataFrame(
        {
            "Tác giả": ["a_user1", None],
            "Nội dung tự do": ["Sản phẩm ổn", None],
        }
    )
    df_copy = df.copy()

    result = drop_empty_rows(df)
    print_row_diff(df_copy, result, label="test_drop_empty_rows_does_not_mutate_input")

    pd.testing.assert_frame_equal(df, df_copy)


def test_fix_data_types_parses_time_col_as_naive_datetime():
    df = pd.DataFrame({"Thời gian": ["2025-12-17 01:38", "2026-01-28 15:03"]})

    result = fix_data_types(df)
    print_row_diff(df, result, label="test_fix_data_types_parses_time_col_as_naive_datetime")

    assert pd.api.types.is_datetime64_any_dtype(result["Thời gian"])
    assert result["Thời gian"].dt.tz is None
    assert result.loc[0, "Thời gian"] == pd.Timestamp("2025-12-17 01:38")


def test_fix_data_types_parses_scraped_at_col_as_utc_datetime():
    df = pd.DataFrame({"Thời điểm cào": ["2026-08-22T13:40:30.954Z", "2026-08-22T13:40:32.564Z"]})

    result = fix_data_types(df)
    print_row_diff(df, result, label="test_fix_data_types_parses_scraped_at_col_as_utc_datetime")

    assert pd.api.types.is_datetime64_any_dtype(result["Thời điểm cào"])
    assert str(result["Thời điểm cào"].dt.tz) == "UTC"
    assert result.loc[0, "Thời điểm cào"] == pd.Timestamp("2026-08-22T13:40:30.954Z")


def test_fix_data_types_handles_both_columns_together():
    df = pd.DataFrame(
        {
            "Thời gian": ["2025-12-17 01:38"],
            "Thời điểm cào": ["2026-08-22T13:40:30.954Z"],
        }
    )

    result = fix_data_types(df)
    print_row_diff(df, result, label="test_fix_data_types_handles_both_columns_together")

    assert result["Thời gian"].dt.tz is None
    assert str(result["Thời điểm cào"].dt.tz) == "UTC"


def test_fix_data_types_keeps_missing_values_as_nat():
    df = pd.DataFrame(
        {
            "Thời gian": ["2025-12-17 01:38", None],
            "Thời điểm cào": [None, "2026-08-22T13:40:30.954Z"],
        }
    )

    result = fix_data_types(df)
    print_row_diff(df, result, label="test_fix_data_types_keeps_missing_values_as_nat")

    assert pd.isna(result.loc[1, "Thời gian"])
    assert pd.isna(result.loc[0, "Thời điểm cào"])


def test_fix_data_types_raises_on_malformed_value():
    # Gia tri khong khop dinh dang khai bao (thieu gio:phut) -> phai raise
    # ngay thay vi am tham tra ve NaT, de phat hien du lieu bat thuong som.
    df = pd.DataFrame({"Thời gian": ["2025-12-17"]})

    with pytest.raises(ValueError):
        fix_data_types(df)


def test_fix_data_types_missing_columns_returns_copy_unchanged():
    df = pd.DataFrame({"Tác giả": ["abc"]})

    result = fix_data_types(df)
    print_row_diff(df, result, label="test_fix_data_types_missing_columns_returns_copy_unchanged")

    pd.testing.assert_frame_equal(result, df)
    assert result is not df


def test_fix_data_types_does_not_mutate_input():
    df = pd.DataFrame({"Thời gian": ["2025-12-17 01:38"]})
    df_copy = df.copy()

    result = fix_data_types(df)
    print_row_diff(df_copy, result, label="test_fix_data_types_does_not_mutate_input")

    pd.testing.assert_frame_equal(df, df_copy)


def test_full_chain_t11_then_t13_then_t15():
    # Test tich hop: chay noi tiep T1.1 (sua lech cot) -> T1.2+T1.3 (xoa dong
    # thieu noi dung) -> T1.5 (ep kieu ngay gio), giong dung thu tu run_t15.py.
    df = pd.DataFrame(
        {
            "Tác giả": [
                "Biết thế không xinh gái nữa, làm anh nào cũng tưởng",  # #0: lech cot (T1.1)
                "a_user2",  # #1: thieu noi dung -> bi xoa (T1.3)
                "a_user3",  # #2: dong hop le, giu nguyen
            ],
            "Nội dung tự do": [None, None, "Pin trâu, sạc nhanh"],
            "Thời gian": ["2025-12-17 01:38", "2026-01-28 15:03", "2026-06-03 10:37"],
            "Thời điểm cào": [
                "2026-08-22T13:40:30.954Z",
                "2026-08-22T13:40:32.564Z",
                "2026-08-22T13:40:34.159Z",
            ],
        }
    )

    after_t11 = fix_field_misalignment(df)
    print_row_diff(df, after_t11, label="test_full_chain][T1.1")

    after_t13 = drop_empty_rows(after_t11)
    print_row_diff(after_t11, after_t13, label="test_full_chain][T1.2+T1.3")

    after_t15 = fix_data_types(after_t13)
    print_row_diff(after_t13, after_t15, label="test_full_chain][T1.5")

    # T1.1: dong #0 duoc chuyen noi dung tu 'Tac gia' sang 'Noi dung tu do'.
    assert after_t11.loc[0, "Nội dung tự do"] == (
        "Biết thế không xinh gái nữa, làm anh nào cũng tưởng"
    )
    assert after_t11.loc[0, "Tác giả"] == "ẩn danh"

    # T1.2+T1.3: dong #1 (van thieu noi dung sau T1.1) bi xoa, chi con #0 va #2.
    assert list(after_t13.index) == [0, 2]

    # T1.5: 2 dong con lai duoc ep dung kieu datetime (tz-naive / tz-aware UTC).
    assert pd.api.types.is_datetime64_any_dtype(after_t15["Thời gian"])
    assert after_t15["Thời gian"].dt.tz is None
    assert str(after_t15["Thời điểm cào"].dt.tz) == "UTC"
    assert len(after_t15) == 2


def test_split_merged_fields_creates_one_column_per_criterion():
    df = pd.DataFrame(
        {
            "Tiêu chí đánh giá": [
                "Hiệu suất: mượt\nThiết kế: oki",
                "Thiết kế: đẹp",
            ]
        }
    )

    result = split_merged_fields(df)
    print_row_diff(df, result, label="test_split_merged_fields_creates_one_column_per_criterion")

    assert list(result["Hiệu suất"]) == ["mượt", pd.NA]
    assert list(result["Thiết kế"]) == ["oki", "đẹp"]


def test_split_merged_fields_leaves_source_column_intact():
    df = pd.DataFrame({"Tiêu chí đánh giá": ["Màu sắc: đen"]})

    result = split_merged_fields(df)

    assert "Tiêu chí đánh giá" in result.columns
    assert result.loc[0, "Tiêu chí đánh giá"] == "Màu sắc: đen"


def test_split_merged_fields_blank_for_missing_criterion_and_nan_source():
    df = pd.DataFrame(
        {
            "Tiêu chí đánh giá": [
                "Chất liệu: vải cotton\nMàu sắc: đen",
                None,  # khong co tieu chi nao -> moi cot moi deu trong
            ]
        }
    )

    result = split_merged_fields(df)
    print_row_diff(df, result, label="test_split_merged_fields_blank_for_missing_criterion_and_nan_source")

    assert result.loc[0, "Chất liệu"] == "vải cotton"
    assert pd.isna(result.loc[1, "Chất liệu"])
    assert pd.isna(result.loc[1, "Màu sắc"])


def test_split_merged_fields_splits_only_on_first_colon():
    # Gia tri co the chua ':' o sau (vd URL) -> khong duoc cat nham.
    df = pd.DataFrame({"Tiêu chí đánh giá": ["Ghi chú: xem thêm http://a.co:8080/x"]})

    result = split_merged_fields(df)

    assert result.loc[0, "Ghi chú"] == "xem thêm http://a.co:8080/x"


def test_split_merged_fields_concatenates_duplicate_key_in_same_row():
    df = pd.DataFrame({"Tiêu chí đánh giá": ["Màu sắc: đen\nMàu sắc: bóng"]})

    result = split_merged_fields(df)
    print_row_diff(df, result, label="test_split_merged_fields_concatenates_duplicate_key_in_same_row")

    assert result.loc[0, "Màu sắc"] == "đen; bóng"


def test_split_merged_fields_suffixes_column_name_on_collision():
    # 'San pham' trung ten voi 1 cot co san trong df -> phai them hau to,
    # KHONG duoc ghi de cot goc.
    df = pd.DataFrame(
        {
            "Sản phẩm": ["giá trị gốc"],
            "Tiêu chí đánh giá": ["Sản phẩm: tốt"],
        }
    )

    result = split_merged_fields(df)

    assert result.loc[0, "Sản phẩm"] == "giá trị gốc"
    assert result.loc[0, "Sản phẩm (tiêu chí)"] == "tốt"


def test_split_merged_fields_missing_source_col_returns_copy_unchanged():
    df = pd.DataFrame({"Tác giả": ["abc"]})

    result = split_merged_fields(df)
    print_row_diff(df, result, label="test_split_merged_fields_missing_source_col_returns_copy_unchanged")

    pd.testing.assert_frame_equal(result, df)
    assert result is not df


def test_split_merged_fields_does_not_mutate_input():
    df = pd.DataFrame({"Tiêu chí đánh giá": ["Màu sắc: đen"]})
    df_copy = df.copy()

    result = split_merged_fields(df)
    print_row_diff(df_copy, result, label="test_split_merged_fields_does_not_mutate_input")

    pd.testing.assert_frame_equal(df, df_copy)
