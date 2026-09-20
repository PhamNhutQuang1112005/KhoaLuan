"""
pipelines/build_reviewed_t219.py
===================================
Tính lại TỪ ĐẦU chuỗi T1.1 -> T2.19 cho 1 sản phẩm, NGAY TRONG BỘ NHỚ — nối
tiếp `pipelines.build_reviewed_t218.build_reviewed_t218_dataframe` bằng
`split_spelling_error_reviews` (T2.19) rồi áp kết quả kiểm duyệt thủ công
`Suspect_Spelling_Errors_Checked.xlsx` (nếu đã có).

KHÁC `merge_checked_rows` (dùng cho T2.11-T2.18, nơi dòng bị XOÁ khỏi file
Checked nghĩa là con người loại bỏ dòng đó): sửa chính tả KHÔNG loại dòng nào.
Quy ước ở đây:
  - Dòng nghi vấn KHÔNG có trong Checked (hoặc ô 'Nội dung sau xử lý' để
    trống) -> giữ NGUYÊN văn gốc (không áp đề xuất chưa được duyệt).
  - Dòng có trong Checked -> 'Nội dung tự do' := 'Nội dung sau xử lý' (bản đã
    duyệt/chỉnh tay). Muốn từ chối 1 đề xuất: xoá dòng đó, để trống ô, hoặc
    chép lại văn gốc vào ô.
Checked CHƯA tồn tại -> in CẢNH BÁO và giữ nguyên văn gốc toàn bộ (kết quả
TẠM THỜI). Gọi nhiều lần với cùng raw/ + cùng file Checked luôn cho cùng kết
quả (điều kiện để run_t219.py và Merge_Suspect_Spelling_Errors_Checked.py
khớp index với nhau, giống các pipelines/build_reviewed_t2xx.py khác).
"""

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from pipelines.build_reviewed_t214 import PRODUCT_COL, SOURCE_ROW_COL
from pipelines.build_reviewed_t218 import build_reviewed_t218_dataframe
from transforms.tang2_content_quality import (
    CONTENT_COL,
    CORRECTED_CONTENT_COL,
    CORRECTION_DETAIL_COL,
    split_spelling_error_reviews,
)

SUSPECT_SPELLING_ERRORS_CHECKED_PATH = DATA_INTERIM_DIR / "Suspect_Spelling_Errors_Checked.xlsx"


def apply_spelling_review(kept: pd.DataFrame, suspect: pd.DataFrame, checked_path, product: str) -> pd.DataFrame:
    """Ghép `kept` + `suspect` (bỏ 2 cột phụ trợ) thành 1 DataFrame đủ dòng,
    thay 'Nội dung tự do' bằng 'Nội dung sau xử lý' đã duyệt trong
    `checked_path` (lọc theo 'Sản phẩm' == `product`) — xem docstring module."""
    restored = suspect.drop(columns=[CORRECTED_CONTENT_COL, CORRECTION_DETAIL_COL])
    if not checked_path.exists():
        print(
            f"[{product}][T2.19] CANH BAO: chua co {checked_path.name} — giu "
            f"nguyen van goc cho {len(suspect)} dong nghi sai chinh ta, ket "
            f"qua hien tai la TAM THOI."
        )
        return pd.concat([kept, restored]).sort_index()

    checked = pd.read_excel(checked_path)
    unknown_products = set(checked[PRODUCT_COL].unique()) - set(PRODUCT_FILES)
    if unknown_products:
        raise ValueError(
            f"Cot '{PRODUCT_COL}' trong {checked_path} co gia tri khong hop "
            f"le: {sorted(unknown_products)}. San pham hop le: {sorted(PRODUCT_FILES)}."
        )
    approved = checked.loc[checked[PRODUCT_COL] == product].copy()
    approved.index = approved[SOURCE_ROW_COL] - 2

    duplicated_idx = approved.index[approved.index.duplicated()]
    if not duplicated_idx.empty:
        raise ValueError(
            f"[{product}] {checked_path} co {len(duplicated_idx)} dong trung "
            f"'{SOURCE_ROW_COL}': {sorted(set(duplicated_idx))[:10]}..."
        )
    invalid_idx = approved.index.difference(suspect.index)
    if not invalid_idx.empty:
        raise ValueError(
            f"[{product}] {len(invalid_idx)} dong trong {checked_path} co "
            f"'{SOURCE_ROW_COL}' khong khop dong nghi sai chinh ta nao da tach "
            f"cho san pham nay (index goc: {sorted(invalid_idx)[:10]}...). "
            f"Kiem tra lai cot '{PRODUCT_COL}'/'{SOURCE_ROW_COL}'."
        )

    corrected = approved[CORRECTED_CONTENT_COL]
    corrected = corrected[corrected.notna() & (corrected.astype(str).str.strip() != "")]
    restored.loc[corrected.index, CONTENT_COL] = corrected
    return pd.concat([kept, restored]).sort_index()


def build_reviewed_t219_dataframe(name: str) -> pd.DataFrame:
    """T1.1 -> T2.19 cho 1 sản phẩm, trong bộ nhớ (xem docstring module)."""
    kept, suspect = split_spelling_error_reviews(build_reviewed_t218_dataframe(name))
    return apply_spelling_review(kept, suspect, SUSPECT_SPELLING_ERRORS_CHECKED_PATH, name)
