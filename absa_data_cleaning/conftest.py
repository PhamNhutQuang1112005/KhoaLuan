"""
conftest.py
============
Đảm bảo pytest luôn import được các package nằm ngay dưới absa_data_cleaning/
(`transforms`, `config`, `dataio`, ...) bất kể pytest được chạy từ thư mục nào
(vd chạy `pytest` từ thư mục gốc repo thay vì từ absa_data_cleaning/).

Cần thiết vì `tests/` có __init__.py (là 1 package) nhưng absa_data_cleaning/
thì không, nên nếu không có file này, một số cách chạy IDE/pytest sẽ không tự
thêm absa_data_cleaning/ vào sys.path, gây lỗi
`ModuleNotFoundError: No module named 'transforms'`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
