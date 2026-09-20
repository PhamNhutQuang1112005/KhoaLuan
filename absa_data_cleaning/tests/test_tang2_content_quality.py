"""
tests/test_tang2_content_quality.py
=====================================
Test cho transforms/tang2_content_quality.py (T2.9 + T2.10 gộp chung) và các
hàm phụ trợ liên quan trong transforms/utils_text.py.
"""

import pandas as pd

from core.diff_report import print_row_diff
from transforms.tang2_content_quality import (
    drop_emoji_or_special_char_only_reviews,
    drop_exact_duplicates,
    fix_spelling_errors,
    is_short_review,
    normalize_teencode_and_abbreviations,
    split_near_duplicate_reviews,
    split_short_reviews,
    split_spelling_error_reviews,
    split_suspect_teencode_reviews,
    split_url_hotline_or_spam_reviews,
)
from transforms.utils_text import (
    contains_any_term,
    contains_phone_number,
    contains_url,
    correct_spelling_text,
    has_vowel,
    is_emoji_only,
    is_emoji_or_special_char_only,
    is_vietnamese_syllable,
    normalize_teencode_text,
    text_similarity,
)


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


def test_keeps_emoji_only_content_when_criteria_has_value():
    # Dong bo nguyen tac T1.2+T1.3: 'Tieu chi danh gia' co gia tri -> GIU LAI
    # du 'Noi dung tu do' chi la emoji/ky tu dac biet.
    df = pd.DataFrame(
        {
            "Tiêu chí đánh giá": ["Pin: tốt"],
            "Nội dung tự do": ["!!! \U0001F60A"],
        }
    )

    result = drop_emoji_or_special_char_only_reviews(df)
    print_row_diff(df, result, label="test_keeps_emoji_only_content_when_criteria_has_value")

    pd.testing.assert_frame_equal(result, df)


def test_drops_emoji_only_content_when_criteria_is_also_blank():
    df = pd.DataFrame(
        {
            "Tiêu chí đánh giá": [None, "   "],
            "Nội dung tự do": ["!!! \U0001F60A", "\U0001F600\U0001F600"],
        }
    )

    result = drop_emoji_or_special_char_only_reviews(df)
    print_row_diff(df, result, label="test_drops_emoji_only_content_when_criteria_is_also_blank")

    assert result.empty


# --- utils_text.has_vowel -----------------------------------------------------

def test_has_vowel_true_for_plain_and_diacritic_vowels():
    assert has_vowel("ok") is True
    assert has_vowel("tốt") is True  # 'ố' -> NFD tach thanh 'o' + dau


def test_has_vowel_false_for_consonants_only():
    assert has_vowel("kkkk") is False
    assert has_vowel("vs") is False


# --- is_short_review (T2.11 + T2.12) ------------------------------------------

def test_is_short_review_true_at_or_under_default_threshold():
    assert is_short_review("ok") is True
    assert is_short_review("Sản phẩm tốt") is True  # 2 tu
    assert is_short_review("Pin khỏe dùng ổn") is True  # dung 4 tu


def test_is_short_review_false_above_default_threshold():
    assert is_short_review("Pin khỏe dùng rất ổn") is False  # 5 tu


def test_is_short_review_respects_custom_max_words():
    assert is_short_review("Pin khỏe dùng ổn", max_words=3) is False  # 4 tu
    assert is_short_review("Pin khỏe dùng", max_words=3) is True  # 3 tu


def test_is_short_review_false_for_blank_or_none():
    assert is_short_review("") is False
    assert is_short_review("   ") is False
    assert is_short_review(None) is False


# --- split_short_reviews (T2.11 + T2.12) --------------------------------------

def test_splits_short_reviews_out_when_criteria_is_blank():
    df = pd.DataFrame(
        {
            "Nội dung tự do": [
                "ok",  # #0: ngan -> tach
                "Máy đẹp, dùng rất ổn, pin trâu",  # #1: dai -> giu
                "Pin khỏe",  # #2: ngan -> tach (van huu ich nhung van la review ngan)
            ]
        }
    )

    kept, short = split_short_reviews(df)
    print_row_diff(df, kept, label="test_splits_short_reviews_out_when_criteria_is_blank")

    assert list(kept.index) == [1]
    assert list(short.index) == [0, 2]


def test_keeps_short_review_in_kept_df_when_criteria_has_value():
    # Dong bo nguyen tac T1.2+T1.3: 'Tieu chi danh gia' co gia tri -> KHONG
    # tach du 'Noi dung tu do' ngan.
    df = pd.DataFrame(
        {
            "Tiêu chí đánh giá": ["Pin: tốt", "Thiết kế: đẹp"],
            "Nội dung tự do": ["ok", "sdfg"],
        }
    )

    kept, short = split_short_reviews(df)
    print_row_diff(df, kept, label="test_keeps_short_review_in_kept_df_when_criteria_has_value")

    pd.testing.assert_frame_equal(kept, df)
    assert short.empty


def test_splits_short_review_out_when_criteria_is_also_blank():
    df = pd.DataFrame(
        {
            "Tiêu chí đánh giá": [None, "   "],
            "Nội dung tự do": ["ok", "sdfg"],
        }
    )

    kept, short = split_short_reviews(df)
    print_row_diff(df, kept, label="test_splits_short_review_out_when_criteria_is_also_blank")

    assert kept.empty
    pd.testing.assert_frame_equal(short, df)


