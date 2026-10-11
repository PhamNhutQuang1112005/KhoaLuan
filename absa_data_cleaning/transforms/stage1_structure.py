"""
transforms/stage1_structure.py
================================
GIAI ĐOẠN 1 — SỬA CẤU TRÚC (tự động). Thứ tự bắt buộc:

  Bước 1  `fix_field_misalignment` — xử lý lệch cột. PHẢI làm đầu tiên: xoá
          dòng thiếu dữ liệu trước sẽ xoá nhầm dòng bị lệch (review nằm ở cột
          tác giả, cột review trống). (taxonomy T1.1)
  Bước 2  `drop_empty_rows`        — xoá dòng trống / thiếu cột bắt buộc, chỉ
          làm SAU khi đã kéo dữ liệu về đúng cột. (T1.2 + T1.3; alias cũ
          `validate_required_columns`)
  Bước 3  `fix_data_types`         — ép kiểu cột thời gian (hỗ trợ khử trùng
          lặp về sau: cùng tác giả + cùng thời điểm + cùng nội dung). (T1.5)
  Bước 4  `split_merged_fields`    — tách 'Tiêu chí đánh giá' thành các cột
          riêng. (T1.6)

Checkpoint sau giai đoạn: v1_structured.

Hằng tên cột + helper `_is_blank_value` / `_criteria_is_blank_series` ở đây
được các giai đoạn sau import dùng chung.

Mỗi hàm là 1 HÀM THUẦN: nhận pd.DataFrame, trả pd.DataFrame mới (không sửa
inplace, không I/O).
"""

import re

import pandas as pd

AUTHOR_COL = "Tác giả"
CONTENT_COL = "Nội dung tự do"
ANON_LABEL = "ẩn danh"
TIME_COL = "Thời gian"
SCRAPED_AT_COL = "Thời điểm cào"
CRITERIA_COL = "Tiêu chí đánh giá"
MOVED_CRITERIA_COL = "Tiêu chí chuyển sang tự do"  # đánh dấu T1.6
_TIME_FORMAT = "%Y-%m-%d %H:%M"  # giờ địa phương, không tz — vd '2025-12-17 01:38'
_SCRAPED_AT_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"  # ISO 8601 UTC — vd '2026-08-22T13:40:30.954Z'
_VIETNAMESE_DIACRITIC_RE = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]",
    re.IGNORECASE,
)


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
    với cách `stage1_structure.drop_empty_rows` xử lý cột bắt buộc bị thiếu
    hẳn.
    """
    if criteria_col not in df.columns:
        return pd.Series(True, index=df.index)
    return df[criteria_col].apply(_is_blank_value)


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
    Loại bỏ 1 dòng nếu rơi vào 1 trong 2 trường hợp:
      1. Dòng trống / bản ghi rỗng hoàn toàn: MỌI cột đều NaN/None hoặc chỉ
         chứa khoảng trắng. Hiện tại (10 file trong data/raw/) CHƯA phát sinh
         trường hợp này, nhưng vẫn giữ lại làm lưới an toàn phòng dữ liệu mới.
      2. Trống ĐỒNG THỜI cả 2 cột bắt buộc `criteria_col` ('Tiêu chí đánh giá')
         và `content_col` ('Nội dung tự do'): dòng không còn giá trị nào cho
         ABSA (không có tiêu chí, cũng không có nội dung tự do) -> loại bỏ.
         CÒN TỒN TẠI GIÁ TRỊ Ở 1 TRONG 2 (hoặc cả 2) THÌ GIỮ LẠI DÒNG — khác
         với thiết kế trước đây (chỉ `content_col` là bắt buộc, trống là xoá
         bất kể `criteria_col`).
         Nếu 1 trong 2 cột này KHÔNG TỒN TẠI trong `df` (thiếu hẳn cột, khác
         với thiếu giá trị từng dòng): coi cột đó là "trống" ở MỌI dòng, vì
         không có giá trị nào cho trường đó trong toàn bộ dữ liệu.

    Với dòng được GIỮ LẠI: giá trị rỗng dạng chuỗi rỗng / chỉ khoảng trắng ở
    CẢ 2 cột bắt buộc (nếu có) được CHUẨN HOÁ về `pd.NA` nhất quán (dữ liệu
    thô có thể lẫn lộn None / '' / '   ' tuỳ dòng; giá trị None/NaN đã có sẵn
    thì giữ nguyên, không cần rewrite).

    Hàm thuần: không sửa `df` gốc, không I/O. Giữ nguyên index gốc của các
    dòng còn lại (để truy vết đúng số dòng đã xoá qua core.diff_report).
    """

    def _is_blank(series: pd.Series) -> pd.Series:
        s = series.astype("string")
        return s.isna() | (s.str.strip() == "")

    out = df.copy()

    for col in (criteria_col, content_col):
        if col in out.columns:
            values = out[col]
            whitespace_only = values.notna() & values.astype("string").str.strip().eq("")
            out.loc[whitespace_only, col] = pd.NA

    all_columns_blank = pd.Series(True, index=out.index)
    for col in out.columns:
        all_columns_blank &= _is_blank(out[col])

    if criteria_col in out.columns:
        criteria_blank = _is_blank(out[criteria_col])
    else:
        criteria_blank = pd.Series(True, index=out.index)

    if content_col in out.columns:
        content_blank = _is_blank(out[content_col])
    else:
        content_blank = pd.Series(True, index=out.index)

    both_required_blank = criteria_blank & content_blank

    return out.loc[~(all_columns_blank | both_required_blank)].copy()


