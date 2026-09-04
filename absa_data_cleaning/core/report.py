"""
core/report.py
===============
CleaningReport: đối tượng thu thập số liệu "trước/sau" mỗi lần chạy 1 step,
phục vụ:
- Truy vết trong quá trình phát triển (debug).
- Số liệu định lượng để đưa vào luận văn (VD: "loại bỏ 19 dòng lệch cột ở T1.1").

Đây là phần có trạng thái + side-effect (ghi log ra logs/) nên thuộc khung OOP.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class CleaningReport:
    step_id: str  # mã taxonomy, VD "T1.1"
    step_name: str
    product: str  # VD "phone", "ipad" — hoặc "ALL" nếu chạy liên file (Tầng 4)
    rows_before: int = 0
    rows_after: int = 0
    rows_changed: int = 0
    rows_dropped: int = 0
    examples: list[dict] = field(default_factory=list)  # vài ví dụ trước/sau minh hoạ
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    extra: dict[str, Any] = field(default_factory=dict)  # số liệu tuỳ step (VD ngưỡng dùng)

    def to_dict(self) -> dict:
        """Serialize để ghi ra JSON. TODO: implement."""
        raise NotImplementedError

    def save(self, logs_dir: Path) -> Path:
        """Ghi report ra logs/<step_id>_<product>_<timestamp>.json.

        TODO: implement — tạo thư mục nếu chưa có, dùng self.to_dict().
        """
        raise NotImplementedError

    def summary_line(self) -> str:
        """Trả về 1 dòng tóm tắt dùng để in ra console khi chạy CLI.

        VD: "[T1.1][phone] 1911 -> 1892 dòng (19 dòng bị sửa)"
        TODO: implement.
        """
        raise NotImplementedError