def test_keeps_long_review_untouched_even_without_criteria():
    df = pd.DataFrame(
        {"Nội dung tự do": ["Sản phẩm này thực sự rất tốt và đáng đồng tiền bát gạo"]}
    )

    kept, short = split_short_reviews(df)
    print_row_diff(df, kept, label="test_keeps_long_review_untouched_even_without_criteria")

    pd.testing.assert_frame_equal(kept, df)
    assert short.empty


def test_does_not_split_blank_or_nan_content():
    df = pd.DataFrame({"Nội dung tự do": [None, "   "]})

    kept, short = split_short_reviews(df)
    print_row_diff(df, kept, label="test_does_not_split_blank_or_nan_content")

    pd.testing.assert_frame_equal(kept, df)
    assert short.empty


def test_missing_content_col_returns_kept_copy_and_empty_short():
    df = pd.DataFrame({"Tác giả": ["abc"]})

    kept, short = split_short_reviews(df)
    print_row_diff(df, kept, label="test_missing_content_col_returns_kept_copy_and_empty_short")

    pd.testing.assert_frame_equal(kept, df)
    assert kept is not df
    assert short.empty


def test_does_not_mutate_input_when_splitting():
    df = pd.DataFrame({"Nội dung tự do": ["ok", "Pin khỏe dùng ổn nhưng loa hơi bé"]})
    df_copy = df.copy()

    kept, short = split_short_reviews(df)
    print_row_diff(df_copy, kept, label="test_does_not_mutate_input_when_splitting")

    pd.testing.assert_frame_equal(df, df_copy)


def test_preserves_original_index_across_both_splits():
    df = pd.DataFrame(
        {
            "Nội dung tự do": [
                "ok",  # #0: ngan -> tach
                "Pin khỏe dùng ổn nhưng loa hơi bé",  # #1: dai -> giu
                "sdfg",  # #2: ngan -> tach
                "Máy đẹp, dùng ổn, pin trâu, camera nét",  # #3: dai -> giu
            ]
        }
    )

    kept, short = split_short_reviews(df)
    print_row_diff(df, kept, label="test_preserves_original_index_across_both_splits")

    assert list(kept.index) == [1, 3]
    assert list(short.index) == [0, 2]


# --- utils_text.contains_url ---------------------------------------------------

def test_contains_url_true_for_http_and_www():
    assert contains_url("Xem thêm tại https://shop.vn/abc") is True
    assert contains_url("www.example.vn/sanpham") is True


def test_contains_url_true_for_bare_domain():
    assert contains_url("Ghé shop.com nhé") is True


def test_contains_url_false_for_plain_sentence():
    assert contains_url("Sản phẩm này thực sự rất tốt.") is False
    assert contains_url("Giá 500.000đ rẻ quá") is False


def test_contains_url_false_for_blank_or_none():
    assert contains_url("") is False
    assert contains_url("   ") is False
    assert contains_url(None) is False


def test_contains_url_false_for_missing_space_after_period_with_shop_word():
    # Regression: TLD 'shop' TUNG bi go bo khoi danh sach domain tran vi
    # review tieng Viet hay thieu khoang trang sau dau cham cuoi cau (vd 'lui
    # 1 size.Shop dong goi...' -> y la 2 cau rieng 'lui 1 size.' + 'Shop dong
    # goi...') khien 'size.Shop' bi doc nham thanh domain -> xoa nham review
    # that. Xem transforms/utils_text.py._URL_RE.
    assert contains_url("bạn nào thích mặc vừa người nên lùi 1 size.Shop đóng gói hàng cẩn thận") is False
    assert contains_url("Nón đẹp, đúng from.Shop vui vẻ nhiệt tình giao hàng nhanh") is False


# --- utils_text.contains_phone_number -------------------------------------------

def test_contains_phone_number_true_for_real_phone_number():
    assert contains_phone_number("Gọi hotline 0987654321 để đặt hàng") is True
    assert contains_phone_number("SĐT: 090.123.4567") is True


def test_contains_phone_number_false_for_ad_related_keyword_without_digits():
    # Regression: KHONG con bat theo tu khoa 'zalo'/'ib'/'inbox'/'hotline'
    # dung rieng (khong kem so cu the) — rat nhieu review THAT nhac cac tu
    # nay ma khong phai quang cao (vd che tinh nang khong cai duoc zalo, khen
    # shop rep ib nhanh). Xem transforms/utils_text.py.contains_phone_number.
    assert contains_phone_number("Liên hệ zalo shop nhé") is False
    assert contains_phone_number("Inbox shop để được tư vấn") is False
    assert contains_phone_number("Ko cài đc zalo, zoom.... tiền nào của ấy ko nên mua nhé") is False
    assert contains_phone_number("Sản phẩm tốt, shop rep ib nhanh") is False
    assert contains_phone_number("Gọi lên hotline hỏi thì nói có xuất hoá đơn") is False


def test_contains_phone_number_false_for_8_digit_date():
    # Regression: nguong toi thieu da tang tu 7 len 8 chu so con lai (tong
    # 9-11 chu so, dung do dai SDT VN that) de tranh bat nham ngay thang dang
    # 'DD.MM.YYYY' (vd '01.02.2023' chi co 8 chu so).
    assert contains_phone_number("Mình mua ngày 01.02.2023 dùng đến giờ vẫn ổn") is False


