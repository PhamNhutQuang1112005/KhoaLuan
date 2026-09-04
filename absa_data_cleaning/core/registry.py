"""
core/registry.py
=================
Cầu nối giữa lõi FP (hàm thuần trong transforms/) và khung OOP (ProcessingStep).

Ý tưởng: thay vì phải viết 1 class ProcessingStep con cho từng vấn đề trong 52 mục
taxonomy (rất nhiều boilerplate), ta cho phép đăng ký trực tiếp 1 hàm thuần bằng
decorator `@register_step`, và registry sẽ tự bọc nó thành 1 ProcessingStep chuẩn.

Đây cũng là nơi trả lời câu hỏi "vấn đề T2.17 hiện có hàm xử lý chưa, tên gì,
đăng ký ở step nào" — phục vụ đối chiếu tiến độ với bảng taxonomy 52 mục.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from core.step_base import PureTransformFn, StepMeta


@dataclass
class RegisteredStep:
    meta: StepMeta
    fn: PureTransformFn


class StepRegistry:
    """Registry toàn cục (singleton theo module) chứa mọi step đã đăng ký."""

    _steps: dict[str, RegisteredStep] = {}

    @classmethod
    def register(cls, meta: StepMeta, fn: PureTransformFn) -> None:
        """Đăng ký 1 hàm thuần vào registry theo mã taxonomy.

        TODO: implement — cần kiểm tra trùng taxonomy_id, validate chữ ký hàm fn.
        """
        raise NotImplementedError

    @classmethod
    def get(cls, taxonomy_id: str) -> Optional[RegisteredStep]:
        """Lấy step đã đăng ký theo mã taxonomy, VD 'T2.17'."""
        raise NotImplementedError

    @classmethod
    def list_by_tang(cls, tang: int) -> list[RegisteredStep]:
        """Liệt kê toàn bộ step thuộc 1 tầng — dùng để chạy theo tầng."""
        raise NotImplementedError

    @classmethod
    def coverage_report(cls) -> dict:
        """So sánh danh sách step đã đăng ký với đầy đủ 52 mục taxonomy,
        trả về mục nào đã có code / chưa có — hỗ trợ viết luận văn (mục 6 README).

        TODO: implement, có thể đọc trực tiếp taxonomy/taxonomy_loader.py để
        lấy danh sách 52 mục làm baseline đối chiếu.
        """
        raise NotImplementedError


def register_step(
    taxonomy_id: str,
    tang: int,
    name: str,
    description: str = "",
    severity: str = "",
):
    """Decorator để gắn 1 hàm thuần trong transforms/ vào StepRegistry.

    Cách dùng dự kiến trong transforms/tang2_content_quality.py:

        @register_step(
            taxonomy_id="T2.17",
            tang=2,
            name="teencode_normalize",
            description="Chuẩn hoá teencode trong cột Nội dung tự do",
            severity="Trung bình",
        )
        def normalize_teencode(df: pd.DataFrame) -> pd.DataFrame:
            ...  # logic thật, viết sau

    TODO: implement — gọi StepRegistry.register() với StepMeta dựng từ tham số.
    """

    def decorator(fn: PureTransformFn) -> PureTransformFn:
        raise NotImplementedError

    return decorator
