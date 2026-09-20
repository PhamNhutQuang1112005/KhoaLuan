"""
transforms/tang2_content_quality.py
=====================================
TẦNG 2 — CHẤT LƯỢNG & NHIỄU CỦA NỘI DUNG REVIEW (24 mục theo taxonomy).

Chia 3 nhóm con (giữ nguyên theo taxonomy để dễ đối chiếu):
  2.1 Nội dung không có giá trị      (T2.9  .. T2.16) — T2.9+T2.10 ĐÃ GỘP
      CHUNG thành `drop_emoji_or_special_char_only_reviews` (cùng 1 tiêu chí
      "nội dung chỉ toàn emoji/ký tự đặc biệt, không mang thông tin"); T2.11+
      T2.12 ĐÃ GỘP CHUNG thành `split_short_reviews` — KHÔNG tự động xoá,
      chỉ TÁCH RIÊNG review ngắn (<= SHORT_REVIEW_MAX_WORDS từ) ra 1 nhóm để
      con người rà soát thủ công (xem docstring hàm để biết lý do); T2.13+
      T2.14 ĐÃ GỘP CHUNG thành `split_url_hotline_or_spam_reviews` — CŨNG
      KHÔNG tự động xoá, chỉ TÁCH RIÊNG review nghi vấn URL/SĐT ra
      `Suspect_URL_Spam.xlsx` để con người rà soát thủ công (giống hệt tinh
      thần T2.11+T2.12), dùng chung 1 bộ lọc regex URL/số điện thoại — xem
      `utils_text.contains_url` + `utils_text.contains_phone_number` — kiểm
      tra CẢ cột 'Nội dung tự do' LẪN 'Tiêu chí đánh giá', khác với
      T2.9+T2.10/T2.11+T2.12 vốn chỉ xoá/tách khi CẢ 2 cột ĐỒNG THỜI không
      hữu ích. CỐ TÌNH KHÔNG bắt theo từ khoá kiểu 'zalo'/'ib'/'hotline'
      đứng riêng — rà soát thực tế cho thấy các từ này xuất hiện rất nhiều
      trong review THẬT (vd than phiền máy không cài được Zalo, khen shop
      trả lời inbox nhanh), bắt theo từ khoá gây tách nhầm hàng loạt dữ liệu
      hữu ích vào diện nghi vấn. T2.15 `drop_exact_duplicates` — XOÁ HẲN (tự
      động, không cần rà soát) review trùng lặp TUYỆT ĐỐI theo 'Nội dung tự
      do' + 'Tác giả' (dấu hiệu chắc chắn của lỗi crawl trùng, không phải suy
      đoán). T2.16 `split_near_duplicate_reviews` — theo ĐÚNG tinh thần
      T2.11+T2.12/T2.13+T2.14 (KHÔNG tự động xoá), chỉ TÁCH RIÊNG cặp review
      NGHI VẤN gần trùng (similarity theo `utils_text.text_similarity` >=
      ngưỡng `config.settings.NEAR_DUPLICATE_SIMILARITY_THRESHOLD`) GIỮA 2
      TÁC GIẢ KHÁC NHAU ra `Suspect_Duplicate_Content.xlsx` để con người rà
      soát thủ công, lưu lại thành `Suspect_Duplicate_Content_Checked.xlsx`
      rồi chạy `Merge_Suspect_Duplicate_Content_Checked.py` để hoà lại — xem
      `run_t216.py`.
  2.2 Nhiễu biểu diễn                 (T2.17 .. T2.27) — T2.17+T2.18 ĐÃ GỘP
      CHUNG thành `normalize_teencode_and_abbreviations` (dùng chung 1 từ
      điển `dictionary/teencode_abbreviation.txt`, xem docstring hàm), CÙNG
      TINH THẦN "chỉ tách để rà soát thủ công" của nhóm 2.1: từ nghi vấn
      (không đủ tự tin thêm vào từ điển) được `split_suspect_teencode_reviews`
      tách ra `Suspect_Teencode_Abbreviation.xlsx` — xem `run_t218.py`. T2.19
      `fix_spelling_errors` / `split_spelling_error_reviews` — dòng có lỗi
      chính tả được tách ra `Suspect_Spelling_Errors.xlsx` kèm cột 'Nội dung
      sau xử lý' (đề xuất sửa) để con người kiểm duyệt — xem `run_t219.py`.
  2.3 Nội dung cần giữ lại, KHÔNG xoá (T2.28 .. T2.32)

LƯU Ý QUAN TRỌNG cho nhóm 2.3: các hàm trong nhóm này không phải hàm "làm sạch"
theo nghĩa loại bỏ, mà là hàm NHẬN DIỆN/ĐÁNH DẤU để đảm bảo các bước ở nhóm 2.1/2.2
không vô tình xoá mất tín hiệu cảm xúc quan trọng (phủ định, nhấn mạnh, tiếng lóng...).
Cân nhắc thiết kế: mỗi hàm 2.3 trả về DataFrame có thêm cột cờ đánh dấu (flag),
không xoá dữ liệu.
"""

from difflib import SequenceMatcher

import pandas as pd

from config.settings import NEAR_DUPLICATE_SIMILARITY_THRESHOLD
from dataio.dictionary_loader import (
    load_spelling_errors_dict,
    load_spelling_whitelist,
    load_suspect_teencode_terms,
    load_teencode_dict,
)
from transforms.tang1_structural import AUTHOR_COL, CRITERIA_COL
from transforms.utils_text import (
    build_syllable_vocab,
    contains_any_term,
    correct_spelling_text,
    contains_phone_number,
    contains_url,
    is_emoji_or_special_char_only,
    normalize_teencode_text,
    text_similarity,
)

CONTENT_COL = "Nội dung tự do"
CORRECTED_CONTENT_COL = "Nội dung sau xử lý"  # T2.19: cột đề xuất sửa, để con người kiểm duyệt
CORRECTION_DETAIL_COL = "Chi tiết sửa"  # T2.19: 'từ sai -> từ đúng; ...'