def test_contains_phone_number_false_for_plain_sentence():
    assert contains_phone_number("Máy đẹp, dùng ổn, pin trâu") is False
    assert contains_phone_number("Mua với giá 990000 đồng") is False
    assert contains_phone_number("Đánh giá 5 sao cho sản phẩm") is False


def test_contains_phone_number_false_for_blank_or_none():
    assert contains_phone_number("") is False
    assert contains_phone_number("   ") is False
    assert contains_phone_number(None) is False


# --- split_url_hotline_or_spam_reviews (T2.13 + T2.14) ---------------------------

def test_splits_out_review_containing_only_url():
    df = pd.DataFrame({"Nội dung tự do": ["https://shop.vn/khuyenmai"]})

    kept, suspect = split_url_hotline_or_spam_reviews(df)
    print_row_diff(df, kept, label="test_splits_out_review_containing_only_url")

    assert kept.empty
    pd.testing.assert_frame_equal(suspect, df)


def test_splits_out_review_with_hotline_ad_inserted_into_real_text():
    # T2.14: quang cao/hotline chen lan vao review that -> van tach vi dung
    # CHUNG 1 bo loc regex voi T2.13 (khac T2.13 o cho khong phai TOAN BO
    # noi dung la URL/hotline, ma bi CHEN LAN vao).
    df = pd.DataFrame(
        {
            "Nội dung tự do": [
                "Sản phẩm dùng tạm ổn, liên hệ hotline 0987654321 để mua giá tốt"
            ]
        }
    )

    kept, suspect = split_url_hotline_or_spam_reviews(df)
    print_row_diff(df, kept, label="test_splits_out_review_with_hotline_ad_inserted_into_real_text")

    assert kept.empty
    pd.testing.assert_frame_equal(suspect, df)


def test_keeps_review_without_any_url_or_hotline():
    df = pd.DataFrame(
        {
            "Nội dung tự do": [
                "Sản phẩm rất tốt, đóng gói cẩn thận",
                "Giao hàng nhanh, pin trâu",
            ]
        }
    )

    kept, suspect = split_url_hotline_or_spam_reviews(df)
    print_row_diff(df, kept, label="test_keeps_review_without_any_url_or_hotline")

    pd.testing.assert_frame_equal(kept, df)
    assert suspect.empty


def test_does_not_split_blank_or_nan_content_for_url_or_spam():
    df = pd.DataFrame({"Nội dung tự do": [None, "   "]})

    kept, suspect = split_url_hotline_or_spam_reviews(df)
    print_row_diff(df, kept, label="test_does_not_split_blank_or_nan_content_for_url_or_spam")

    pd.testing.assert_frame_equal(kept, df)
    assert suspect.empty


def test_missing_both_cols_returns_kept_copy_and_empty_suspect():
    df = pd.DataFrame({"Tác giả": ["abc"]})

    kept, suspect = split_url_hotline_or_spam_reviews(df)
    print_row_diff(df, kept, label="test_missing_both_cols_returns_kept_copy_and_empty_suspect")

    pd.testing.assert_frame_equal(kept, df)
    assert kept is not df
    assert suspect.empty


def test_splits_out_url_content_even_when_criteria_has_real_value():
    # KHAC voi T2.9+T2.10/T2.11+T2.12: 'Tieu chi danh gia' co gia tri that
    # KHONG "cuu" duoc dong neu 'Noi dung tu do' la URL/hotline quang cao —
    # ban than cot chua quang cao da la dau hieu nhieu, phai tach du cot kia
    # co gia tri that.
    df = pd.DataFrame(
        {
            "Tiêu chí đánh giá": ["Pin: tốt"],
            "Nội dung tự do": ["https://shop.vn/khuyenmai"],
        }
    )

    kept, suspect = split_url_hotline_or_spam_reviews(df)
    print_row_diff(df, kept, label="test_splits_out_url_content_even_when_criteria_has_real_value")

    assert kept.empty
    pd.testing.assert_frame_equal(suspect, df)


def test_splits_out_when_criteria_col_itself_contains_url_or_hotline():
    # Kiem tra CA 2 cot: quang cao/hotline bi chen vao 'Tieu chi danh gia'
    # (khong phai 'Noi dung tu do') van phai bi tach.
    df = pd.DataFrame(
        {
            "Tiêu chí đánh giá": ["Lh zalo 0987654321 shop ạ"],
            "Nội dung tự do": ["Sản phẩm dùng tốt, đóng gói cẩn thận"],
        }
    )

    kept, suspect = split_url_hotline_or_spam_reviews(df)
    print_row_diff(df, kept, label="test_splits_out_when_criteria_col_itself_contains_url_or_hotline")

    assert kept.empty
    pd.testing.assert_frame_equal(suspect, df)


def test_keeps_genuine_reviews_mentioning_zalo_ib_hotline_without_ad_content():
    # Regression: cac cau nay TUNG bi xoa nham vi khop tu khoa 'zalo'/'ib'/
    # 'hotline' dung rieng, du la review THAT khong phai quang cao (phat
    # hien khi ra soat data/interim thuc te — xem docstring
    # split_url_hotline_or_spam_reviews).
    df = pd.DataFrame(
        {
            "Nội dung tự do": [
                "Không có khe cắm sim để nghe gọi. Ko cài đc zalo, zoom.... tiền nào của ấy ko nên mua nhé",
                "Sản phẩm tốt chưa thấy bị lỗi, ib shop trả lời lâu và chưa hỗ trợ nhiệt tình",
                "Gọi lên hotline hỏi thì nói có xuất hoá đơn nên mình mới đặt mua vì mua cho cty",
            ]
        }
    )

    kept, suspect = split_url_hotline_or_spam_reviews(df)
    print_row_diff(df, kept, label="test_keeps_genuine_reviews_mentioning_zalo_ib_hotline_without_ad_content")

    pd.testing.assert_frame_equal(kept, df)
    assert suspect.empty