def validate_required_columns(
    df: pd.DataFrame,
    content_col: str = CONTENT_COL,
    criteria_col: str = CRITERIA_COL,
) -> pd.DataFrame:
    """T1.2 — Đã GỘP CHUNG với T1.3 (xem `drop_empty_rows` ở trên): 2 cột bắt
    buộc ('Tiêu chí đánh giá' và 'Nội dung tự do') — chỉ xoá dòng khi CẢ 2
    cùng trống, còn tồn tại giá trị ở 1 trong 2 (hoặc cả 2) thì giữ lại — và
    dòng rỗng hoàn toàn được xử lý trong cùng 1 hàm (xem docstring
    `drop_empty_rows` để biết chi tiết).

    Giữ hàm này lại (delegate sang `drop_empty_rows`) để code/test cũ gọi
    riêng theo mã T1.2 vẫn chạy đúng.
    """
    return drop_empty_rows(df, content_col=content_col, criteria_col=criteria_col)


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
    content_col: str = CONTENT_COL,
    moved_col: str = MOVED_CRITERIA_COL,
    min_rows: int = 3,
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

    LỌC TIÊU CHÍ HIẾM: chỉ tên_tiêu_chí xuất hiện ở >= `min_rows` dòng (mặc
    định 3, tức "trên 2 dòng") mới được tách thành cột. Tên chỉ có 1-2 dòng thì
    vốn không phải tiêu chí đánh giá mà là review tự do bị đặt nhầm sang cột
    tiêu chí -> KHÔNG tạo cột; dòng gốc 'tên: giá trị' của chúng được nối vào
    CUỐI `content_col` (cách nhau '\n', tạo cột nếu chưa có) và tên được ghi
    vào cột đánh dấu `moved_col` (nhiều tên nối bằng '; ') để rà soát lại.

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

    row_count = {k: sum(k in rv for rv in parsed_by_row.values()) for k in ordered_keys}
    kept_keys = [k for k in ordered_keys if row_count[k] >= min_rows]

    for key in kept_keys:
        col_name = f"{key} (tiêu chí)" if key in out.columns else key
        out[col_name] = pd.Series(
            {idx: row_values.get(key) for idx, row_values in parsed_by_row.items()},
            index=out.index,
            dtype="string",
        )

    rare_keys = {k for k in ordered_keys if row_count[k] < min_rows}
    if rare_keys:
        content = out[content_col].astype("string") if content_col in out.columns else pd.Series(pd.NA, index=out.index, dtype="string")
        moved = pd.Series(pd.NA, index=out.index, dtype="string")
        for idx, row_values in parsed_by_row.items():
            rare = [k for k in row_values if k in rare_keys]
            if not rare:
                continue
            text = "\n".join(f"{k}: {row_values[k]}" for k in rare)
            old = content[idx]
            content[idx] = text if pd.isna(old) or not str(old).strip() else f"{str(old).strip()}\n{text}"
            moved[idx] = "; ".join(rare)
        out[content_col] = content
        out[moved_col] = moved

    return out
