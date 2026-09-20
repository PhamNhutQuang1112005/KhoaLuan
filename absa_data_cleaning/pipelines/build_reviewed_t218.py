"""
pipelines/build_reviewed_t218.py
===================================
Tính lại TỪ ĐẦU (từ data/raw/) toàn bộ chuỗi T1.1 -> T2.18 cho 1 sản phẩm,
NGAY TRONG BỘ NHỚ — nối tiếp `pipelines.build_reviewed_t214` (T1.1 -> T2.14)
bằng T2.15+T2.16 (giống hệt run_t216.py) rồi T2.17+T2.18 (giống hệt
`transforms.tang2_content_quality.normalize_teencode_and_abbreviations` +
`split_suspect_teencode_reviews`).

Lý do tách 2 hàm (`build_reviewed_t216_dataframe`, `build_reviewed_t218_dataframe`)
thay vì gộp 1 hàm: `Merge_Suspect_Teencode_Abbreviation_Checked.py` cần
`build_reviewed_t216_dataframe(name)` làm điểm bắt đầu để tự áp lại T2.17+T2.18
(giống cách `Merge_Suspect_Duplicate_Content_Checked.py` dùng
`build_reviewed_t214_dataframe`), không cần gọi lại toàn bộ `build_reviewed_t218_dataframe`.

Mỗi hàm gọi lại nhiều lần với CÙNG data/raw/ + CÙNG các file *_Checked.xlsx
LUÔN cho kết quả (và index) GIỐNG HỆT nhau — điều kiện để `run_t218.py` và
`Merge_Suspect_Teencode_Abbreviation_Checked.py` gọi độc lập ở 2 lần chạy
khác nhau mà vẫn khớp đúng index (xem thêm lý do kỹ thuật trong docstring
`pipelines.build_reviewed_t214`).
"""

from config.settings import DATA_INTERIM_DIR
from pipelines.build_reviewed_t214 import build_reviewed_t214_dataframe, merge_checked_rows
from transforms.tang2_content_quality import (
    drop_exact_duplicates,
    normalize_teencode_and_abbreviations,
    split_near_duplicate_reviews,
    split_suspect_teencode_reviews,
)

SUSPECT_DUPLICATE_CONTENT_CHECKED_PATH = DATA_INTERIM_DIR / "Suspect_Duplicate_Content_Checked.xlsx"
SUSPECT_TEENCODE_ABBREVIATION_CHECKED_PATH = DATA_INTERIM_DIR / "Suspect_Teencode_Abbreviation_Checked.xlsx"


def build_reviewed_t216_dataframe(name: str):
    """T1.1 -> T2.16 cho 1 sản phẩm, trong bộ nhớ (xem docstring module)."""
    t214 = build_reviewed_t214_dataframe(name)
    after_t215 = drop_exact_duplicates(t214)
    kept_216, suspect_216 = split_near_duplicate_reviews(after_t215)
    return merge_checked_rows(kept_216, suspect_216, SUSPECT_DUPLICATE_CONTENT_CHECKED_PATH, name, "T2.16")


def build_reviewed_t218_dataframe(name: str):
    """T1.1 -> T2.18 cho 1 sản phẩm, trong bộ nhớ (xem docstring module)."""
    t216 = build_reviewed_t216_dataframe(name)
    normalized = normalize_teencode_and_abbreviations(t216)
    kept_218, suspect_218 = split_suspect_teencode_reviews(normalized)
    return merge_checked_rows(kept_218, suspect_218, SUSPECT_TEENCODE_ABBREVIATION_CHECKED_PATH, name, "T2.17+T2.18")