def test_keeps_row_when_neither_column_contains_url_or_hotline():
    df = pd.DataFrame(
        {
            "Tiêu chí đánh giá": ["Pin: tốt", None],
            "Nội dung tự do": ["Dùng ổn, pin trâu", "Giao hàng nhanh"],
        }
    )

    kept, suspect = split_url_hotline_or_spam_reviews(df)
    print_row_diff(df, kept, label="test_keeps_row_when_neither_column_contains_url_or_hotline")

    pd.testing.assert_frame_equal(kept, df)
    assert suspect.empty


def test_missing_criteria_col_only_checks_content_col():
    df = pd.DataFrame({"Nội dung tự do": ["https://shop.vn/khuyenmai", "Máy đẹp"]})

    kept, suspect = split_url_hotline_or_spam_reviews(df)
    print_row_diff(df, kept, label="test_missing_criteria_col_only_checks_content_col")

    assert list(kept.index) == [1]
    assert list(suspect.index) == [0]


def test_preserves_original_index_across_both_splits_for_url_or_spam():
    df = pd.DataFrame(
        {
            "Nội dung tự do": [
                "https://shop.vn/khuyenmai",  # #0: nghi van -> tach
                "Máy đẹp, dùng ổn",  # #1: giu lai
                "hotline 0987654321",  # #2: nghi van -> tach
                "Pin trâu",  # #3: giu lai
            ]
        }
    )

    kept, suspect = split_url_hotline_or_spam_reviews(df)
    print_row_diff(df, kept, label="test_preserves_original_index_across_both_splits_for_url_or_spam")

    assert list(kept.index) == [1, 3]
    assert list(suspect.index) == [0, 2]


def test_does_not_mutate_input_for_url_or_spam():
    df = pd.DataFrame(
        {"Nội dung tự do": ["Sản phẩm tốt", "https://shop.vn/khuyenmai"]}
    )
    df_copy = df.copy()

    kept, suspect = split_url_hotline_or_spam_reviews(df)
    print_row_diff(df_copy, kept, label="test_does_not_mutate_input_for_url_or_spam")

    pd.testing.assert_frame_equal(df, df_copy)


# --- utils_text.text_similarity ------------------------------------------------

def test_text_similarity_returns_1_for_identical_strings():
    assert text_similarity("Sản phẩm tốt", "Sản phẩm tốt") == 1.0


def test_text_similarity_ignores_case_and_surrounding_whitespace():
    assert text_similarity("  Sản phẩm tốt  ", "sản phẩm tốt") == 1.0


def test_text_similarity_low_for_unrelated_strings():
    assert text_similarity("Sản phẩm tốt, đóng gói cẩn thận", "Pin nhanh hết") < 0.5


def test_text_similarity_zero_for_blank_or_none():
    assert text_similarity("", "abc") == 0.0
    assert text_similarity("abc", "   ") == 0.0
    assert text_similarity(None, "abc") == 0.0
    assert text_similarity("abc", None) == 0.0


# --- drop_exact_duplicates (T2.15) ---------------------------------------------

def test_drops_exact_duplicate_content_and_author_keeping_first():
    df = pd.DataFrame(
        {
            "Tác giả": ["An", "An", "Bình"],
            "Nội dung tự do": ["Sản phẩm rất tốt", "Sản phẩm rất tốt", "Dùng ổn"],
        }
    )

    result = drop_exact_duplicates(df)
    print_row_diff(df, result, label="test_drops_exact_duplicate_content_and_author_keeping_first")

    assert list(result.index) == [0, 2]


def test_keeps_same_content_from_different_authors():
    # Chi trung 'Noi dung tu do', KHAC 'Tac gia' -> KHONG du chac chan la loi
    # crawl trung, phai GIU LAI ca 2 (khac voi split_near_duplicate_reviews
    # T2.16 se dua cap nay vao dien nghi van neu du similarity).
    df = pd.DataFrame(
        {
            "Tác giả": ["An", "Bình"],
            "Nội dung tự do": ["Sản phẩm rất tốt", "Sản phẩm rất tốt"],
        }
    )

    result = drop_exact_duplicates(df)
    print_row_diff(df, result, label="test_keeps_same_content_from_different_authors")

    pd.testing.assert_frame_equal(result, df)


def test_dedup_by_content_only_when_author_col_missing():
    df = pd.DataFrame({"Nội dung tự do": ["Sản phẩm rất tốt", "Sản phẩm rất tốt"]})

    result = drop_exact_duplicates(df)
    print_row_diff(df, result, label="test_dedup_by_content_only_when_author_col_missing")

    assert list(result.index) == [0]


def test_does_not_drop_blank_or_nan_content_as_duplicate():
    df = pd.DataFrame(
        {
            "Tác giả": ["An", "Bình"],
            "Nội dung tự do": [None, "   "],
        }
    )

    result = drop_exact_duplicates(df)
    print_row_diff(df, result, label="test_does_not_drop_blank_or_nan_content_as_duplicate")

    pd.testing.assert_frame_equal(result, df)


