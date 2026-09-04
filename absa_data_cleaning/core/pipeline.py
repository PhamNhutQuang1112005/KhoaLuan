"""
core/pipeline.py
=================
class Pipeline: bộ điều phối trung tâm (khung OOP). Đây là nơi DUY NHẤT
chịu trách nhiệm quyết định "input của step này lấy từ đâu" — theo nguyên tắc
mô tả ở README mục 3 (chạy từng bước, không bắt buộc chạy hết).

Pipeline KHÔNG chứa logic làm sạch. Nó chỉ:
1. Đọc cấu hình (config/pipeline_config.yaml).
2. Với mỗi step được yêu cầu chạy: xác định input path -> đọc -> gọi step.run()
   -> ghi output -> lưu report.
"""

from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from core.report import CleaningReport
from core.step_base import ProcessingStep


class Pipeline:
    def __init__(
        self,
        raw_dir: Path,
        interim_dir: Path,
        processed_dir: Path,
        logs_dir: Path,
    ) -> None:
        self.raw_dir = raw_dir
        self.interim_dir = interim_dir
        self.processed_dir = processed_dir
        self.logs_dir = logs_dir

    def resolve_input_path(self, step: ProcessingStep, product: str) -> Path:
        """Tìm file input phù hợp cho `step` trên `product`.

        Quy tắc dự kiến (xem README mục 3):
        - Nếu step trước đó (theo depends_on trong pipeline_config.yaml) đã có
          output trong interim_dir -> dùng file đó.
        - Nếu không có step trước / chưa chạy -> dùng file gốc trong raw_dir.

        TODO: implement, đọc depends_on từ config/pipeline_config.yaml.
        """
        raise NotImplementedError

    def resolve_output_path(self, step: ProcessingStep, product: str) -> Path:
        """Trả về đường dẫn output cho step này: interim_dir/<step_id>/<product>.xlsx

        TODO: implement.
        """
        raise NotImplementedError

    def run_step(self, step: ProcessingStep, products: Iterable[str]) -> list[CleaningReport]:
        """Chạy 1 step độc lập trên danh sách sản phẩm chỉ định (mặc định: tất cả).

        Đây là entry point chính cho yêu cầu "chạy từng lần xử lý 1" — không bắt
        buộc phải gọi run_tang hay run_full.

        TODO: implement theo vòng đời mô tả ở README mục 5:
        đọc -> step.run() -> report -> ghi output -> lưu report.
        """
        raise NotImplementedError

    def run_tang(self, tang: int, products: Iterable[str]) -> list[CleaningReport]:
        """Chạy toàn bộ step thuộc 1 tầng, theo đúng thứ tự khai báo trong
        pipeline_config.yaml (tôn trọng depends_on).

        TODO: implement — lấy danh sách step từ core.registry.StepRegistry.list_by_tang,
        rồi gọi run_step tuần tự.
        """
        raise NotImplementedError

    def run_full(self, products: Iterable[str]) -> list[CleaningReport]:
        """Chạy nối tiếp cả 4 tầng — TUỲ CHỌN, không phải cách dùng bắt buộc.

        TODO: implement, gọi run_tang(1..4) tuần tự và ghi output cuối cùng
        vào processed_dir thay vì interim_dir.
        """
        raise NotImplementedError