def _is_blank_value(value) -> bool:
    """True nếu 1 giá trị ô đơn lẻ là rỗng (NaN/None hoặc chuỗi chỉ khoảng
    trắng) — dùng để kiểm tra 'Tiêu chí đánh giá' còn giá trị hay không trước
    khi quyết định xoá dòng ở các hàm T2.9+T2.10 / T2.11+T2.12 bên dưới.
    """
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def _criteria_is_blank_series(df: pd.DataFrame, criteria_col: str) -> pd.Series:
    """Trả về Series bool: dòng nào có `criteria_col` rỗng.

    Nếu `criteria_col` không tồn tại trong `df`: coi như rỗng ở MỌI dòng
    (không có giá trị nào cho trường này trong toàn bộ dữ liệu) — nhất quán
    với cách `tang1_structural.drop_empty_rows` xử lý cột bắt buộc bị thiếu
    hẳn.
    """
    if criteria_col not in df.columns:
        return pd.Series(True, index=df.index)
    return df[criteria_col].apply(_is_blank_value)

# --- T2.11 + T2.12: ngưỡng số từ để coi là "review ngắn" --------------------
# QUYẾT ĐỊNH THIẾT KẾ (thay cho heuristic gõ bừa/khớp stop-phrase cũ): thay vì
# tự động ĐOÁN và XOÁ review ngắn theo heuristic (dễ bắt nhầm/bỏ sót — vd
# heuristic cũ không có từ điển nên không phủ hết biến thể chính tả, và có
# nguy cơ xoá nhầm review ngắn nhưng hữu ích), MỌI review <= ngưỡng số từ dưới
# đây được TÁCH RIÊNG ra 1 nhóm để con người rà soát thủ công (xem
# `split_short_reviews`) — tránh lãng phí dữ liệu do máy quyết định sai.
SHORT_REVIEW_MAX_WORDS = 4


def is_short_review(text, max_words: int = SHORT_REVIEW_MAX_WORDS) -> bool:
    """T2.11 + T2.12 — True nếu `text` (sau khi strip khoảng trắng) có
    <= `max_words` từ (đếm bằng `str.split()` theo khoảng trắng).

    Chuỗi rỗng/toàn khoảng trắng/None trả về False (phạm vi T1.3, không phải
    T2.11/T2.12).
    """
    if text is None:
        return False
    stripped = str(text).strip()
    if not stripped:
        return False
    return len(stripped.split()) <= max_words


# --- 2.1 Nội dung không có giá trị ------------------------------------------

def drop_emoji_or_special_char_only_reviews(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
    criteria_col: str = CRITERIA_COL,
) -> pd.DataFrame:
    """T2.9 + T2.10 (GỘP CHUNG) — Xoá HẲN dòng khi CẢ 2 điều kiện sau ĐỒNG THỜI
    đúng:
      1. `content_col` ('Nội dung tự do'), sau khi strip khoảng trắng, CHỈ
         gồm emoji và/hoặc ký tự đặc biệt (không có chữ/số nào mang thông
         tin) — dùng `utils_text.is_emoji_or_special_char_only`.
      2. `criteria_col` ('Tiêu chí đánh giá') CŨNG rỗng (không có giá trị).

    Vì sao cần điều kiện 2: nhất quán với nguyên tắc T1.2+T1.3 (xem
    `tang1_structural.drop_empty_rows`) — 1 dòng chỉ thực sự "không mang giá
    trị gì cho ABSA" khi CẢ 2 trường bắt buộc đều rỗng/không hữu ích. Nếu
    `criteria_col` CÓ giá trị (vd 'Pin: tốt') thì dòng vẫn hữu ích cho ABSA dù
    'Nội dung tự do' chỉ là '!!! 😊' -> PHẢI GIỮ LẠI, không được xoá theo
    `content_col` một mình.

    Vì sao gộp T2.9 (chỉ emoji) và T2.10 (chỉ ký tự đặc biệt) làm 1: cả 2 cùng
    chung 1 tiêu chí "nội dung không mang giá trị thông tin gì cho ABSA" —
    khác biệt duy nhất là LOẠI ký tự (emoji hay dấu câu/ký hiệu), còn quyết
    định xử lý (xoá dòng) là NHƯ NHAU; nội dung trộn lẫn cả 2 loại (vd
    '!!! 😊') cũng tính, không cần tách riêng 2 lượt quét cho cùng 1 dòng.

    Dòng có nội dung rỗng/NaN hoàn toàn KHÔNG bị xoá ở đây (không phải "chỉ
    emoji/ký tự đặc biệt" — đơn giản là không có nội dung) — đó là phạm vi
    của T1.3 (`tang1_structural.drop_empty_rows`), PHẢI chạy TRƯỚC bước này.

    Nếu `content_col` không tồn tại trong `df`: trả về bản sao nguyên vẹn,
    không xoá dòng nào (không đủ thông tin để đánh giá). Nếu `criteria_col`
    không tồn tại: coi như rỗng ở mọi dòng (xem `_criteria_is_blank_series`).

    Hàm thuần: không sửa `df` gốc, không I/O. Giữ nguyên index gốc của các
    dòng còn lại (để truy vết đúng số dòng đã xoá qua core.diff_report).
    """
    if content_col not in df.columns:
        return df.copy()

    content = df[content_col]
    content_only_noise = content.apply(
        lambda value: False if pd.isna(value) else is_emoji_or_special_char_only(value)
    )
    criteria_blank = _criteria_is_blank_series(df, criteria_col)

    should_drop = content_only_noise & criteria_blank
    return df.loc[~should_drop].copy()