def test_does_not_drop_when_author_is_blank_even_if_content_matches():
    df = pd.DataFrame(
        {
            "Tác giả": [None, "   "],
            "Nội dung tự do": ["Sản phẩm rất tốt", "Sản phẩm rất tốt"],
        }
    )

    result = drop_exact_duplicates(df)
    print_row_diff(df, result, label="test_does_not_drop_when_author_is_blank_even_if_content_matches")

    pd.testing.assert_frame_equal(result, df)


def test_does_not_drop_two_different_anonymous_authors_with_matching_content():
    # Regression: 'an danh' la nhan CHUNG cho MOI khach an danh tren nhieu san
    # TMDT (khong phai 1 dinh danh duy nhat) - phat hien khi ra soat thuc te
    # data/interim (xem docstring drop_exact_duplicates / _ANONYMOUS_AUTHOR_LABELS).
    # Neu coi day la 1 "tac gia" hop le thi 2 khach an danh KHAC NHAU cung
    # viet 1 cau ngan pho bien se bi hieu nham la trung lap va xoa nham.
    df = pd.DataFrame(
        {
            "Tác giả": ["ẩn danh", "ẩn danh"],
            "Nội dung tự do": ["Tốt", "Tốt"],
        }
    )

    result = drop_exact_duplicates(df)
    print_row_diff(df, result, label="test_does_not_drop_two_different_anonymous_authors_with_matching_content")

    pd.testing.assert_frame_equal(result, df)


def test_anonymous_author_label_check_is_case_insensitive():
    df = pd.DataFrame(
        {
            "Tác giả": ["Ẩn Danh", "ẨN DANH"],
            "Nội dung tự do": ["Tốt", "Tốt"],
        }
    )

    result = drop_exact_duplicates(df)
    print_row_diff(df, result, label="test_anonymous_author_label_check_is_case_insensitive")

    pd.testing.assert_frame_equal(result, df)


def test_still_drops_duplicate_from_real_non_anonymous_author():
    # Doi chung voi test tren: username THAT (khong phai nhan an danh dung
    # chung) van duoc coi la dinh danh hop le de phat hien trung lap.
    df = pd.DataFrame(
        {
            "Tác giả": ["nguyenvana123", "nguyenvana123"],
            "Nội dung tự do": ["Tốt", "Tốt"],
        }
    )

    result = drop_exact_duplicates(df)
    print_row_diff(df, result, label="test_still_drops_duplicate_from_real_non_anonymous_author")

    assert list(result.index) == [0]


def test_missing_content_col_returns_copy_unchanged_for_exact_duplicates():
    df = pd.DataFrame({"Tác giả": ["An"]})

    result = drop_exact_duplicates(df)
    print_row_diff(df, result, label="test_missing_content_col_returns_copy_unchanged_for_exact_duplicates")

    pd.testing.assert_frame_equal(result, df)
    assert result is not df


def test_preserves_original_index_of_remaining_rows_for_exact_duplicates():
    df = pd.DataFrame(
        {
            "Tác giả": ["An", "An", "Bình", "An"],
            "Nội dung tự do": [
                "Sản phẩm rất tốt",  # #0: giu (lan dau)
                "Máy đẹp, dùng ổn",  # #1: giu (khac noi dung)
                "Sản phẩm rất tốt",  # #2: giu (khac tac gia)
                "Sản phẩm rất tốt",  # #3: xoa (trung #0)
            ]
        }
    )

    result = drop_exact_duplicates(df)
    print_row_diff(df, result, label="test_preserves_original_index_of_remaining_rows_for_exact_duplicates")

    assert list(result.index) == [0, 1, 2]


def test_does_not_mutate_input_for_exact_duplicates():
    df = pd.DataFrame(
        {
            "Tác giả": ["An", "An"],
            "Nội dung tự do": ["Sản phẩm rất tốt", "Sản phẩm rất tốt"],
        }
    )
    df_copy = df.copy()

    result = drop_exact_duplicates(df)
    print_row_diff(df_copy, result, label="test_does_not_mutate_input_for_exact_duplicates")

    pd.testing.assert_frame_equal(df, df_copy)


# --- split_near_duplicate_reviews (T2.16) ---------------------------------------

def test_splits_near_duplicate_content_between_different_authors():
    df = pd.DataFrame(
        {
            "Tác giả": ["An", "Bình", "Chi"],
            "Nội dung tự do": [
                "Sản phẩm này thực sự rất tốt, đóng gói cẩn thận",
                "Sản phẩm này thực sự rất tốt, đóng gói cẩn thận!",  # gan trung #0, khac tac gia
                "Pin dùng nhanh hết, hơi thất vọng",
            ],
        }
    )

    kept, suspect = split_near_duplicate_reviews(df)
    print_row_diff(df, kept, label="test_splits_near_duplicate_content_between_different_authors")

    assert list(kept.index) == [2]
    assert list(suspect.index) == [0, 1]


