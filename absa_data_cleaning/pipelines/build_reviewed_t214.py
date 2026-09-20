"""
pipelines/build_reviewed_t214.py
===================================
Tính lại TỪ ĐẦU (từ data/raw/) toàn bộ chuỗi T1.1 -> T2.14 cho 1 sản phẩm,
NGAY TRONG BỘ NHỚ — không đọc bất kỳ {name}_t2.12.xlsx / {name}_t2.14.xlsx nào
trên đĩa.

TẠI SAO CẦN FILE NÀY: `run_t216.py` (T2.15+T2.16) ban đầu đọc thẳng
data/interim/{name}_t2.14.xlsx trên đĩa, ngầm giả định file đó ĐÃ phản ánh
đúng kết quả sau khi con người rà soát xong CẢ Short_reviews_Checked.xlsx LẪN
Suspect_URL_Spam_Checked.xlsx (tức đã chạy đủ run_t212.py ->
Merge_Short_Reviews_Checked.py -> run_t214.py -> Merge_Suspect_URL_Spam_Checked.py
theo ĐÚNG thứ tự). Nếu 1 trong 2 bước rà soát đó CHƯA xong (vd
Suspect_URL_Spam_Checked.xlsx chưa được tạo) mà vẫn chạy run_t216.py, kết quả
T2.15/T2.16 sẽ dựa trên dữ liệu THIẾU (chưa gồm các dòng nghi vấn URL/spam mà
con người thật ra muốn giữ lại) — dễ chạy nhầm thứ tự mà không nhận ra, vì
{name}_t2.14.xlsx trên đĩa vẫn "có vẻ" hợp lệ (không báo lỗi gì).

File này giải quyết đúng vấn đề đó: `build_reviewed_t214_dataframe(name)` tính
lại toàn bộ chuỗi ngay trong bộ nhớ mỗi lần gọi (giống cách
Merge_Short_Reviews_Checked.py đã làm — xem docstring file đó để biết lý do kỹ
thuật: `to_excel(index=False)` không lưu lại index gốc nên đọc lại file .xlsx
trên đĩa KHÔNG khôi phục đúng vị trí dòng ban đầu, phải tính lại từ raw), tự
gộp 2 file đã duyệt NẾU đã tồn tại, và IN CẢNH BÁO RÕ RÀNG ra console nếu 1
trong 2 file đó CHƯA tồn tại (kết quả khi đó là TẠM THỜI, không âm thầm coi
như "đã xong"). Nhờ vậy `run_t216.py` không còn phụ thuộc việc các script
trước đó đã được chạy đúng thứ tự hay chưa — chỉ cần data/raw/ và 2 file đã
duyệt (nếu có) là đủ để tính ra kết quả ĐÚNG với tình trạng rà soát hiện tại.

`merge_checked_rows` tách riêng vì được dùng LẶP LẠI cho cả 2 vòng rà soát
(Short_reviews_Checked.xlsx, Suspect_URL_Spam_Checked.xlsx) — thuật toán giống
hệt phần merge trong Merge_Short_Reviews_Checked.py /
Merge_Suspect_URL_Spam_Checked.py (2 script đó KHÔNG bị sửa, vẫn giữ nguyên
logic cũ độc lập — xem thêm ghi chú trong run_t216.py).
"""

from pathlib import Path

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from dataio.file_registry import raw_path
from transforms.tang1_structural import (
    SCRAPED_AT_COL,
    drop_empty_rows,
    fix_data_types,
    fix_field_misalignment,
)
from transforms.tang2_content_quality import (
    drop_emoji_or_special_char_only_reviews,
    split_short_reviews,
    split_url_hotline_or_spam_reviews,
)

SHORT_REVIEWS_CHECKED_PATH = DATA_INTERIM_DIR / "Short_reviews_Checked.xlsx"
SUSPECT_URL_SPAM_CHECKED_PATH = DATA_INTERIM_DIR / "Suspect_URL_Spam_Checked.xlsx"
PRODUCT_COL = "Sản phẩm"
SOURCE_ROW_COL = "Dòng Excel gốc"


