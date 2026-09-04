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
    """Đường dẫn file gốc của 1 sản phẩm, VD raw_path('phone') -> data/raw/phone_2127.xlsx

    TODO: implement, raise KeyError rõ ràng nếu `product` không có trong PRODUCT_FILES.
    """
    raise NotImplementedError


def interim_path(step_id: str, product: str) -> Path:
    """Đường dẫn output trung gian của 1 step cho 1 sản phẩm.

    Quy ước: data/interim/<step_id>/<product>.xlsx
    TODO: implement.
    """
    raise NotImplementedError


def all_products() -> list[str]:
    """Danh sách khoá sản phẩm hiện có (vd ['ipad', 'buds', 'watch', 'pin', 'phone']).

    TODO: implement — trả về list(PRODUCT_FILES.keys()).
    """
    raise NotImplementedError