def test_keeps_similar_content_from_same_author():
    # Cung 1 tac gia -> KHONG tinh la nghi van (da xu ly dut diem o T2.15 neu
    # trung tuyet doi; gan giong nhau cung tac gia khong phai dau hieu dang
    # ngo). Xem docstring split_near_duplicate_reviews.
    df = pd.DataFrame(
        {
            "Tác giả": ["An", "An"],
            "Nội dung tự do": [
                "Sản phẩm này thực sự rất tốt, đóng gói cẩn thận",
                "Sản phẩm này thực sự rất tốt, đóng gói cẩn thận!",
            ],
        }
    )

    kept, suspect = split_near_duplicate_reviews(df)
    print_row_diff(df, kept, label="test_keeps_similar_content_from_same_author")

    pd.testing.assert_frame_equal(kept, df)
    assert suspect.empty


def test_keeps_unrelated_content_from_different_authors():
    df = pd.DataFrame(
        {
            "Tác giả": ["An", "Bình"],
            "Nội dung tự do": ["Sản phẩm rất tốt", "Pin dùng nhanh hết"],
        }
    )

    kept, suspect = split_near_duplicate_reviews(df)
    print_row_diff(df, kept, label="test_keeps_unrelated_content_from_different_authors")

    pd.testing.assert_frame_equal(kept, df)
    assert suspect.empty


def test_near_duplicate_respects_custom_similarity_threshold():
    df = pd.DataFrame(
        {
            "Tác giả": ["An", "Bình"],
            "Nội dung tự do": ["Sản phẩm rất tốt", "Sản phẩm khá tốt"],
        }
    )

    kept_default, suspect_default = split_near_duplicate_reviews(df)
    kept_loose, suspect_loose = split_near_duplicate_reviews(df, similarity_threshold=0.5)

    print_row_diff(df, kept_default, label="test_near_duplicate_respects_custom_similarity_threshold][default")
    print_row_diff(df, kept_loose, label="test_near_duplicate_respects_custom_similarity_threshold][loose")

    assert suspect_default.empty
    assert list(suspect_loose.index) == [0, 1]


def test_does_not_compare_blank_or_nan_content_for_near_duplicates():
    df = pd.DataFrame(
        {
            "Tác giả": ["An", "Bình"],
            "Nội dung tự do": [None, "   "],
        }
    )

    kept, suspect = split_near_duplicate_reviews(df)
    print_row_diff(df, kept, label="test_does_not_compare_blank_or_nan_content_for_near_duplicates")

    pd.testing.assert_frame_equal(kept, df)
    assert suspect.empty


def test_does_not_compare_rows_with_blank_author_for_near_duplicates():
    df = pd.DataFrame(
        {
            "Tác giả": [None, "   "],
            "Nội dung tự do": [
                "Sản phẩm này thực sự rất tốt, đóng gói cẩn thận",
                "Sản phẩm này thực sự rất tốt, đóng gói cẩn thận!",
            ],
        }
    )

    kept, suspect = split_near_duplicate_reviews(df)
    print_row_diff(df, kept, label="test_does_not_compare_rows_with_blank_author_for_near_duplicates")

    pd.testing.assert_frame_equal(kept, df)
    assert suspect.empty


def test_missing_author_col_returns_kept_copy_and_empty_suspect():
    df = pd.DataFrame({"Nội dung tự do": ["Sản phẩm rất tốt", "Sản phẩm rất tốt"]})

    kept, suspect = split_near_duplicate_reviews(df)
    print_row_diff(df, kept, label="test_missing_author_col_returns_kept_copy_and_empty_suspect")

    pd.testing.assert_frame_equal(kept, df)
    assert kept is not df
    assert suspect.empty


def test_preserves_original_index_across_both_splits_for_near_duplicates():
    df = pd.DataFrame(
        {
            "Tác giả": ["An", "Bình", "Chi", "Dung"],
            "Nội dung tự do": [
                "Sản phẩm này thực sự rất tốt, đóng gói cẩn thận",  # #0: nghi van
                "Máy đẹp, dùng ổn, pin trâu",  # #1: giu
                "Sản phẩm này thực sự rất tốt, đóng gói cẩn thận!",  # #2: nghi van (trung #0)
                "Giao hàng nhanh, đóng gói kỹ",  # #3: giu
            ],
        }
    )

    kept, suspect = split_near_duplicate_reviews(df)
    print_row_diff(df, kept, label="test_preserves_original_index_across_both_splits_for_near_duplicates")

    assert list(kept.index) == [1, 3]
    assert list(suspect.index) == [0, 2]


def test_does_not_mutate_input_for_near_duplicates():
    df = pd.DataFrame(
        {
            "Tác giả": ["An", "Bình"],
            "Nội dung tự do": [
                "Sản phẩm này thực sự rất tốt, đóng gói cẩn thận",
                "Sản phẩm này thực sự rất tốt, đóng gói cẩn thận!",
            ],
        }
    )
    df_copy = df.copy()

    kept, suspect = split_near_duplicate_reviews(df)
    print_row_diff(df_copy, kept, label="test_does_not_mutate_input_for_near_duplicates")

    pd.testing.assert_frame_equal(df, df_copy)


# --- utils_text.normalize_teencode_text / contains_any_term (T2.17 + T2.18) ----

def _safe(value: str) -> list:
    """Dict {key: [ung_vien]} voi 1 ung vien duy nhat (khong da nghia) -
    dung de dung ngan gon trong test, khop dung shape ma
    dataio.dictionary_loader.load_teencode_dict tra ve."""
    return [{"value": value, "context_keywords": None, "flag": "safe"}]


