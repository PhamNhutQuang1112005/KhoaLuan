"""
convert_raw_to_markdown.py — nhân bản toàn bộ file trong data/raw/ sang
Markdown, ghi ra data/raw_markdown/ (mỗi {name}.xlsx -> 1 file {name}.md, nội
dung là 1 bảng Markdown đầy đủ dữ liệu GỐC, KHÔNG qua bất kỳ bước làm sạch
nào — nhân bản thuần định dạng).

Đây chỉ là script chạy tay tiện ích, KHÔNG phải 1 phần của pipeline chính:
    python convert_raw_to_markdown.py
"""

import pandas as pd

from config.settings import DATA_RAW_MARKDOWN_DIR, PRODUCT_FILES
from dataio.file_registry import raw_path


def _cell_to_markdown(value) -> str:
    """1 giá trị ô -> chuỗi an toàn cho ô bảng Markdown: NaN -> rỗng, thoát ký
    tự '|' (phân cách cột), gộp xuống dòng trong nội dung (vd 'Nội dung tự
    do' nhiều dòng) thành khoảng trắng vì bảng Markdown không cho phép ô chứa
    xuống dòng thật."""
    if pd.isna(value):
        return ""
    text = str(value).replace("|", "\\|")
    return " ".join(text.split())


def dataframe_to_markdown_table(df: pd.DataFrame) -> str:
    """DataFrame -> bảng Markdown (pipe table) đầy đủ dữ liệu, giữ nguyên thứ
    tự cột/dòng gốc."""
    header = "| " + " | ".join(df.columns) + " |"
    separator = "| " + " | ".join("---" for _ in df.columns) + " |"
    rows = (
        "| " + " | ".join(_cell_to_markdown(v) for v in row) + " |"
        for row in df.itertuples(index=False)
    )
    return "\n".join([header, separator, *rows]) + "\n"


DATA_RAW_MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)

for name in PRODUCT_FILES:
    src_path = raw_path(name)
    df = pd.read_excel(src_path)
    out_path = DATA_RAW_MARKDOWN_DIR / f"{name}.md"
    out_path.write_text(dataframe_to_markdown_table(df), encoding="utf-8")
    print(f"{src_path} -> {out_path} ({len(df)} dong)")
