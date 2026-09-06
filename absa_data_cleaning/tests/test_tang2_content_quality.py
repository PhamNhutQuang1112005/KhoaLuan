"""
tests/test_tang2_content_quality.py
=====================================
Test cho transforms/tang2_content_quality.py (T2.9 + T2.10 gộp chung) và các
hàm phụ trợ liên quan trong transforms/utils_text.py.
"""

import pandas as pd

from core.diff_report import print_row_diff
from transforms.tang2_content_quality import drop_emoji_or_special_char_only_reviews
from transforms.utils_text import is_emoji_only, is_emoji_or_special_char_only


# --- utils_text.is_emoji_only ------------------------------------------------

def test_is_emoji_only_true_for_pure_emoji():
    assert is_emoji_only("\U0001F600\U0001F60A\U0001F44D") is True


def test_is_emoji_only_true_for_misc_symbol_emoji():
    # Nam ngoai khoi 1F3xx (emoticon pho bien) - vd ngoi sao trong khoi Misc
    # Symbols (⬀-⯿).
    assert is_emoji_only("⭐⭐") is True


def test_is_emoji_only_false_when_mixed_with_special_chars():
    assert is_emoji_only("\U0001F600!!!") is False


def test_is_emoji_only_false_for_text_with_words():
    assert is_emoji_only("Sản phẩm tốt \U0001F60A") is False


def test_is_emoji_only_false_for_blank_or_none():
    assert is_emoji_only("") is False
    assert is_emoji_only("   ") is False
    assert is_emoji_only(None) is False


# --- utils_text.is_emoji_or_special_char_only --------------------------------

def test_is_emoji_or_special_char_only_true_for_pure_emoji():
    assert is_emoji_or_special_char_only("\U0001F600\U0001F60A") is True


def test_is_emoji_or_special_char_only_true_for_pure_special_chars():
    assert is_emoji_or_special_char_only("!!!") is True
    assert is_emoji_or_special_char_only("...") is True
    assert is_emoji_or_special_char_only("-----") is True


def test_is_emoji_or_special_char_only_true_for_mixed_emoji_and_special_chars():
    assert is_emoji_or_special_char_only("!!! \U0001F600") is True


def test_is_emoji_or_special_char_only_false_when_any_letter_or_digit_present():
    assert is_emoji_or_special_char_only("ok") is False
    assert is_emoji_or_special_char_only("5") is False
    assert is_emoji_or_special_char_only("ổn \U0001F600") is False


def test_is_emoji_or_special_char_only_false_for_blank_or_none():
    assert is_emoji_or_special_char_only("") is False
    assert is_emoji_or_special_char_only("   ") is False
    assert is_emoji_or_special_char_only(None) is False


# --- drop_emoji_or_special_char_only_reviews (T2.9 + T2.10) ------------------

def test_drops_review_containing_only_emoji():
    df = pd.DataFrame({"Nội dung tự do": ["\U0001F600\U0001F60A\U0001F44D"]})

    result = drop_emoji_or_special_char_only_reviews(df)
    print_row_diff(df, result, label="test_drops_review_containing_only_emoji")

    assert result.empty


def test_drops_review_containing_only_special_chars():
    df = pd.DataFrame({"Nội dung tự do": ["!!!", "...", "-----"]})

    result = drop_emoji_or_special_char_only_reviews(df)
    print_row_diff(df, result, label="test_drops_review_containing_only_special_chars")

    assert result.empty


def test_drops_review_mixing_emoji_and_special_chars():
    df = pd.DataFrame({"Nội dung tự do": ["!!! \U0001F600 ..."]})

    result = drop_emoji_or_special_char_only_reviews(df)
    print_row_diff(df, result, label="test_drops_review_mixing_emoji_and_special_chars")

    assert result.empty


def test_keeps_review_with_real_content_even_if_it_has_emoji():
    df = pd.DataFrame(
        {
            "Nội dung tự do": [
                "Sản phẩm rất tốt \U0001F60A",
                "Giao hàng nhanh!!!",
                "\U0001F600\U0001F60A\U0001F44D",  # bi xoa
            ]
        }
    )

    result = drop_emoji_or_special_char_only_reviews(df)
    print_row_diff(df, result, label="test_keeps_review_with_real_content_even_if_it_has_emoji")

    assert list(result.index) == [0, 1]


def test_keeps_blank_or_nan_content_untouched():
    # Dong rong/NaN hoan toan KHONG thuoc pham vi T2.9/T2.10 (do la T1.3) ->
    # KHONG bi xoa o day.
    df = pd.DataFrame({"Nội dung tự do": [None, "   "]})

    result = drop_emoji_or_special_char_only_reviews(df)
    print_row_diff(df, result, label="test_keeps_blank_or_nan_content_untouched")

    pd.testing.assert_frame_equal(result, df)


def test_missing_content_col_returns_copy_unchanged():
    df = pd.DataFrame({"Tác giả": ["abc"]})

    result = drop_emoji_or_special_char_only_reviews(df)
    print_row_diff(df, result, label="test_missing_content_col_returns_copy_unchanged")

    pd.testing.assert_frame_equal(result, df)
    assert result is not df


def test_does_not_mutate_input():
    df = pd.DataFrame(
        {"Nội dung tự do": ["Sản phẩm tốt", "\U0001F600\U0001F60A"]}
    )
    df_copy = df.copy()

    result = drop_emoji_or_special_char_only_reviews(df)
    print_row_diff(df_copy, result, label="test_does_not_mutate_input")

    pd.testing.assert_frame_equal(df, df_copy)


def test_preserves_original_index_of_remaining_rows():
    df = pd.DataFrame(
        {
            "Nội dung tự do": [
                "\U0001F600\U0001F60A",  # #0: bi xoa
                "Máy đẹp, dùng ổn",  # #1: giu lai
                "!!!",  # #2: bi xoa
                "Pin trâu",  # #3: giu lai
            ]
        }
    )

    result = drop_emoji_or_special_char_only_reviews(df)
    print_row_diff(df, result, label="test_preserves_original_index_of_remaining_rows")

    assert list(result.index) == [1, 3]