def _ambiguous(*value_keywords: tuple) -> list:
    """Dict {key: [ung_vien, ...]} nhieu ung vien (da nghia), moi phan tu la
    (value, [context_keywords])."""
    return [{"value": v, "context_keywords": kws, "flag": "ambiguous"} for v, kws in value_keywords]


def test_normalize_teencode_text_replaces_single_word_key():
    d = {"ko": _safe("không"), "sp": _safe("sản phẩm")}
    assert normalize_teencode_text("Ko thích sp này", d) == "không thích sản phẩm này"


def test_normalize_teencode_text_prefers_multi_word_key_over_single_word():
    d = {"san": _safe("XXX"), "san pham": _safe("sản phẩm")}
    assert normalize_teencode_text("mua san pham", d) == "mua sản phẩm"


def test_normalize_teencode_text_does_not_match_inside_larger_token():
    d = {"ko": _safe("không")}
    assert normalize_teencode_text("depko123 vl", d) == "depko123 vl"


def test_normalize_teencode_text_leaves_unknown_words_untouched():
    d = {"ko": _safe("không")}
    assert normalize_teencode_text("Sản phẩm tốt", d) == "Sản phẩm tốt"


def test_normalize_teencode_text_returns_text_unchanged_for_blank_dict():
    assert normalize_teencode_text("Ko thích", {}) == "Ko thích"


def test_normalize_teencode_text_returns_none_for_none_input():
    assert normalize_teencode_text(None, {"ko": _safe("không")}) is None


def test_normalize_teencode_text_resolves_ambiguous_key_by_context_keyword():
    d = {"nc": _ambiguous(("nước", ["ngâm", "ướt"]), ("nói chung", ["chung", "tổng thể"]))}
    assert normalize_teencode_text("bị ngâm nc lâu quá", d) == "bị ngâm nước lâu quá"
    assert normalize_teencode_text("nhìn chung nc thì ổn", d) == "nhìn chung nói chung thì ổn"


def test_normalize_teencode_text_keeps_ambiguous_key_when_no_context_keyword_matches():
    d = {"nc": _ambiguous(("nước", ["ngâm", "ướt"]), ("nói chung", ["chung", "tổng thể"]))}
    assert normalize_teencode_text("máy này nc ổn", d) == "máy này nc ổn"


def test_normalize_teencode_text_keeps_ambiguous_key_when_both_candidates_match():
    d = {"nc": _ambiguous(("nước", ["ổn"]), ("nói chung", ["chung"]))}
    assert normalize_teencode_text("nhìn chung nc ổn", d) == "nhìn chung nc ổn"


def test_normalize_teencode_text_ambiguous_context_window_is_limited():
    d = {"nc": _ambiguous(("nước", ["ngâm"]), ("nói chung", ["chung"]))}
    far_prefix = "ngâm " + "x" * 60 + " "
    assert normalize_teencode_text(far_prefix + "nc ổn", d) == far_prefix + "nc ổn"


def test_contains_any_term_true_when_term_present():
    assert contains_any_term("Đẹp vl luôn", {"vl", "kp"}) is True


def test_contains_any_term_false_when_no_term_present():
    assert contains_any_term("Sản phẩm tốt", {"vl", "kp"}) is False


def test_contains_any_term_false_for_blank_text_or_terms():
    assert contains_any_term("", {"vl"}) is False
    assert contains_any_term(None, {"vl"}) is False
    assert contains_any_term("Đẹp vl", set()) is False


# --- normalize_teencode_and_abbreviations (T2.17 + T2.18) ----------------------

def test_normalize_teencode_and_abbreviations_uses_real_dictionary():
    df = pd.DataFrame({"Nội dung tự do": ["Ko thích sp này"]})

    result = normalize_teencode_and_abbreviations(df)
    print_row_diff(df, result, label="test_normalize_teencode_and_abbreviations_uses_real_dictionary")

    assert result.loc[0, "Nội dung tự do"] == "không thích sản phẩm này"


def test_normalize_teencode_and_abbreviations_keeps_blank_or_nan():
    df = pd.DataFrame({"Nội dung tự do": [None, "   "]})

    result = normalize_teencode_and_abbreviations(df)

    assert pd.isna(result.loc[0, "Nội dung tự do"])
    assert result.loc[1, "Nội dung tự do"] == "   "


def test_normalize_teencode_and_abbreviations_missing_content_col_returns_copy():
    df = pd.DataFrame({"Tác giả": ["An"]})

    result = normalize_teencode_and_abbreviations(df)

    pd.testing.assert_frame_equal(result, df)
    assert result is not df


def test_normalize_teencode_and_abbreviations_does_not_mutate_input():
    df = pd.DataFrame({"Nội dung tự do": ["Ko thích"]})
    df_copy = df.copy()

    normalize_teencode_and_abbreviations(df)

    pd.testing.assert_frame_equal(df, df_copy)


# --- split_suspect_teencode_reviews (T2.17 + T2.18) -----------------------------

def test_splits_out_review_containing_suspect_term():
    # 'kp' khong co trong dictionary/teencode_abbreviation.txt (chua ro nghia)
    # -> nam trong dictionary/suspect_teencode_terms.txt.
    df = pd.DataFrame({"Nội dung tự do": ["Đẹp kp luôn", "Sản phẩm tốt"]})

    kept, suspect = split_suspect_teencode_reviews(df)
    print_row_diff(df, kept, label="test_splits_out_review_containing_suspect_term")

    assert list(kept.index) == [1]
    assert list(suspect.index) == [0]


