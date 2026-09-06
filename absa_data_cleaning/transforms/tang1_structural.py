"""
transforms/tang1_structural.py
================================
TẦNG 1 — LỖI CẤU TRÚC DỮ LIỆU (8 mục theo taxonomy).

Mỗi hàm dưới đây là 1 HÀM THUẦN: nhận vào pd.DataFrame, trả về pd.DataFrame mới
(không sửa inplace, không side-effect I/O). Khi triển khai thật, gắn decorator
`@register_step(...)` từ core.registry lên từng hàm để hệ thống nhận diện.

Danh sách 8 mục (mã taxonomy T1.1 .. T1.8):
  T1.1  Sai / lệch cột dữ liệu (Field Misalignment)          — Nghiêm trọng
  T1.2  Thiếu cột bắt buộc ('Tiêu chí đánh giá' và              ┐ gộp chung,
        'Nội dung tự do') — Thấp                                 ┘ xem drop_empty_rows
  T1.3  Dòng trống / bản ghi rỗng hoàn toàn        — Nghiêm trọng
  T1.4  Giá trị NULL / NaN / None                              — Trung bình
  T1.5  Sai kiểu dữ liệu (Data Type)                           — Trung bình
  T1.6  Dữ liệu bị dồn nhiều trường vào một ô                   — Nghiêm trọng
  T1.7  Ký tự xuống dòng / tab làm phá cấu trúc trường          — Trung bình
  T1.8  Encoding lỗi / ký tự bị lỗi (mojibake)                  — Thấp
"""

import re

import pandas as pd

AUTHOR_COL = "Tác giả"
CONTENT_COL = "Nội dung tự do"
ANON_LABEL = "ẩn danh"
TIME_COL = "Thời gian"
SCRAPED_AT_COL = "Thời điểm cào"
CRITERIA_COL = "Tiêu chí đánh giá"
_TIME_FORMAT = "%Y-%m-%d %H:%M"  # giờ địa phương, không tz — vd '2025-12-17 01:38'
_SCRAPED_AT_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"  # ISO 8601 UTC — vd '2026-08-22T13:40:30.954Z'

_VIETNAMESE_DIACRITIC_RE = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]",
    re.IGNORECASE,
)


def fix_field_misalignment(
    df: pd.DataFrame,
    author_col: str = AUTHOR_COL,
    content_col: str = CONTENT_COL,
    anon_label: str = ANON_LABEL,
    min_words: int = 2,
) -> pd.DataFrame:
    """T1.1 — Phát hiện & sửa trường hợp nội dung review lọt sang cột 'Tác giả'
    (khi người dùng để trống tên hiển thị).

    Ví dụ thực tế đã ghi nhận: phone #1911 — 'Tác giả' chứa nội dung review
    thật, 'Nội dung tự do' rỗng.

    Heuristic (kiểm chứng trên toàn bộ 10 file hiện có trong data/raw/):
    username thật trên các sàn TMĐT này luôn là 1 token thuần ASCII/số/gạch
    dưới (vd 'ha_lucsi', 'a*****9'), không bao giờ chứa dấu tiếng Việt.
    'Tác giả' được coi là chứa nội dung review (bị lệch cột) khi:
      - có >= `min_words` từ (giống câu review, không phải username), HOẶC
      - chỉ 1 token nhưng có chứa dấu tiếng Việt (vd 'đẹp' — không có username
        thật nào trong dữ liệu chứa dấu).
    Trường hợp 1 token, không dấu, không đạt `min_words` (vd 'ok') được coi là
    mơ hồ và CỐ TÌNH bỏ qua để tránh sửa nhầm username thật.

    Khi khớp:
      - Nếu 'Nội dung tự do' đang rỗng: chuyển hẳn nội dung 'Tác giả' sang đó.
      - Nếu 'Nội dung tự do' đã có sẵn nội dung (cả 2 cột cùng bị lệch, vd
        buds #766, watch #789): nối 'Tác giả' vào TRƯỚC nội dung sẵn có, cách
        nhau bằng '\\n'.
      Sau đó gán lại 'Tác giả' = `anon_label`.

    Hàm thuần: không sửa `df` gốc, không I/O.
    """
    if author_col not in df.columns or content_col not in df.columns:
        return df.copy()

    out = df.copy()
    author = out[author_col].astype("string")
    content = out[content_col].astype("string")

    author_stripped = author.str.strip()
    word_count = author_stripped.str.split().str.len()
    has_diacritics = author_stripped.str.contains(_VIETNAMESE_DIACRITIC_RE, na=False)
    author_is_review = author.notna() & (word_count.ge(min_words) | has_diacritics)

    content_empty = content.isna() | (content.str.strip() == "")
    misaligned_empty = author_is_review & content_empty
    misaligned_filled = author_is_review & ~content_empty

    out.loc[misaligned_empty, content_col] = author_stripped[misaligned_empty]
    out.loc[misaligned_filled, content_col] = (
        author_stripped[misaligned_filled] + "\n" + content[misaligned_filled].str.strip()
    )
    out.loc[author_is_review, author_col] = anon_label
    return out