def split_short_reviews(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
    criteria_col: str = CRITERIA_COL,
    max_words: int = SHORT_REVIEW_MAX_WORDS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """T2.11 + T2.12 (ĐÃ ĐỔI CÁCH XỬ LÝ — không còn tự động XOÁ) — TÁCH dòng
    thành 2 nhóm (kept_df, short_df) thay vì xoá hẳn, để con người tự rà soát
    thủ công nhóm review ngắn thay vì để heuristic quyết định (tránh lãng phí
    dữ liệu do bắt nhầm/bỏ sót).

    Một dòng thuộc nhóm `short_df` khi CẢ 2 điều kiện sau ĐỒNG THỜI đúng:
      1. `content_col` ('Nội dung tự do'), sau khi strip khoảng trắng, có
         <= `max_words` từ — xem `is_short_review`.
      2. `criteria_col` ('Tiêu chí đánh giá') CŨNG rỗng (không có giá trị).

    Vì sao cần điều kiện 2: nhất quán với nguyên tắc T1.2+T1.3 (xem
    `tang1_structural.drop_empty_rows`) — 1 dòng chỉ thực sự cần tách riêng
    khi CẢ 2 trường bắt buộc đều rỗng/ngắn. Nếu `criteria_col` CÓ giá trị (vd
    'Pin: tốt') thì dòng vẫn hữu ích cho ABSA dù 'Nội dung tự do' ngắn -> GIỮ
    NGUYÊN trong `kept_df`, không tách.

    Dòng có nội dung rỗng/NaN hoàn toàn KHÔNG bị tách ở đây — đó là phạm vi
    của T1.3 (`tang1_structural.drop_empty_rows`), PHẢI chạy TRƯỚC bước này.

    Nếu `content_col` không tồn tại trong `df`: trả về (df.copy(), df rỗng
    cùng cột) — không đủ thông tin để tách. Nếu `criteria_col` không tồn tại:
    coi như rỗng ở mọi dòng (xem `_criteria_is_blank_series`).

    Hàm thuần: không sửa `df` gốc, không I/O. Giữ nguyên index gốc của các
    dòng ở cả 2 DataFrame trả về (để truy vết đúng số dòng qua
    core.diff_report / khi ghép nhiều file lại ở run_t212.py).
    """
    if content_col not in df.columns:
        return df.copy(), df.iloc[0:0].copy()

    content = df[content_col]
    content_is_short = content.apply(
        lambda value: False if pd.isna(value) else is_short_review(value, max_words)
    )
    criteria_blank = _criteria_is_blank_series(df, criteria_col)

    should_split = content_is_short & criteria_blank
    return df.loc[~should_split].copy(), df.loc[should_split].copy()


def _is_url_or_hotline_ad(value) -> bool:
    """True nếu 1 giá trị ô đơn lẻ có chứa URL hoặc số điện thoại — dùng
    CHUNG cho cả 2 cột (`content_col` lẫn `criteria_col`) trong
    `split_url_hotline_or_spam_reviews`, vì quảng cáo có thể bị chèn vào bất
    kỳ cột nào tuỳ theo cách crawl/dán nhầm, không riêng gì 'Nội dung tự
    do'."""
    if pd.isna(value):
        return False
    return contains_url(value) or contains_phone_number(value)


def split_url_hotline_or_spam_reviews(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
    criteria_col: str = CRITERIA_COL,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """T2.13 + T2.14 (GỘP CHUNG — KHÔNG tự động XOÁ) — TÁCH dòng thành 2 nhóm
    (kept_df, suspect_df) thay vì xoá hẳn, để con người tự rà soát thủ công
    nhóm nghi vấn thay vì để regex quyết định luôn (tránh lãng phí dữ liệu do
    bắt nhầm/bỏ sót — xem `split_short_reviews` T2.11+T2.12, đã áp dụng đúng
    tinh thần này trước đó; T2.13+T2.14 CŨNG đổi theo sau khi rà soát thực tế
    phát hiện quy tắc xoá tự động từng bắt nhầm nhiều review THẬT).

    Một dòng thuộc nhóm `suspect_df` khi `content_col` ('Nội dung tự do')
    HOẶC `criteria_col` ('Tiêu chí đánh giá') có chứa URL
    (`utils_text.contains_url`) và/hoặc số điện thoại
    (`utils_text.contains_phone_number`) — dùng CHUNG 1 bộ lọc regex URL/số
    điện thoại cho cả 2 mục T2.13 và T2.14, vì cả 2 cùng là "nội dung quảng
    cáo/hotline chèn vào review" (khác biệt duy nhất chỉ là URL/SĐT chiếm
    TOÀN BỘ nội dung — T2.13 — hay bị CHÈN LẪN vào giữa review thật — T2.14),
    còn quyết định TÁCH RIÊNG để rà soát là NHƯ NHAU.

    CỐ TÌNH KHÔNG bắt theo từ khoá kiểu 'zalo'/'ib'/'inbox'/'hotline'/'sđt'
    đứng riêng (không kèm URL/số cụ thể): rà soát thực tế trên data/interim
    cho thấy các từ này xuất hiện RẤT NHIỀU trong review THẬT — vd "Ko cài đc
    zalo, zoom... tiền nào của ấy" (đang chê tính năng máy, KHÔNG phải quảng
    cáo), "shop rep ib nhanh" (khen thái độ phục vụ), "Gọi lên hotline hỏi
    thì..." (kể lại trải nghiệm, không phải chèn quảng cáo). Chỉ URL tường
    minh và số điện thoại dạng chuỗi số thật mới đủ tin cậy làm căn cứ tách.

    KIỂM TRA CẢ 2 CỘT (khác với T2.9+T2.10/T2.11+T2.12 chỉ xoá/tách khi CẢ 2
    trường bắt buộc ĐỒNG THỜI không hữu ích): URL/SĐT là nội dung đáng ngờ dù
    xuất hiện ở cột nào — cột còn lại có giá trị thật hay không cũng KHÔNG
    "cứu" được dòng khỏi bị đưa vào diện rà soát, vì bản thân cột chứa
    URL/SĐT đã là dấu hiệu nhiễu cho ABSA. Do đó chỉ cần 1 trong 2 cột dính
    URL/SĐT là đủ để tách dòng vào `suspect_df`.

    Dòng có nội dung rỗng/NaN hoàn toàn KHÔNG bị tách ở đây (không chứa
    URL/SĐT nào cả) — đó là phạm vi của T1.3, PHẢI chạy TRƯỚC bước này.

    Nếu CẢ `content_col` lẫn `criteria_col` đều không tồn tại trong `df`: trả
    về (df.copy(), df rỗng cùng cột) — không đủ thông tin để tách. Nếu chỉ 1
    trong 2 cột tồn tại: chỉ kiểm tra cột đó.

    Hàm thuần: không sửa `df` gốc, không I/O. Giữ nguyên index gốc của các
    dòng ở cả 2 DataFrame trả về (để truy vết đúng số dòng qua
    core.diff_report / khi ghép nhiều file lại ở run_t214.py).
    """
    has_content_col = content_col in df.columns
    has_criteria_col = criteria_col in df.columns
    if not has_content_col and not has_criteria_col:
        return df.copy(), df.iloc[0:0].copy()

    is_ad_or_spam = pd.Series(False, index=df.index)
    if has_content_col:
        is_ad_or_spam = is_ad_or_spam | df[content_col].apply(_is_url_or_hotline_ad)
    if has_criteria_col:
        is_ad_or_spam = is_ad_or_spam | df[criteria_col].apply(_is_url_or_hotline_ad)

    return df.loc[~is_ad_or_spam].copy(), df.loc[is_ad_or_spam].copy()


# Nhãn tác giả CHUNG dùng để hiện thị review ẩn danh/không xác định trên các
# sàn TMĐT (Shopee/Lazada/Tiki...) — rà soát thực tế trên data/interim cho
# thấy giá trị này lặp lại 4-9 lần/sản phẩm và KHÔNG hề đại diện cho 1 tác giả
# duy nhất (chỉ là placeholder "không biết ai viết"). Coi ĐÂY LÀ TRƯỜNG HỢP
# "author rỗng" (không đủ thông tin định danh) khi ghép cặp trùng lặp ở
# `drop_exact_duplicates`, để tránh 2 review THẬT của 2 khách ẩn danh KHÁC
# NHAU nhưng tình cờ viết cùng 1 câu ngắn phổ biến (vd "Ổn", "Tốt") bị xoá
# nhầm lẫn nhau — khác với username đã bị MASK một phần (vd 't*****2') vẫn
# giữ nguyên vai trò định danh vì mỗi giá trị mask vẫn bám theo 1 username gốc
# cụ thể (rủi ro trùng ngẫu nhiên giữa 2 username gốc khác nhau thấp hơn
# nhiều so với 1 placeholder dùng chung cho MỌI người ẩn danh).
_ANONYMOUS_AUTHOR_LABELS = {"ẩn danh"}


def _dedup_key_series(df: pd.DataFrame, content_col: str, author_col: str) -> tuple[pd.Series, pd.Series]:
    """Trả về (key, has_key) dùng chung cho `drop_exact_duplicates`.

    `key` là chuỗi/tuple dùng để so trùng lặp (đã strip khoảng trắng); `has_key`
    là Series bool đánh dấu dòng nào ĐỦ thông tin để tham gia so trùng (content
    KHÔNG rỗng, và nếu có `author_col` thì author CŨNG không rỗng/không phải
    nhãn ẩn danh chung — xem `_ANONYMOUS_AUTHOR_LABELS`) — dòng thiếu thông
    tin không bao giờ bị coi là trùng lặp với dòng khác.
    """
    content = df[content_col].apply(
        lambda v: None if pd.isna(v) or str(v).strip() == "" else str(v).strip()
    )
    has_content = content.notna()

    if author_col not in df.columns:
        return content, has_content

    def _normalize_author(v):
        if pd.isna(v) or str(v).strip() == "":
            return None
        stripped = str(v).strip()
        if stripped.lower() in _ANONYMOUS_AUTHOR_LABELS:
            return None
        return stripped

    author = df[author_col].apply(_normalize_author)
    key = pd.Series(list(zip(author, content)), index=df.index)
    return key, has_content & author.notna()


def drop_exact_duplicates(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
    author_col: str = AUTHOR_COL,
) -> pd.DataFrame:
    """T2.15 — Xoá HẲN review trùng lặp HOÀN TOÀN (trong cùng 1 file/sản phẩm),
    khác với T2.16 (chỉ TÁCH RIÊNG để rà soát thủ công) vì đây là dấu hiệu
    RẤT chắc chắn của lỗi crawl (cào trùng cùng 1 review nhiều lần) chứ không
    phải suy đoán — an toàn để tự động xoá mà không cần con người xác nhận
    lại, không giống các mục 2.1 khác đã đổi hướng sang "chỉ tách" (xem
    `split_short_reviews`, `split_url_hotline_or_spam_reviews`).

    Một dòng bị coi là trùng lặp khi khớp CHÍNH XÁC (sau khi strip khoảng
    trắng) với 1 dòng ĐỨNG TRƯỚC nó (theo thứ tự trong `df`) trên:
      - `content_col` ('Nội dung tự do'), VÀ
      - `author_col` ('Tác giả'), NẾU cột này tồn tại trong `df` (nhất quán
        với gợi ý trong taxonomy: "dựa trên 'Nội dung tự do' + có thể +
        'Tác giả'"). Nếu `author_col` không tồn tại: chỉ so theo `content_col`.

    Vì sao CẦN thêm `author_col` khi có: chỉ so `content_col` một mình có
    nguy cơ xoá nhầm 2 review THẬT của 2 khách hàng khác nhau nhưng tình cờ
    viết giống hệt nhau (vd cùng gõ 'Sản phẩm tốt, giao hàng nhanh') — thêm
    điều kiện CÙNG tác giả mới đủ chắc chắn đây là 1 review bị crawl trùng,
    không phải 2 review độc lập trùng nội dung ngẫu nhiên.

    AN TOÀN VỚI NHÃN "ẨN DANH" DÙNG CHUNG: rà soát thực tế trên data/interim
    cho thấy nhiều sàn TMĐT hiện tên tác giả review ẩn danh bằng đúng 1 chuỗi
    CHUNG ('ẩn danh') cho MỌI khách không muốn hiện tên — đây KHÔNG phải 1
    định danh duy nhất, nên nếu dùng thẳng làm 1 phần của key thì 2 khách ẩn
    danh KHÁC NHAU cùng viết 1 câu ngắn phổ biến (vd 'Ổn', 'Tốt') sẽ bị hiểu
    lầm là "cùng tác giả" và bị xoá nhầm. Vì vậy `_dedup_key_series` coi nhãn
    này (xem `_ANONYMOUS_AUTHOR_LABELS`, so KHÔNG phân biệt hoa/thường) như
    'author rỗng' — dòng có tác giả ẩn danh KHÔNG BAO GIỜ được ghép cặp trùng
    lặp với dòng khác chỉ qua đường author, dù nội dung khớp tuyệt đối. Ngược
    lại, username đã bị website MASK một phần (vd 't*****2') VẪN được coi là
    định danh hợp lệ, vì mỗi giá trị mask vẫn bám theo 1 username gốc cụ thể
    (đã kiểm chứng thực tế: mọi cặp trùng lặp phát hiện được với author dạng
    mask trong data/interim đều có 'Thời điểm cào'/'Thời gian' xảy ra trong
    cùng vài phút, khớp với việc 1 khách mua nhiều biến thể/SKU trong CÙNG 1
    đơn và review bị lặp lại theo từng dòng SKU — không phải trùng ngẫu nhiên
    giữa 2 khách khác nhau).

    CỐ TÌNH KHÔNG xét `criteria_col`: nếu 'Nội dung tự do' (+ 'Tác giả') đã
    khớp tuyệt đối thì đã đủ chắc chắn là dòng bị crawl trùng, dù 'Thời điểm
    cào' hay 'Tiêu chí đánh giá' có thể khác nhau đôi chút giữa 2 lần crawl.

    CỐ TÌNH KHÔNG yêu cầu 'Thời gian' (thời điểm đăng review) phải gần nhau:
    rà soát thực tế cho thấy nhiều cặp trùng lặp THẬT của CÙNG 1 tác giả lại
    cách nhau HÀNG THÁNG (vd cùng 1 username đăng lại đúng 1 đoạn review dài
    cho 1 lần mua khác) — nếu bắt buộc 'Thời gian' phải gần nhau sẽ BỎ SÓT
    chính những trường hợp trùng lặp rõ ràng nhất (nội dung dài, đặc thù,
    khớp tuyệt đối từng ký tự).

    Dòng có `content_col` rỗng/NaN (hoặc `author_col` rỗng/NaN/là nhãn ẩn danh
    dùng chung khi cột này tồn tại) KHÔNG bao giờ bị coi là trùng lặp ở đây —
    không đủ thông tin để kết luận, và nội dung rỗng hoàn toàn là phạm vi của
    T1.3.

    Nếu `content_col` không tồn tại trong `df`: trả về bản sao nguyên vẹn,
    không xoá dòng nào.

    Hàm thuần: không sửa `df` gốc, không I/O. Giữ nguyên index gốc của các
    dòng còn lại (để truy vết đúng số dòng đã xoá qua core.diff_report), và
    LUÔN giữ lại lần xuất hiện ĐẦU TIÊN (theo thứ tự dòng gốc) của mỗi cặp
    trùng lặp, chỉ xoá các lần xuất hiện SAU.
    """
    if content_col not in df.columns:
        return df.copy()

    key, has_key = _dedup_key_series(df, content_col, author_col)
    is_duplicate = has_key & key.duplicated(keep="first")
    return df.loc[~is_duplicate].copy()


def split_near_duplicate_reviews(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
    author_col: str = AUTHOR_COL,
    similarity_threshold: float = NEAR_DUPLICATE_SIMILARITY_THRESHOLD,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """T2.16 — TÁCH dòng thành 2 nhóm (kept_df, suspect_df) — KHÔNG tự động
    xoá — cùng tinh thần với `split_short_reviews`/`split_url_hotline_or_spam_reviews`:
    similarity chỉ là suy đoán (có thể trùng ngẫu nhiên vì cùng phàn nàn/khen 1
    đặc điểm phổ biến bằng câu từ tương tự), nên cần con người rà soát thủ
    công thay vì để máy xoá luôn — xem `Suspect_Duplicate_Content.xlsx` /
    `run_t216.py`.

    Phát hiện bằng cơ chế similarity: với MỌI cặp dòng (i, j) có TÁC GIẢ KHÁC
    NHAU trong `df`, nếu `utils_text.text_similarity` giữa `content_col` của
    2 dòng >= `similarity_threshold` (mặc định
    `config.settings.NEAR_DUPLICATE_SIMILARITY_THRESHOLD`), CẢ 2 dòng đều
    được đưa vào `suspect_df`.

    CỐ TÌNH CHỈ so sánh giữa các tác giả KHÁC NHAU (không so trong cùng 1 tác
    giả): review gần giống nhau của CÙNG 1 người (vd sửa lại review cũ, hoặc
    2 review về 2 sản phẩm khác nhau nhưng cùng thói quen hành văn) không
    phải dấu hiệu nghi vấn — dấu hiệu đáng ngờ (review ảo/copy hàng loạt/1
    người dùng nhiều tài khoản) là khi 2 TÁC GIẢ KHÁC NHAU lại viết nội dung
    gần như y hệt nhau. Trường hợp trùng tuyệt đối CÙNG tác giả đã được xử lý
    dứt điểm (xoá hẳn) ở T2.15 (`drop_exact_duplicates`) — hàm này không xử
    lý lại.

    Dòng có `content_col` hoặc `author_col` rỗng/NaN KHÔNG tham gia so sánh
    (không đủ thông tin để xác định "khác tác giả" hay để tính similarity) —
    các dòng này luôn ở lại `kept_df`.

    Nếu `content_col` hoặc `author_col` không tồn tại trong `df`: trả về
    (df.copy(), df rỗng cùng cột) — không đủ thông tin để tách.

    Hàm thuần: không sửa `df` gốc, không I/O. Giữ nguyên index gốc của các
    dòng ở cả 2 DataFrame trả về (để truy vết đúng số dòng qua
    core.diff_report / khi ghép nhiều file lại ở run_t216.py).

    LƯU Ý HIỆU NĂNG: về lý thuyết đây là bài toán so sánh MỌI CẶP dòng ĐỦ
    ĐIỀU KIỆN (content + author đều không rỗng) — O(n^2) cặp. Trên thực tế
    KHÔNG cần tính `text_similarity` đầy đủ cho từng cặp: với
    `difflib.SequenceMatcher.ratio() = 2*M/(len(a)+len(b))` và `M <=
    min(len(a), len(b))`, ta có chặn trên `ratio <= 2*min(len(a),len(b)) /
    (len(a)+len(b))` — 2 chuỗi có độ dài CHÊNH LỆCH quá xa KHÔNG BAO GIỜ đạt
    được `similarity_threshold`, dù nội dung có giống nhau đến đâu. Vì vậy
    sắp dòng theo độ dài `content_col` rồi CHỈ so cặp có độ dài đủ gần nhau
    (dùng cửa sổ trượt, dừng sớm khi vượt ngưỡng độ dài — xem code) — kết quả
    TOÁN HỌC TƯƠNG ĐƯƠNG hoàn toàn với việc so MỌI cặp (không bỏ sót cặp nào
    thật sự đạt ngưỡng), chỉ nhanh hơn nhiều trong thực tế vì review dài/ngắn
    chênh lệch nhiều bị loại ngay mà không cần tính `text_similarity`.

    Với các cặp lọt qua chặn độ dài ở trên, còn dùng thêm
    `SequenceMatcher.quick_ratio()` làm bước lọc rẻ thứ 2 TRƯỚC KHI gọi
    `text_similarity` (vốn tính `ratio()` đầy đủ, tốn hơn):
    `quick_ratio()` LUÔN >= `ratio()` thật (chặn trên dựa trên tần suất ký tự
    chung, không xét thứ tự) nên lọc bằng `quick_ratio()` KHÔNG bao giờ bỏ sót
    cặp thật sự đạt `similarity_threshold` — chỉ loại sớm chắc chắn KHÔNG đạt.
    Đo thực nghiệm trên data/interim thực tế: giảm ~99% số lần phải tính
    `ratio()` đầy đủ so với chỉ lọc bằng độ dài.
    """
    if content_col not in df.columns or author_col not in df.columns:
        return df.copy(), df.iloc[0:0].copy()

    content = df[content_col]
    author = df[author_col]
    normalized_content: dict = {}
    normalized_author: dict = {}
    for idx in df.index:
        c, a = content[idx], author[idx]
        if pd.isna(c) or str(c).strip() == "" or pd.isna(a) or str(a).strip() == "":
            continue
        # Lowercase san o day de khop dung normalize hoa/thuong ma
        # text_similarity ap dung, dam bao quick_ratio() (dung de loc) va
        # ratio() (dung de xac nhan qua text_similarity) tinh tren CUNG 1
        # cap chuoi da chuan hoa.
        normalized_content[idx] = str(c).strip().lower()
        normalized_author[idx] = str(a).strip()

    by_length = sorted(normalized_content, key=lambda idx: len(normalized_content[idx]))
    n = len(by_length)

    is_suspect = pd.Series(False, index=df.index)
    matcher = SequenceMatcher()
    for i in range(n):
        idx_i = by_length[i]
        content_i = normalized_content[idx_i]
        len_i = len(content_i)
        # Chan tren do dai chuoi thu 2 de con co co hoi dat similarity_threshold
        # (suy tu ratio <= 2*len_i/(len_i+len_j) >= similarity_threshold).
        max_len_j = float("inf") if similarity_threshold <= 0 else len_i * (2 / similarity_threshold - 1)
        matcher.set_seq2(content_i)
        for j in range(i + 1, n):
            idx_j = by_length[j]
            content_j = normalized_content[idx_j]
            if len(content_j) > max_len_j:
                break  # by_length da sap theo do dai tang dan -> cac j sau cung vuot nguong
            if normalized_author[idx_j] == normalized_author[idx_i]:
                continue
            matcher.set_seq1(content_j)
            if matcher.quick_ratio() < similarity_threshold:
                continue
            if text_similarity(content_i, content_j) >= similarity_threshold:
                is_suspect.at[idx_i] = True
                is_suspect.at[idx_j] = True

    return df.loc[~is_suspect].copy(), df.loc[is_suspect].copy()


# --- 2.2 Nhiễu biểu diễn ------------------------------------------------------

def normalize_teencode_and_abbreviations(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
) -> pd.DataFrame:
    """T2.17 + T2.18 (GỘP CHUNG) — Chuẩn hoá teencode (vd 'ko' -> 'không') VÀ
    mở rộng từ viết tắt (vd 'sp' -> 'sản phẩm') trong `content_col`.

    Gộp chung vì cả 2 mục dùng CHUNG 1 từ điển
    `dictionary/teencode_abbreviation.txt` (mỗi Teencode có thể có NHIỀU dòng
    ứng viên nghĩa, vd 'nc' -> 'nước'/'nói chung', kèm cột Context_Keywords +
    Flag để chọn đúng nghĩa theo ngữ cảnh — xem
    `dataio.dictionary_loader.load_teencode_dict`) — bản thân từ điển không
    phân biệt "teencode do gõ tắt/sai chính tả" (T2.17) với "từ viết tắt có
    chủ đích" (T2.18), cả 2 đều là 1 phép thay thế chuỗi->chuỗi NHƯ NHAU,
    khác biệt chỉ là NGUỒN GỐC của từ, không ảnh hưởng cách xử lý (đúng tinh
    thần gộp như T2.9+T2.10 ở nhóm 2.1).

    Dùng `transforms.utils_text.normalize_teencode_text` (khớp CẢ khoá nhiều
    từ vd 'san pham' lẫn khoá 1 từ, không phân biệt hoa/thường, theo ranh
    giới từ; khoá ĐA NGHĨA chỉ thay khi ngữ cảnh xung quanh đủ rõ, xem
    docstring hàm đó) áp cho từng dòng của `content_col`.

    Nếu `content_col` không tồn tại trong `df`: trả về bản sao nguyên vẹn.
    Dòng có `content_col` rỗng/NaN giữ nguyên (không có gì để chuẩn hoá).

    Hàm thuần (KHÔNG đọc file): từ điển được nạp qua tham số ẩn
    `load_teencode_dict()` (dataio.dictionary_loader) — cache sẵn, không đọc
    lại file mỗi dòng. Không sửa `df` gốc, giữ nguyên index gốc.
    """
    if content_col not in df.columns:
        return df.copy()

    teencode_dict = load_teencode_dict()
    result = df.copy()
    result[content_col] = result[content_col].apply(
        lambda v: v if pd.isna(v) else normalize_teencode_text(str(v), teencode_dict)
    )
    return result


def split_suspect_teencode_reviews(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """T2.17 + T2.18 — TÁCH dòng thành 2 nhóm (kept_df, suspect_df) — CÙNG
    tinh thần split_short_reviews/split_url_hotline_or_spam_reviews: từ nghi
    vấn được TÁCH RIÊNG ra `Suspect_Teencode_Abbreviation.xlsx` để con người
    rà soát thủ công, thay vì đoán bừa 1 dạng chuẩn có thể SAI. GỌI HÀM NÀY
    SAU `normalize_teencode_and_abbreviations` (trên chính output của nó) —
    xem `run_t218.py`.

    "Từ nghi vấn" gồm 2 nguồn:
      1. `load_suspect_teencode_terms()` — từ/cụm HOÀN TOÀN KHÔNG có trong
         `dictionary/teencode_abbreviation.txt` (chưa rõ nghĩa gì cả, xem
         `dictionary/suspect_teencode_terms.txt`).
      2. Khoá ĐA NGHĨA trong `dictionary/teencode_abbreviation.txt` (Flag =
         'ambiguous', nhiều dòng cùng Teencode, vd 'nc') mà
         `normalize_teencode_and_abbreviations` KHÔNG đủ ngữ cảnh để chọn 1
         ứng viên — occurrence đó vẫn còn nguyên dạng gốc trong `content_col`
         (xem `utils_text.normalize_teencode_text`), nên chỉ cần dò lại đúng
         các khoá đa nghĩa này là bắt được đúng những dòng CHƯA xử lý được.

    Một dòng thuộc `suspect_df` khi `content_col` chứa ÍT NHẤT 1 từ/cụm từ
    trong hợp của 2 nguồn trên (ranh giới từ, không phân biệt hoa/thường —
    xem `utils_text.contains_any_term`).

    Nếu `content_col` không tồn tại trong `df`, hoặc không có từ nghi vấn nào
    ở cả 2 nguồn: trả về (df.copy(), df rỗng cùng cột) — không có gì để tách.

    Hàm thuần: không sửa `df` gốc, không I/O trực tiếp (từ điển nạp qua các
    hàm `load_*` đã cache). Giữ nguyên index gốc của các dòng ở cả 2 DataFrame
    trả về.
    """
    ambiguous_keys = {key for key, candidates in load_teencode_dict().items() if len(candidates) > 1}
    suspect_terms = load_suspect_teencode_terms() | ambiguous_keys
    if content_col not in df.columns or not suspect_terms:
        return df.copy(), df.iloc[0:0].copy()

    is_suspect = df[content_col].apply(
        lambda v: False if pd.isna(v) else contains_any_term(str(v), suspect_terms)
    )
    return df.loc[~is_suspect].copy(), df.loc[is_suspect].copy()


def _correct_content(df: pd.DataFrame, content_col: str) -> tuple[pd.Series, pd.Series]:
    """(nội dung đã sửa, chi tiết sửa) theo từng dòng của `content_col`.
    Từ điển ứng viên sửa (`vocab`) dựng từ CHÍNH `df` — xem
    `utils_text.suggest_spelling_fix`. Dòng rỗng/NaN giữ nguyên, chi tiết ''."""
    errors, whitelist = load_spelling_errors_dict(), load_spelling_whitelist()
    vocab = build_syllable_vocab(df[content_col].dropna())
    results = df[content_col].apply(
        lambda v: (v, []) if pd.isna(v) else correct_spelling_text(v, errors, whitelist, vocab)
    )
    fixed = results.apply(lambda r: r[0])
    detail = results.apply(lambda r: "; ".join(f"{a} -> {b}" for a, b in r[1]))
    return fixed, detail


def fix_spelling_errors(df: pd.DataFrame, content_col: str = CONTENT_COL) -> pd.DataFrame:
    """T2.19 — Sửa lỗi chính tả trong `content_col` (trả về bản sao đã sửa).
    Muốn CON NGƯỜI KIỂM DUYỆT trước khi áp dụng thì dùng
    `split_spelling_error_reviews` (cách chạy thật, xem `run_t219.py`); hàm
    này là dạng "sửa luôn, không hỏi" của cùng logic.

    Phát hiện + sửa theo 3 lớp (xem `utils_text.correct_spelling_text`):
      1. `dictionary/spelling_errors.txt` — từ điển sửa tay các lỗi thường gặp.
      2. Bộ kiểm tra âm tiết tiếng Việt theo luật ghép vần (không cần từ điển
         ngoài): token không phải âm tiết hợp lệ, không thuộc
         `dictionary/spelling_whitelist.txt` (từ ngoại lai/thương hiệu) -> nghi
         sai chính tả.
      3. Cách sửa: giải mã Telex sót ('hangf' -> 'hàng') hoặc sửa 1 ký tự về
         âm tiết phổ biến trong chính dữ liệu ('cũnh' -> 'cũng'). Không đủ chắc
         thì GIỮ NGUYÊN.

    CỐ TÌNH KHÔNG xử lý: lỗi thiếu dấu ('nhieu' — T2.20), ký tự kéo dài
    ('nhaaa' — T2.21), teencode/viết tắt (T2.17+T2.18), từ sai nhưng vẫn là âm
    tiết hợp lệ ('thí' thay 'thì' — cần ngữ cảnh/mô hình ngôn ngữ).

    Nếu `content_col` không tồn tại: trả về bản sao nguyên vẹn. Hàm thuần,
    giữ nguyên index, không sửa `df` gốc.
    """
    result = df.copy()
    if content_col in result.columns:
        result[content_col] = _correct_content(result, content_col)[0]
    return result


def split_spelling_error_reviews(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """T2.19 — TÁCH dòng thành (kept_df, suspect_df) — cùng tinh thần
    `split_suspect_teencode_reviews`: dòng có lỗi chính tả được ghi nhận thì
    tách riêng ra `Suspect_Spelling_Errors.xlsx` để con người kiểm duyệt
    (xem `run_t219.py`). `suspect_df` có thêm 2 cột NGAY SAU `content_col`:
    `CORRECTED_CONTENT_COL` (bản đã sửa — chỗ để bạn chỉnh tay) và
    `CORRECTION_DETAIL_COL` (liệt kê từ sai -> từ đúng). `content_col` giữ
    NGUYÊN văn gốc để đối chiếu.

    Một dòng thuộc `suspect_df` khi `fix_spelling_errors` sửa được >= 1 từ.
    Hàm thuần, giữ nguyên index gốc ở cả 2 DataFrame trả về.
    """
    if content_col not in df.columns:
        return df.copy(), df.iloc[0:0].copy()

    fixed, detail = _correct_content(df, content_col)
    is_suspect = detail != ""
    suspect = df.loc[is_suspect].copy()
    pos = suspect.columns.get_loc(content_col) + 1
    suspect.insert(pos, CORRECTED_CONTENT_COL, fixed[is_suspect])
    suspect.insert(pos + 1, CORRECTION_DETAIL_COL, detail[is_suspect])
    return df.loc[~is_suspect].copy(), suspect


def restore_diacritics(df: pd.DataFrame) -> pd.DataFrame:
    """T2.20 — Xử lý review viết không dấu. TODO: implement (bài toán thêm dấu
    tiếng Việt — có thể cần model riêng, đánh giá độ ưu tiên trước khi làm)."""
    raise NotImplementedError


def normalize_repeated_characters(df: pd.DataFrame) -> pd.DataFrame:
    """T2.21 — Chuẩn hoá lặp ký tự kéo dài (vd 'đẹppppp' -> 'đẹp'). TODO: implement."""
    raise NotImplementedError


def handle_inline_emoji(df: pd.DataFrame) -> pd.DataFrame:
    """T2.22 — Xử lý emoji/emoticon xen giữa câu (chuẩn hoá vị trí/tách khỏi từ,
    KHÔNG xoá — xem thêm T2.32 ở nhóm 2.3). TODO: implement."""
    raise NotImplementedError


def remove_meaningless_special_chars(df: pd.DataFrame) -> pd.DataFrame:
    """T2.23 — Loại ký tự đặc biệt không mang ý nghĩa. TODO: implement."""
    raise NotImplementedError


def strip_extra_whitespace(df: pd.DataFrame) -> pd.DataFrame:
    """T2.24 — Khoảng trắng thừa/nhiều khoảng trắng liên tiếp.
    TODO: implement (dùng utils_text.strip_extra_whitespace)."""
    raise NotImplementedError


def normalize_casing(df: pd.DataFrame) -> pd.DataFrame:
    """T2.25 — Chuẩn hoá chữ hoa/chữ thường không nhất quán. TODO: implement,
    cân nhắc KHÔNG lowercase toàn bộ nếu viết hoa mang tín hiệu cảm xúc (liên hệ T2.30)."""
    raise NotImplementedError


def flag_code_switching(df: pd.DataFrame) -> pd.DataFrame:
    """T2.26 — Đánh dấu review có tiếng Anh xen tiếng Việt (code-switching).
    TODO: implement — quyết định giữ hay dịch, ghi rõ trong annotation guideline."""
    raise NotImplementedError


def flag_out_of_scope_language(df: pd.DataFrame) -> pd.DataFrame:
    """T2.27 — Đánh dấu/loại review bằng ngôn ngữ ngoài phạm vi nghiên cứu
    (xem config.settings.ALLOWED_LANGUAGES). TODO: implement (dùng language detection)."""
    raise NotImplementedError


# --- 2.3 Nội dung cần giữ lại — KHÔNG được xoá -------------------------------
# Các hàm dưới đây chỉ ĐÁNH DẤU (thêm cột flag), không xoá dữ liệu.

def flag_negation_words(df: pd.DataFrame) -> pd.DataFrame:
    """T2.28 — Đánh dấu review chứa từ phủ định ('không', 'chẳng', 'đâu có'...).
    TODO: implement."""
    raise NotImplementedError


def flag_intensifiers(df: pd.DataFrame) -> pd.DataFrame:
    """T2.29 — Đánh dấu từ nhấn mạnh ('rất', 'cực kỳ', 'siêu'...). TODO: implement."""
    raise NotImplementedError


def flag_exclamatory_sentences(df: pd.DataFrame) -> pd.DataFrame:
    """T2.30 — Đánh dấu câu cảm thán. TODO: implement."""
    raise NotImplementedError


def flag_meaningful_slang(df: pd.DataFrame) -> pd.DataFrame:
    """T2.31 — Đánh dấu tiếng lóng có ý nghĩa cảm xúc (cần từ điển riêng,
    KHÁC với teencode ở T2.17 vốn chỉ là biến thể chính tả). TODO: implement."""
    raise NotImplementedError


def flag_expressive_emoji(df: pd.DataFrame) -> pd.DataFrame:
    """T2.32 — Đánh dấu emoji có giá trị biểu đạt cảm xúc (không xoá ở bước làm sạch,
    dành cho bước gán nhãn/aspect sau này quyết định dùng hay không). TODO: implement."""
    raise NotImplementedError
