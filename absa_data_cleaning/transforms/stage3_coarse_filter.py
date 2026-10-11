"""
transforms/stage3_coarse_filter.py
====================================
GIAI ĐOẠN 3 — LỌC BỎ THÔ. Mục tiêu: giảm khối lượng dữ liệu sớm nhất có thể.

  8.  Bước 8a + 21a: xoá trùng lặp chính xác — trong từng file
      (`drop_exact_duplicates`, hiện so 'Nội dung tự do' + 'Tác giả', taxonomy
      T2.15) rồi giữa các file (`drop_exact_duplicates_across_files`).
      Kế hoạch: exact match trên `text_norm`. Cùng nội dung nhưng khác tác giả
      (vd "Hàng đẹp giao nhanh") có thể là review thật -> quyết định giữ 1 bản
      hay giữ có giới hạn, ghi rõ trong luận văn.
  9.  Bước 5: xoá review chỉ gồm emoji/ký tự đặc biệt
      (`drop_emoji_or_special_char_only_reviews`, T2.9 + T2.10).
  10. Bước 7: lọc URL quảng cáo/spam — kiểm duyệt thủ công
      (`split_url_hotline_or_spam_reviews`, T2.13 + T2.14 -> Suspect_URL_Spam.xlsx).
  11. Bước 19: lọc review không phải tiếng Việt (`split_non_vietnamese_reviews`).

Checkpoint sau giai đoạn: v3_filtered.
"""

import re
import unicodedata

import pandas as pd

from transforms.stage1_structure import AUTHOR_COL, CONTENT_COL, CRITERIA_COL, _criteria_is_blank_series
from transforms.stage2_normalize import TEXT_NORM_COL
from transforms.utils_text import contains_phone_number, contains_url, is_emoji_or_special_char_only

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
    `stage1_structure.drop_empty_rows`) — 1 dòng chỉ thực sự "không mang giá
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
    của T1.3 (`stage1_structure.drop_empty_rows`), PHẢI chạy TRƯỚC bước này.

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


def drop_exact_duplicates_across_files(
    dfs: dict[str, pd.DataFrame],
    content_col: str = TEXT_NORM_COL,
    author_col: str = AUTHOR_COL,
) -> dict[str, pd.DataFrame]:
    """Bước 21a — xoá trùng lặp chính xác GIỮA các file sản phẩm (input:
    {tên sản phẩm: DataFrame}), chạy sau `drop_exact_duplicates` trong từng
    file.

    Khoá so khớp = (`author_col`, `content_col`) với cùng quy tắc như
    `_dedup_key_series` (bỏ qua nội dung rỗng và tác giả rỗng/ẩn danh); mặc
    định so trên `text_norm` (không phân biệt hoa/thường), nếu df không có
    cột đó thì rơi về `CONTENT_COL`. GIỮ bản xuất hiện đầu tiên theo thứ tự
    của dict (rồi theo thứ tự dòng), xoá các bản sau ở file khác. Chỉ ghép
    cặp khi cùng tác giả để không xoá nhầm review THẬT của 2 khách khác nhau
    tình cờ viết giống nhau.

    Hàm thuần; giữ nguyên index gốc và thứ tự key của dict.
    """
    seen: set = set()
    out = {}
    for name, df in dfs.items():
        col = content_col if content_col in df.columns else CONTENT_COL
        if col not in df.columns:
            out[name] = df.copy()
            continue
        key, has_key = _dedup_key_series(df, col, author_col)
        is_dup = has_key & (key.duplicated(keep="first") | key.isin(seen))
        seen.update(key[has_key])
        out[name] = df.loc[~is_dup].copy()
    return out


