"""
taxonomy/taxonomy_loader.py
==============================
PLACEHOLDER — tiện ích đọc file taxonomy nghiệp vụ
(`Taxonomy_lam_sach_du_lieu_ABSA_v2.xlsx` hiện tại, hoặc phiên bản Aspect
Taxonomy sau này) để dùng cho:

- core/registry.py -> StepRegistry.coverage_report() (đối chiếu 52 mục làm sạch
  với các step đã cài đặt).
- taxonomy/aspect_taxonomy.py khi bắt đầu xây taxonomy khía cạnh.

Tách riêng khỏi aspect_taxonomy.py vì đây là việc ĐỌC dữ liệu taxonomy (I/O),
không phải ĐỊNH NGHĨA cấu trúc taxonomy.
"""

from pathlib import Path


def load_cleaning_taxonomy(xlsx_path: Path) -> list[dict]:
    """Đọc sheet 'Taxonomy làm sạch' từ file taxonomy hiện tại, trả về danh sách
    52 mục dạng dict (Tầng, STT, Vấn đề, Mức độ, Đề xuất xử lý...).

    Dùng để đối chiếu tự động với core.registry.StepRegistry (mục nào đã có code,
    mục nào chưa) — hỗ trợ báo cáo tiến độ trong luận văn.

    TODO: implement bằng pandas.read_excel, bỏ qua các dòng tiêu đề nhóm
    (VD 'TẦNG 1 — LỖI CẤU TRÚC DỮ LIỆU...') chỉ giữ dòng có STT là số.
    """
    raise NotImplementedError


def load_aspect_taxonomy(source: Path):
    """PLACEHOLDER cho giai đoạn xây Aspect Taxonomy — chưa triển khai.

    TODO (giai đoạn sau): implement khi có file taxonomy khía cạnh chính thức.
    """
    raise NotImplementedError