def drop_empty_rows(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
    criteria_col: str = CRITERIA_COL,
) -> pd.DataFrame:
    """T1.3 (GỘP CHUNG với T1.2 — xem `validate_required_columns` bên dưới) —
    Có 2 CỘT BẮT BUỘC: `criteria_col` ('Tiêu chí đánh giá') và `content_col`
    ('Nội dung tự do'). Mỗi cột "bắt buộc" theo 1 CÁCH KHÁC NHAU vì bản chất
    dữ liệu khác nhau:
      - `content_col` rỗng: dòng không mang thông tin gì cho ABSA -> LOẠI BỎ
        HẲN dòng (khác phạm vi với T1.4 — không giữ lại rồi xử lý NULL sau).
      - `criteria_col` rỗng (NaN, chuỗi rỗng, hoặc chỉ chứa khoảng trắng):
        review tự do không gắn tiêu chí vẫn hợp lệ và vẫn hữu ích cho ABSA
        -> KHÔNG xoá dòng, chỉ CHUẨN HOÁ giá trị rỗng về `pd.NA` (dữ liệu thô
        có thể lẫn lộn None / '' / '   ' tuỳ dòng; giá trị None/NaN đã có sẵn
        thì giữ nguyên, không cần rewrite).

    Ngoài ra vẫn loại bỏ dòng trống / bản ghi rỗng hoàn toàn: MỌI cột đều
    NaN/None hoặc chỉ chứa khoảng trắng. Gộp chung việc quét dòng rỗng hoàn
    toàn và dòng thiếu `content_col` trong cùng 1 lượt vì trên dữ liệu thực
    tế, dòng rỗng hoàn toàn dĩ nhiên cũng rỗng luôn cột nội dung.

    Hàm thuần: không sửa `df` gốc, không I/O. Giữ nguyên index gốc của các
    dòng còn lại (để truy vết đúng số dòng đã xoá qua core.diff_report).
    """

    def _is_blank(series: pd.Series) -> pd.Series:
        s = series.astype("string")
        return s.isna() | (s.str.strip() == "")

    out = df.copy()

    if criteria_col in out.columns:
        criteria = out[criteria_col]
        whitespace_only = criteria.notna() & criteria.astype("string").str.strip().eq("")
        out.loc[whitespace_only, criteria_col] = pd.NA

    all_columns_blank = pd.Series(True, index=out.index)
    for col in out.columns:
        all_columns_blank &= _is_blank(out[col])

    if content_col in out.columns:
        content_blank = _is_blank(out[content_col])
    else:
        content_blank = pd.Series(False, index=out.index)

    return out.loc[~(all_columns_blank | content_blank)].copy()


def validate_required_columns(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
    criteria_col: str = CRITERIA_COL,
) -> pd.DataFrame:
    """T1.2 — Đã GỘP CHUNG với T1.3 (xem `drop_empty_rows` ở trên): 2 cột bắt
    buộc ('Tiêu chí đánh giá' và 'Nội dung tự do') và dòng rỗng hoàn toàn được
    xử lý trong cùng 1 hàm (xem docstring `drop_empty_rows` để biết cách xử lý
    khác nhau giữa 2 cột: xoá dòng vs chuẩn hoá giá trị rỗng).

    Giữ hàm này lại (delegate sang `drop_empty_rows`) để code/test cũ gọi
    riêng theo mã T1.2 vẫn chạy đúng.
    """
    return drop_empty_rows(df, content_col=content_col, criteria_col=criteria_col)


def handle_null_values(df: pd.DataFrame) -> pd.DataFrame:
    """T1.4 — Chuẩn hoá giá trị NULL/NaN/None (quyết định: giữ None hay điền
    giá trị mặc định tuỳ cột — vd 'Tiêu chí đánh giá' có thể hợp lệ khi rỗng).

    TODO: implement, cần quyết định chính sách theo từng cột.
    """
    raise NotImplementedError


