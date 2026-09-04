"""
core/step_base.py
==================
Abstract base class ProcessingStep — đơn vị nhỏ nhất có thể chạy độc lập
trong pipeline. Mỗi step:
- Bọc quanh 1 (hoặc vài) hàm thuần từ transforms/ (lõi FP).
- Biết mã taxonomy của mình (T<tầng>.<stt>) để phục vụ truy vết & báo cáo.
- Tự sinh CleaningReport khi chạy xong (số dòng thay đổi, ví dụ trước/sau).

QUAN TRỌNG: ProcessingStep KHÔNG chứa logic làm sạch. Nó chỉ điều phối:
đọc DataFrame vào -> gọi hàm thuần -> so sánh trước/sau -> trả DataFrame ra.
Logic làm sạch thật nằm trong transforms/*.py (pure function, dễ test riêng).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Optional

import pandas as pd

from core.report import CleaningReport


@dataclass
class StepMeta:
    """Metadata mô tả 1 step, dùng để hiển thị CLI / sinh báo cáo luận văn."""

    taxonomy_id: str  # VD: "T2.17"
    tang: int  # 1..4
    name: str  # VD: "teencode_normalize"
    description: str
    severity: str = ""  # "Thấp" | "Trung bình" | "Nghiêm trọng" — theo cột Mức độ


class ProcessingStep(ABC):
    """Một bước xử lý độc lập, có thể chạy riêng lẻ qua CLI.

    Cách dùng dự kiến:
        step = SomeConcreteStep()
        report = step.run(df)          # df đã đọc từ Reader
        step.report                    # CleaningReport vừa sinh ra
    """

    meta: StepMeta

    @abstractmethod
    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """Áp dụng (các) hàm thuần liên quan lên `df`, trả về DataFrame mới.

        TODO khi implement:
        1. Gọi hàm thuần tương ứng trong transforms/tang*_*.py.
        2. So sánh df trước/sau để tính số liệu (dùng core.report.CleaningReport).
        3. KHÔNG side-effect I/O ở đây (không đọc/ghi file) — việc đó thuộc về
           core/pipeline.py + dataio/.
        """
        raise NotImplementedError

    def build_report(
        self, df_before: pd.DataFrame, df_after: pd.DataFrame
    ) -> CleaningReport:
        """Tiện ích dùng chung để các step con tạo report thống nhất.

        TODO: implement (đếm số dòng thay đổi/xoá, lấy vài ví dụ minh hoạ).
        """
        raise NotImplementedError


# --- Kiểu hàm thuần chuẩn mà transforms/*.py phải tuân theo -----------------
# Dùng để type-hint và để StepRegistry kiểm tra chữ ký khi đăng ký (xem registry.py).
PureTransformFn = Callable[[pd.DataFrame], pd.DataFrame]
