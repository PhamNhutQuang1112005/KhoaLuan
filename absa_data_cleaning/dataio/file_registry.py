"""
dataio/file_registry.py
=========================
Khai báo danh sách file input hiện có + quy ước đặt tên output.
Tách riêng khỏi config/settings.py để dataio/ có thể tự chứa toàn bộ logic
liên quan tên file/đường dẫn, nhưng vẫn tham chiếu settings cho hằng số dùng chung.

TODO: cân nhắc gộp với config.settings.PRODUCT_FILES thành 1 nguồn duy nhất
(hiện đang khai báo ở 2 nơi cho mục đích minh hoạ — cần dọn khi triển khai thật).
"""

from pathlib import Path

from config.settings import DATA_INTERIM_DIR, DATA_RAW_DIR, PRODUCT_FILES


def raw_path(product: str) -> Path:
    """Đường dẫn file gốc của 1 sản phẩm, VD raw_path('phone') -> data/raw/phone.xlsx"""
    try:
        filename = PRODUCT_FILES[product]
    except KeyError as exc:
        raise KeyError(
            f"Không tìm thấy sản phẩm '{product}' trong PRODUCT_FILES. "
            f"Các sản phẩm hợp lệ: {sorted(PRODUCT_FILES)}"
        ) from exc
    return DATA_RAW_DIR / filename


def interim_path(step_id: str, product: str) -> Path:
    """Đường dẫn output trung gian của 1 step cho 1 sản phẩm.

    Quy ước: data/interim/<step_id>/<product>.xlsx
    """
    return DATA_INTERIM_DIR / step_id / f"{product}.xlsx"


def all_products() -> list[str]:
    """Danh sách khoá sản phẩm hiện có (vd ['ipad', 'buds', 'watch', 'pin', 'phone', ...])."""
    return list(PRODUCT_FILES.keys())
