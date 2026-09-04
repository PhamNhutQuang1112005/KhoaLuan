"""
pipelines/pipeline_full.py
=============================
Ghép nối cả 4 tầng thành 1 lần chạy — CHỈ LÀ TUỲ CHỌN TIỆN LỢI, không phải cách
dùng bắt buộc. Theo yêu cầu thiết kế, mọi step/tầng đều phải chạy được độc lập
qua cli.py mà không cần đi qua file này.

TODO: implement — gọi tuần tự pipeline_tang1.run, pipeline_tang2.run,
pipeline_tang3.run, pipeline_tang4.run; output cuối cùng ghi vào
config.settings.DATA_PROCESSED_DIR thay vì DATA_INTERIM_DIR.
"""

from typing import Iterable

from core.pipeline import Pipeline
from pipelines import pipeline_tang1, pipeline_tang2, pipeline_tang3, pipeline_tang4


def run(pipeline: Pipeline, products: Iterable[str]):
    raise NotImplementedError