def merge_checked_rows(
    kept: pd.DataFrame,
    suspect: pd.DataFrame,
    checked_path: Path,
    product: str,
    step_label: str,
) -> pd.DataFrame:
    """Hoà lại các dòng đã duyệt thủ công (đọc từ `checked_path`, lọc theo
    'Sản phẩm' == `product`) vào `kept`, dùng `suspect.index` để validate —
    thuật toán giống hệt phần merge trong Merge_Short_Reviews_Checked.py /
    Merge_Suspect_URL_Spam_Checked.py (gộp lại thành 1 hàm dùng chung vì cả 2
    script đó VÀ `build_reviewed_t214_dataframe` bên dưới đều cần đúng 1 thuật
    toán này).

    Nếu `checked_path` CHƯA TỒN TẠI (con người CHƯA rà soát xong): in CẢNH BÁO
    ra console và trả về `kept` NGUYÊN VẸN (không gộp thêm dòng nào) — kết quả
    gọi hàm này khi đó là TẠM THỜI, cần chạy lại sau khi có đủ file đã duyệt.
    """
    if not checked_path.exists():
        print(
            f"[{product}][{step_label}] CANH BAO: chua co {checked_path.name} "
            f"— dung tam 'kept' (chua ra soat/hoa cac dong nghi van), ket qua "
            f"hien tai la TAM THOI."
        )
        return kept.copy()

    checked = pd.read_excel(checked_path)
    unknown_products = set(checked[PRODUCT_COL].unique()) - set(PRODUCT_FILES)
    if unknown_products:
        raise ValueError(
            f"Cot '{PRODUCT_COL}' trong {checked_path} co gia tri khong hop "
            f"le: {sorted(unknown_products)}. San pham hop le: "
            f"{sorted(PRODUCT_FILES)}."
        )

    approved = checked.loc[checked[PRODUCT_COL] == product].copy()
    if approved.empty:
        return kept.copy()

    approved.index = approved[SOURCE_ROW_COL] - 2
    approved = approved.drop(columns=[PRODUCT_COL, SOURCE_ROW_COL])

    duplicated_idx = approved.index[approved.index.duplicated()]
    if not duplicated_idx.empty:
        raise ValueError(
            f"[{product}] {checked_path} co {len(duplicated_idx)} dong trung "
            f"'{SOURCE_ROW_COL}': {sorted(set(duplicated_idx))[:10]}... Kiem "
            f"tra lai co bi copy-paste nham dong khi ra soat khong."
        )

    invalid_idx = approved.index.difference(suspect.index)
    if not invalid_idx.empty:
        raise ValueError(
            f"[{product}] {len(invalid_idx)} dong trong {checked_path} co "
            f"'{SOURCE_ROW_COL}' khong khop bat ky dong nghi van nao da tach "
            f"cho san pham nay (index goc: {sorted(invalid_idx)[:10]}...). "
            f"Kiem tra lai cot '{PRODUCT_COL}'/'{SOURCE_ROW_COL}' co bi sua "
            f"nham khi ra soat khong."
        )

    return pd.concat([kept, approved]).sort_index()


def build_reviewed_t214_dataframe(name: str) -> pd.DataFrame:
    """Tính lại TỪ ĐẦU (từ data/raw/) toàn bộ chuỗi T1.1 -> T2.14 cho 1 sản
    phẩm, TRONG BỘ NHỚ — không đọc bất kỳ {name}_t2.12.xlsx /
    {name}_t2.14.xlsx nào trên đĩa (xem docstring module để biết lý do).

    Trả về DataFrame tương đương {name}_t2.14.xlsx SAU KHI đã hoà đủ 2 vòng rà
    soát thủ công (nếu 2 file Checked tương ứng đã tồn tại) — nếu 1 trong 2
    file Checked CHƯA có, phần tương ứng sẽ CHƯA gộp các dòng nghi vấn đã
    duyệt (in CẢNH BÁO, xem `merge_checked_rows`) — GỌI HÀM NÀY NHIỀU LẦN VỚI
    CÙNG raw/ + CÙNG 2 file Checked LUÔN cho kết quả (và index) GIỐNG HỆT nhau
    (hàm thuần theo nghĩa phụ thuộc duy nhất vào trạng thái các file trên đĩa,
    không có state ẩn nào khác) — đây là điều kiện để `run_t216.py` và
    `Merge_Suspect_Duplicate_Content_Checked.py` gọi hàm này ĐỘC LẬP ở 2 lần
    chạy khác nhau mà vẫn khớp đúng index với nhau.
    """
    raw = pd.read_excel(raw_path(name))

    after_t11 = fix_field_misalignment(raw)
    after_t13 = drop_empty_rows(after_t11)
    after_t15 = fix_data_types(after_t13)
    after_t29 = drop_emoji_or_special_char_only_reviews(after_t15)
    kept_212, short = split_short_reviews(after_t29)

    # .xlsx (openpyxl) khong ho tro datetime co tz -> bo nhan tz truoc khi
    # ghep voi cac dong doc tu Short_reviews_Checked.xlsx (da tz-naive san vi
    # doc tu 1 file .xlsx da tung xuat) -- giong het run_t212.py/
    # Merge_Short_Reviews_Checked.py.
    kept_212 = kept_212.copy()
    kept_212[SCRAPED_AT_COL] = kept_212[SCRAPED_AT_COL].dt.tz_localize(None)
    t212 = merge_checked_rows(kept_212, short, SHORT_REVIEWS_CHECKED_PATH, name, "T2.11+T2.12")

    kept_214, suspect_214 = split_url_hotline_or_spam_reviews(t212)
    t214 = merge_checked_rows(kept_214, suspect_214, SUSPECT_URL_SPAM_CHECKED_PATH, name, "T2.13+T2.14")
    return t214