def test_splits_out_review_with_unresolved_ambiguous_key_after_normalize():
    # 'nc' la khoa DA NGHIA trong dictionary/teencode_abbreviation.txt
    # ('nuoc'/'noi chung') - khong co tu khoa ngu canh nao ro rang quanh no
    # trong cau duoi day nen normalize_teencode_and_abbreviations KHONG thay
    # the, va occurrence con nguyen nay phai bi tach ra suspect.
    df = pd.DataFrame({"Nội dung tự do": ["máy này nc ổn", "Sản phẩm tốt"]})

    normalized = normalize_teencode_and_abbreviations(df)
    kept, suspect = split_suspect_teencode_reviews(normalized)

    assert list(kept.index) == [1]
    assert list(suspect.index) == [0]


def test_does_not_split_blank_or_nan_content_for_suspect_teencode():
    df = pd.DataFrame({"Nội dung tự do": [None, "   "]})

    kept, suspect = split_suspect_teencode_reviews(df)

    pd.testing.assert_frame_equal(kept, df)
    assert suspect.empty


def test_missing_content_col_returns_copy_and_empty_suspect():
    df = pd.DataFrame({"Tác giả": ["An"]})

    kept, suspect = split_suspect_teencode_reviews(df)

    pd.testing.assert_frame_equal(kept, df)
    assert kept is not df
    assert suspect.empty


def test_preserves_original_index_for_suspect_teencode_split():
    df = pd.DataFrame(
        {"Nội dung tự do": ["tn quá", "Sản phẩm tốt", "Giá hơi mắc nhưng ổn", "kp đúng ý lắm"]}
    )

    kept, suspect = split_suspect_teencode_reviews(df)

    assert list(kept.index) == [1, 2]
    assert list(suspect.index) == [0, 3]


def test_does_not_mutate_input_for_suspect_teencode_split():
    df = pd.DataFrame({"Nội dung tự do": ["Đẹp kp luôn", "Sản phẩm tốt"]})
    df_copy = df.copy()

    split_suspect_teencode_reviews(df)

    pd.testing.assert_frame_equal(df, df_copy)


# --- T2.19 sua loi chinh ta -----------------------------------------------------

def test_is_vietnamese_syllable_accepts_real_words_and_rejects_typos():
    for ok in ["hàng", "đẹp", "nghiêng", "quần", "giá", "gì", "khuya", "tuyệt", "này", "ạ", "y", "hòa", "hoà"]:
        assert is_vietnamese_syllable(ok), ok
    for bad in ["hangf", "cũnh", "hj", "muq", "ok", "seal", "ngừoi", "kà", "cê"]:
        assert not is_vietnamese_syllable(bad), bad


def test_correct_spelling_text_telex_dictionary_and_edit_distance():
    vocab = {"hàng": 9, "cũng": 20, "tốt": 9}
    text, fixes = correct_spelling_text("Hangf tôts, cũnh xog, ngừoi", {"xog": "xong", "ngừoi": "người"}, set(), vocab)

    assert text == "Hàng tốt, cũng xong, người"
    assert [f[1] for f in fixes] == ["hàng", "tốt", "cũng", "xong", "người"]


def test_correct_spelling_text_leaves_foreign_repeated_numbers_and_unsure_alone():
    vocab = {"hàng": 9}
    # 'box' (whitelist), 'nhaaa' (T2.21), '2tr' (dinh so), 'iphone' (khong co cach sua chac chan)
    text, fixes = correct_spelling_text("box nhaaa 2tr iphone", {}, {"box"}, vocab)

    assert text == "box nhaaa 2tr iphone"
    assert fixes == []


def test_fix_spelling_errors_fixes_content_and_keeps_nan_and_input():
    # 'hàng' phải xuất hiện >= 2 lần trong chính df để vào từ điển ứng viên.
    df = pd.DataFrame({"Nội dung tự do": ["hangf đẹp", None, "hàng ổn", "hàng tốt"]})
    df_copy = df.copy()

    result = fix_spelling_errors(df)

    assert result["Nội dung tự do"].tolist()[0] == "hàng đẹp"
    assert pd.isna(result["Nội dung tự do"].iloc[1])
    pd.testing.assert_frame_equal(df, df_copy)


def test_split_spelling_error_reviews_adds_corrected_column_next_to_content():
    df = pd.DataFrame({
        "Tác giả": ["A", "B", "C", "D"],
        "Nội dung tự do": ["ổn", "hangf đẹp", "hàng ổn", "hàng tốt"],
        "Số sao": [5, 4, 5, 5],
    })

    kept, suspect = split_spelling_error_reviews(df)

    assert list(kept.index) == [0, 2, 3]
    assert list(suspect.index) == [1]
    assert list(suspect.columns) == ["Tác giả", "Nội dung tự do", "Nội dung sau xử lý", "Chi tiết sửa", "Số sao"]
    assert suspect.loc[1, "Nội dung tự do"] == "hangf đẹp"
    assert suspect.loc[1, "Nội dung sau xử lý"] == "hàng đẹp"
    assert suspect.loc[1, "Chi tiết sửa"] == "hangf -> hàng"


def test_split_spelling_error_reviews_missing_content_col_returns_copy_and_empty_suspect():
    df = pd.DataFrame({"Tác giả": ["An"]})

    kept, suspect = split_spelling_error_reviews(df)

    pd.testing.assert_frame_equal(kept, df)
    assert suspect.empty
