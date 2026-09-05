"""
config/settings.py
===================
Nơi khai báo các hằng số / cấu hình dùng chung cho toàn bộ pipeline.
KHÔNG chứa logic xử lý — chỉ là dữ liệu tĩnh (đúng tinh thần "config as data").

Việc cần làm khi triển khai thật:
- Điền đường dẫn thực tế (có thể đọc từ biến môi trường để linh hoạt giữa máy/CI).
- Bổ sung ngành hàng mới khi crawl thêm (kế hoạch T8 tuần 1-2: thêm 2-3 ngành).
"""

from pathlib import Path

# --- Đường dẫn thư mục gốc ---------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_INTERIM_DIR = BASE_DIR / "data" / "interim"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
LOGS_DIR = BASE_DIR / "logs"

# --- Schema chuẩn 8 cột (theo taxonomy Tầng 1, mục 2) ------------------------
STANDARD_SCHEMA = [
    "Tác giả",
    "Thời gian",
    "Loại hàng (phân loại)",
    "Tiêu chí đánh giá",
    "Nội dung tự do",
    "Số sao",
    "URL sản phẩm",
    "Thời điểm cào",
]

# --- Danh sách sản phẩm / file input hiện có --------------------------------
# TODO: đồng bộ với dataio/file_registry.py — cân nhắc gộp 2 nơi này làm 1
# nguồn sự thật duy nhất (single source of truth) khi triển khai thật.
# Cập nhật theo tên file thực tế hiện có trong data/raw/ (đã đổi tên, bỏ hậu tố số lượng dòng).
PRODUCT_FILES = {
    "ipad": "ipad.xlsx",
    "buds": "buds.xlsx",
    "watch": "watch.xlsx",
    "pin": "pin.xlsx",
    "phone": "phone.xlsx",
    "ao": "ao.xlsx",
    "quan": "quan.xlsx",
    "vay": "vay.xlsx",
    "non": "non.xlsx",
    "vo": "vo.xlsx",
}

# --- Phạm vi nghiên cứu (dùng cho Tầng 4, mục 51-52) ------------------------
RESEARCH_PRODUCT_SCOPE = list(PRODUCT_FILES.keys())
ALLOWED_LANGUAGES = ["vi"]  # TODO: xác định chính sách với review code-switching (T2.26)

# --- Cấu hình mặc định (có thể override qua pipeline_config.yaml) ----------
DEFAULT_ENCODING = "utf-8"
NEAR_DUPLICATE_SIMILARITY_THRESHOLD = 0.9  # dùng cho T2.16 — cần tinh chỉnh thực nghiệm