def fix_data_types(
    df: pd.DataFrame,
    time_col: str = TIME_COL,
    scraped_at_col: str = SCRAPED_AT_COL,
) -> pd.DataFrame:
    """T1.5 — Ép kiểu dữ liệu đúng cho 2 cột thời gian hiện đang lưu dạng chuỗi
    (object) thay vì datetime chuẩn. Hai cột dùng 2 định dạng KHÁC NHAU nên
    phải parse riêng từng cột, không thể dùng chung 1 lệnh pd.to_datetime:
      - `time_col` ('Thời gian'): giờ địa phương, KHÔNG có tz, định dạng
        'YYYY-MM-DD HH:MM' (vd '2025-12-17 01:38') -> ép sang datetime64
        (tz-naive).
      - `scraped_at_col` ('Thời điểm cào'): ISO 8601 UTC, hậu tố 'Z', có mili
        giây (vd '2026-08-22T13:40:30.954Z') -> ép sang datetime64[ns, UTC]
        (tz-aware).

    Parse lỗi (giá trị không khớp định dạng khai báo) sẽ RAISE ngay thay vì
    âm thầm trả về NaT, để phát hiện dữ liệu bất thường sớm thay vì để lọt
    xuống các bước sau.

    Hàm thuần: không sửa `df` gốc, không I/O.
    """
    out = df.copy()

    if time_col in out.columns:
        out[time_col] = pd.to_datetime(out[time_col], format=_TIME_FORMAT)

    if scraped_at_col in out.columns:
        out[scraped_at_col] = pd.to_datetime(
            out[scraped_at_col], format=_SCRAPED_AT_FORMAT, utc=True
        )

    return out


def split_merged_fields(
    df: pd.DataFrame,
    source_col: str = CRITERIA_COL,
) -> pd.DataFrame:
    """T1.6 — Tách cột `source_col` (dạng nhiều dòng 'Tên tiêu chí: giá trị',
    vd 'Hiệu suất: mượt\\nThiết kế: oki') thành MỖI TIÊU CHÍ 1 CỘT RIÊNG. Dòng
    nào không có tiêu chí đó (hoặc `source_col` rỗng hoàn toàn) thì cột tương
    ứng để trống (NaN) đúng như dữ liệu gốc — KHÔNG tự điền giá trị giả.

    Cách tách: mỗi dòng trong `source_col` được tách theo '\\n', mỗi dòng con
    tách tiếp thành (tên_tiêu_chí, giá_trị) tại dấu ':' ĐẦU TIÊN (nhờ vậy giá
    trị có chứa ':' ở sau — vd URL — không bị cắt nhầm). Tên cột mới = đúng
    nguyên văn tên_tiêu_chí đã strip khoảng trắng.

    CỐ TÌNH KHÔNG chuẩn hoá/gộp các tên gần giống nhau (vd 'Chất lượng' và
    'Chất lượng sản phẩm' vẫn là 2 cột khác nhau, và một số dòng lỗi định dạng
    có thể tạo ra "tiêu chí" là cả 1 câu review) — việc gộp nhóm theo khía
    cạnh (aspect) thực sự là bước xử lý ngữ nghĩa riêng, THỰC HIỆN SAU T1.6.

    2 trường hợp biên xử lý an toàn:
      - Nếu 1 dòng dữ liệu có CÙNG 1 tên_tiêu_chí lặp lại nhiều lần (hiếm, đã
        ghi nhận vài trường hợp thật trong data/raw/): nối các giá trị lại
        bằng '; ' thay vì âm thầm giữ 1 giá trị và bỏ qua giá trị còn lại.
      - Nếu tên_tiêu_chí trùng với 1 cột đã có sẵn trong `df`: thêm hậu tố
        ' (tiêu chí)' vào tên cột mới để tránh ghi đè cột gốc.

    Hàm thuần: không sửa `df` gốc, không I/O. Cột `source_col` gốc được GIỮ
    NGUYÊN (không xoá) — các cột tiêu chí mới được nối vào SAU các cột hiện có.
    """
    out = df.copy()

    if source_col not in out.columns:
        return out

    parsed_by_row: dict = {}
    ordered_keys: list[str] = []
    seen_keys: set[str] = set()

    for idx, raw_value in out[source_col].items():
        if pd.isna(raw_value):
            continue
        row_values: dict[str, str] = {}
        for line in str(raw_value).split("\n"):
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue
            row_values[key] = f"{row_values[key]}; {value}" if key in row_values else value
            if key not in seen_keys:
                seen_keys.add(key)
                ordered_keys.append(key)
        parsed_by_row[idx] = row_values

    for key in ordered_keys:
        col_name = f"{key} (tiêu chí)" if key in out.columns else key
        out[col_name] = pd.Series(
            {idx: row_values.get(key) for idx, row_values in parsed_by_row.items()},
            index=out.index,
            dtype="string",
        )

    return out


def normalize_line_breaks(df: pd.DataFrame) -> pd.DataFrame:
    """T1.7 — Xử lý ký tự xuống dòng/tab phá cấu trúc trường (khác với T1.6:
    ở đây là newline làm hỏng định dạng ô Excel, không nhất thiết mang nghĩa
    "nhiều trường trong 1 ô").

    TODO: implement.
    """
    raise NotImplementedError


def fix_encoding_issues(df: pd.DataFrame) -> pd.DataFrame:
    """T1.8 — Phát hiện & sửa lỗi encoding (mojibake).

    TODO: implement.
    """
    raise NotImplementedError