# Từ tiếng Việt KHÔNG DẤU đặc trưng (đã loại các từ trùng chính tả với tiếng
# Anh như "do", "an", "to", "me", "ban", "can"). Chỉ cần 1 từ khớp là coi câu
# có khả năng là tiếng Việt viết không dấu.
_VI_UNACCENTED = frozenset(
    "hang dep tot khong ko k chua rat nhanh giao dung shop san pham mua cho "
    "minh toi va nhung duoc cung voi nay kia dau gia re mau vai chat luong "
    "nhan xau lam cam on hai long that ma thi la cua em anh chi roi qua "
    "sach moi cu hop hoi vua nho lon ngon mem nong lanh chuan dong goi "
    "tang kich thuoc size ve tu nhieu it hon sau truoc dang cac con".split()
)
# Từ tiếng Anh phổ biến (đã loại các từ trùng với tiếng Việt không dấu).
_EN_WORDS = frozenset(
    "the a is are was were it this that good great nice very quality product "
    "fast delivery shipping love like bad best recommend recommended thanks "
    "thank you thx works work worth price perfect excellent amazing happy "
    "seller item received arrived package well and for with of in on my so "
    "not but too really just as at be have has had i we they he she its "
    "cheap fine okay comfortable fit fits small big beautiful".split()
)
_WORD_RE = re.compile(r"[^\W\d_]+")
# Chữ cái đặc trưng của tiếng Việt: nếu có thì chắc là tiếng Việt.
_VI_MARK_RE = re.compile(
    "[ăâđêôơưàáạảãằắặẳẵầấậẩẫèéẹẻẽềếệểễìíịỉĩòóọỏõồốộổỗờớợởỡùúụủũừứựửữỳýỵỷỹ]",
    re.IGNORECASE,
)


def _classify_language(text: str, min_confidence: float) -> str:
    """'vi' | 'drop' | 'suspect' cho 1 chuỗi (heuristic, không cần thư viện)."""
    if _VI_MARK_RE.search(text):
        return "vi"
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "vi"  # không có chữ: việc của bước emoji/ký tự đặc biệt
    if not all(c.isascii() or unicodedata.name(c, "").startswith("LATIN") for c in letters):
        return "drop"  # chữ CJK / Thái / Cyrillic... — chắc chắn không phải tiếng Việt
    tokens = [t.lower() for t in _WORD_RE.findall(text)]
    if any(t in _VI_UNACCENTED for t in tokens):
        return "vi"
    en = sum(t in _EN_WORDS for t in tokens)
    if en == 0:
        return "vi"  # "ok", "oke", tên riêng...: không đủ bằng chứng nước ngoài
    # ponytail: ngưỡng trên tỉ lệ từ khớp danh sách; thay bằng fastText/lingua nếu cần chính xác hơn
    return "drop" if len(tokens) >= 3 and en / len(tokens) >= min_confidence else "suspect"


def split_non_vietnamese_reviews(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
    min_confidence: float = 0.95,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bước 19 — TÁCH (kept_df, suspect_df) review không phải tiếng Việt
    (xem `config.settings.ALLOWED_LANGUAGES`).

    Phân loại từng `content_col` bằng `_classify_language` (heuristic):
      - có dấu/chữ đặc trưng tiếng Việt, hoặc có từ tiếng Việt không dấu
        ('hang', 'dep', 'khong'...), hoặc không có bằng chứng nước ngoài
        -> giữ (kept_df);
      - chữ viết khác Latin (CJK, Thái...), câu >= 3 từ mà >= `min_confidence`
        số từ là từ tiếng Anh phổ biến, hoặc có lẫn từ Anh nhưng chưa chắc
        (vd 'good') -> TẤT CẢ vào suspect_df để kiểm duyệt thủ công.
        KHÔNG xoá tự động dòng nào; chỉ xoá sau khi người kiểm duyệt xác nhận.
    Nội dung rỗng/NaN luôn được giữ. Nếu `content_col` không tồn tại: trả về
    (df.copy(), df rỗng). Hàm thuần, giữ index gốc.
    """
    if content_col not in df.columns:
        return df.copy(), df.iloc[0:0].copy()
    label = df[content_col].map(
        lambda v: "vi" if pd.isna(v) or str(v).strip() == "" else _classify_language(str(v), min_confidence)
    )
    return df.loc[label == "vi"].copy(), df.loc[label != "vi"].copy()
