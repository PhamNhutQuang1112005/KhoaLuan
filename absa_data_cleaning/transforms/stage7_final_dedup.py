"""
transforms/stage7_final_dedup.py
==================================
GIAI ĐOẠN 7 — KHỬ TRÙNG LẶP LẦN CUỐI & KIỂM TRA.

  22. Bước 8b: gần trùng lặp trong từng file — kiểm duyệt thủ công
      (`split_near_duplicate_reviews`, taxonomy T2.16 ->
      Suspect_Duplicate_Content.xlsx). PHẢI sau chuẩn hoá ('sp ok lắm' và
      'sản phẩm ok lắm' mới được nhận ra là giống nhau).
  23. Bước 21b: gần trùng lặp giữa các file
      (`split_cross_file_near_duplicates`). Tránh data leakage train/test
      trong thí nghiệm cross-domain — PHẢI xong trước khi chia train/test và
      trước khi lấy mẫu Gold Dataset.
  24. Kiểm tra cuối (`final_check`): chạy lại bước 16, 17; không còn dòng
      trống; so số dòng với log.

Checkpoint sau giai đoạn: v7_final (ghi vào data/processed/).
"""

from difflib import SequenceMatcher

import pandas as pd

from config.settings import NEAR_DUPLICATE_SIMILARITY_THRESHOLD
from transforms.stage1_structure import AUTHOR_COL, CONTENT_COL, CRITERIA_COL, _criteria_is_blank_series
from transforms.stage2_normalize import TEXT_NORM_COL, add_text_norm_column, strip_extra_whitespace
from transforms.utils_text import text_similarity

PRODUCT_COL = "Nguồn file"  # không dùng "Sản phẩm": trùng cột tiêu chí do T1.6 tách
SOURCE_ROW_COL = "Dòng Excel đầu vào"


def _similar_rows(texts: dict, groups: dict, similarity_threshold: float) -> set:
    """Khoá của MỌI dòng nằm trong ít nhất 1 cặp (i, j) khác `groups` có
    `text_similarity >= similarity_threshold`. `texts`/`groups`: {khoá -> chuỗi
    đã strip+lower / nhãn nhóm}. Lõi dùng chung của 8b (nhóm = tác giả) và 21b
    (nhóm = sản phẩm). Chi tiết hiệu năng (cửa sổ độ dài + quick_ratio, tương
    đương so mọi cặp): xem docstring `split_near_duplicate_reviews`."""
    by_length = sorted(texts, key=lambda k: len(texts[k]))
    n = len(by_length)
    found: set = set()
    matcher = SequenceMatcher()
    for i in range(n):
        key_i = by_length[i]
        content_i = texts[key_i]
        len_i = len(content_i)
        # Chan tren do dai chuoi thu 2 de con co co hoi dat similarity_threshold
        # (suy tu ratio <= 2*len_i/(len_i+len_j) >= similarity_threshold).
        max_len_j = float("inf") if similarity_threshold <= 0 else len_i * (2 / similarity_threshold - 1)
        matcher.set_seq2(content_i)
        for j in range(i + 1, n):
            key_j = by_length[j]
            content_j = texts[key_j]
            if len(content_j) > max_len_j:
                break  # by_length da sap theo do dai tang dan -> cac j sau cung vuot nguong
            if groups[key_j] == groups[key_i]:
                continue
            matcher.set_seq1(content_j)
            if matcher.quick_ratio() < similarity_threshold:
                continue
            if text_similarity(content_i, content_j) >= similarity_threshold:
                found.update((key_i, key_j))
    return found

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

    is_suspect = df.index.isin(list(_similar_rows(normalized_content, normalized_author, similarity_threshold)))
    return df.loc[~is_suspect].copy(), df.loc[is_suspect].copy()


def split_cross_file_near_duplicates(
    dfs: dict[str, pd.DataFrame],
    similarity_threshold: float = NEAR_DUPLICATE_SIMILARITY_THRESHOLD,
    content_col: str = TEXT_NORM_COL,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Bước 21b — tìm cặp review gần trùng GIỮA các file sản phẩm (input:
    {sản phẩm: DataFrame}), trả về ({sản phẩm: kept_df}, suspect_df) để kiểm
    duyệt thủ công; KHÔNG tự xoá. Chống data leakage train/test cross-domain.

    Cùng cơ chế/ngưỡng với `split_near_duplicate_reviews` (so trên
    `content_col`, mặc định `text_norm`, rơi về `CONTENT_COL`), nhưng nhóm là
    SẢN PHẨM chứ không phải tác giả: chỉ so cặp thuộc 2 file khác nhau, KHÔNG
    xét tác giả (leakage xảy ra dù cùng hay khác tác giả; trùng chính xác cùng
    tác giả đã bị 21a xoá). CẢ 2 dòng của mỗi cặp vào `suspect_df`, kèm cột
    'Nguồn file', 'Dòng Excel đầu vào' (= số dòng Excel) để người duyệt giữ lại 1 bản. Dòng nội dung rỗng/NaN không tham gia. Hàm thuần.
    """
    texts: dict = {}
    groups: dict = {}
    for name, df in dfs.items():
        col = content_col if content_col in df.columns else CONTENT_COL
        if col not in df.columns:
            continue
        for idx, value in df[col].items():
            if pd.isna(value) or str(value).strip() == "":
                continue
            texts[(name, idx)] = str(value).strip().lower()
            groups[(name, idx)] = name

    flagged = _similar_rows(texts, groups, similarity_threshold)
    kept, suspects = {}, []
    for name, df in dfs.items():
        mask = df.index.map(lambda idx: (name, idx) in flagged).to_numpy(dtype=bool)
        kept[name] = df.loc[~mask].copy()
        s = df.loc[mask].copy()
        s.insert(0, SOURCE_ROW_COL, s.index + 2)
        s.insert(0, PRODUCT_COL, name)
        suspects.append(s)
    suspect = pd.concat(suspects, ignore_index=True) if suspects else pd.DataFrame()
    return kept, suspect


def final_check(df: pd.DataFrame, expected_rows: int | None = None) -> pd.DataFrame:
    """Kiểm tra cuối — chạy lại `strip_extra_whitespace` (bước 16) +
    `add_text_norm_column` (bước 17); ValueError nếu còn dòng trống (cả 'Nội
    dung tự do' lẫn 'Tiêu chí đánh giá' đều rỗng — nhất quán T1.2+T1.3) hoặc,
    khi có `expected_rows`, số dòng không khớp log. Không xoá dòng nào."""
    out = add_text_norm_column(strip_extra_whitespace(df))
    content_blank = out[CONTENT_COL].isna() if CONTENT_COL in out.columns else pd.Series(True, index=out.index)
    n_empty = int((content_blank & _criteria_is_blank_series(out, CRITERIA_COL)).sum())
    if n_empty:
        raise ValueError(f"final_check: còn {n_empty} dòng trống (không nội dung, không tiêu chí)")
    if expected_rows is not None and len(out) != expected_rows:
        raise ValueError(f"final_check: {len(out)} dòng, log ghi {expected_rows}")
    return out
