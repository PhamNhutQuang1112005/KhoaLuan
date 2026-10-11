"""
pipelines/pipeline_full.py
=============================
Thứ tự chạy toàn bộ quy trình theo "Kế hoạch tiền xử lý dữ liệu review tiếng
Việt cho bài toán ABSA": cấu trúc -> lọc rẻ -> làm sạch ký tự -> chuẩn hoá từ
vựng -> khử trùng lặp lần cuối. Mỗi giai đoạn kết thúc bằng 1 checkpoint
(config.settings.CHECKPOINT_VERSIONS).

`STAGES` chỉ là KHAI BÁO thứ tự (tên bước -> hàm). Bước đánh dấu (manual) là
bước tách file kiểm duyệt thủ công — pipeline phải dừng chờ file *_Checked.xlsx
rồi merge (theo review_id) trước khi đi tiếp.

Luồng chạy hiện tại (đã có kết quả) vẫn là các script trong scripts/legacy/.
"""

from typing import Iterable

from transforms import (
    stage0_prepare as s0,
    stage1_structure as s1,
    stage2_normalize as s2,
    stage3_coarse_filter as s3,
    stage4_char_noise as s4,
    stage5_short_filter as s5,
    stage6_lexical as s6,
    stage7_final_dedup as s7,
)

# (checkpoint, [(bước theo kế hoạch, hàm, manual_review)])
STAGES = [
    ("v0_raw", [
        ("Gán review_id + review_raw", s0.assign_review_id, False),
    ]),
    ("v1_structured", [
        ("Bước 1 — lệch cột", s1.fix_field_misalignment, False),
        ("Bước 2 — dòng trống / thiếu cột bắt buộc", s1.drop_empty_rows, False),
        ("Bước 3 — ép kiểu thời gian", s1.fix_data_types, False),
        ("Bước 4 — tách tiêu chí đánh giá", s1.split_merged_fields, False),
    ]),
    ("v2_normalized", [
        ("Bổ sung — Unicode NFC, dấu thanh, HTML", s2.normalize_unicode_and_html, False),
        ("Bước 16 — khoảng trắng (lượt 1)", s2.strip_extra_whitespace, False),
        ("Bước 17 — cột text_norm", s2.add_text_norm_column, False),
    ]),
    ("v3_filtered", [
        ("Bước 8a — trùng lặp chính xác trong file", s3.drop_exact_duplicates, False),
        ("Bước 21a — trùng lặp chính xác giữa các file", s3.drop_exact_duplicates_across_files, False),
        ("Bước 5 — chỉ emoji / ký tự đặc biệt", s3.drop_emoji_or_special_char_only_reviews, False),
        ("Bước 7 — URL quảng cáo / spam", s3.split_url_hotline_or_spam_reviews, True),
        ("Bước 19 — không phải tiếng Việt", s3.split_non_vietnamese_reviews, True),
    ]),
    ("v4_char_cleaned", [
        ("Bước 14 — emoji xen giữa câu", s4.handle_inline_emoji, False),
        ("Bước 15 — ký tự đặc biệt vô nghĩa", s4.remove_meaningless_special_chars, False),
        ("Bước 13 — lặp ký tự", s4.normalize_repeated_characters, False),
        ("Bước 16 — khoảng trắng (lượt 2)", s2.strip_extra_whitespace, False),
        ("Bước 17 — làm mới text_norm", s2.add_text_norm_column, False),
    ]),
    ("v5_length_filtered", [
        ("Bước 6 — review <= 4 từ", s5.split_short_reviews, True),
    ]),
    ("v6_lexical", [
        ("Bước 9 + 10 — teencode, viết tắt", s6.normalize_teencode_and_abbreviations, False),
        ("Bước 9 + 10 — teencode nghi vấn", s6.split_suspect_teencode_reviews, True),
        ("Bước 18 — tiếng Anh / từ mượn (protected tokens)", s6.mark_protected_tokens, False),
        ("Bước 12 — khôi phục dấu", s6.restore_diacritics, False),
        ("Bước 11 — lỗi chính tả", s6.split_spelling_error_reviews, True),
        ("Bước 20 — tiếng lóng cảm xúc", s6.normalize_emotional_slang, False),
    ]),
    ("v7_final", [
        ("Bước 8b — gần trùng lặp trong file", s7.split_near_duplicate_reviews, True),
        ("Bước 21b — gần trùng lặp giữa các file", s7.split_cross_file_near_duplicates, True),
        ("Kiểm tra cuối", s7.final_check, False),
    ]),
]


def run(products: Iterable[str], until: str | None = None):
    """Chạy lần lượt `STAGES` cho `products`, lưu checkpoint sau mỗi giai
    đoạn (dataio.checkpoint.save_checkpoint), dừng ở checkpoint `until` nếu
    có, và dừng chờ kiểm duyệt ở bước manual_review=True.

    TODO: implement.
    """
    raise NotImplementedError
