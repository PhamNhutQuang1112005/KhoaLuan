"""
core/diff_report.py
=====================
Tiện ích so sánh 2 DataFrame (truoc/sau khi ap dung 1 ham lam sach) va IN RA
CONSOLE danh sach dong da THEM / da XOA / da SUA, kem SO DONG CU THE de co the
quan sat truc tiep khi chay test (tests/test_*.py) hoac file chay thuc te
(run_*.py).

So dong in ra MAC DINH la index cua DataFrame (0-based, giu nguyen tu
pd.read_excel/pd.DataFrame goc). LUU Y: khi mo file .xlsx tuong ung bang Excel,
so dong ban thay se LON HON index nay 2 don vi (1 vi Excel danh so dong tu 1
thay vi 0, +1 nua vi dong 1 la header nen khong nam trong DataFrame). VD: index
479 -> Excel row 481.

Khi goi `print_row_diff` cho du lieu doc tu file .xlsx that (nhu run_t11.py),
truyen `excel_row_offset=2` de in thang so dong Excel, khoi phai tu quy doi.
"""

from __future__ import annotations

import sys

import pandas as pd

# Console Windows (cp1258/cp1252/...) khong encode duoc dau tieng Viet -> ep
# stdout sang UTF-8 de print() khong crash khi chay `pytest -s` hay chay truc
# tiep script tren terminal Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


def _values_equal(a, b) -> bool:
    try:
        if pd.isna(a) and pd.isna(b):
            return True
    except (TypeError, ValueError):
        pass
    return a == b


def diff_rows(df_before: pd.DataFrame, df_after: pd.DataFrame) -> dict:
    """So sanh 2 DataFrame theo index, tra ve:
      {"added": [idx, ...], "removed": [idx, ...], "changed": {idx: [cot, ...]}}
    """
    before_idx = set(df_before.index)
    after_idx = set(df_after.index)

    added = sorted(after_idx - before_idx)
    removed = sorted(before_idx - after_idx)

    changed: dict = {}
    common_cols = [c for c in df_before.columns if c in df_after.columns]
    for idx in sorted(before_idx & after_idx):
        changed_cols = [
            col
            for col in common_cols
            if not _values_equal(df_before.at[idx, col], df_after.at[idx, col])
        ]
        if changed_cols:
            changed[idx] = changed_cols

    return {"added": added, "removed": removed, "changed": changed}


def print_row_diff(
    df_before: pd.DataFrame,
    df_after: pd.DataFrame,
    label: str = "",
    excel_row_offset: int = 0,
) -> dict:
    """In ra console cac dong da THEM / da XOA / da SUA (kem so dong cu the).

    `excel_row_offset`: cong them vao index truoc khi in, de so dong hien thi
    khop voi so dong khi mo file .xlsx goc bang Excel. Truyen 2 khi du lieu
    doc tu file .xlsx that (1 vi Excel danh so tu 1, +1 vi dong 1 la header).
    Mac dinh 0 -> in dung index cua DataFrame (dung cho DataFrame dung trong
    test, khong ung voi file Excel nao).

    Tra ve dict ket qua tu `diff_rows` de co the assert them neu can trong test
    (cac idx trong dict tra ve LUON la index goc cua DataFrame, chua cong offset).
    """
    result = diff_rows(df_before, df_after)
    prefix = f"[{label}] " if label else ""

    def _row_label(idx) -> str:
        return f"#{idx + excel_row_offset}" if excel_row_offset else f"#{idx}"

    if not result["added"] and not result["removed"] and not result["changed"]:
        print(f"{prefix}Khong co dong nao thay doi.")
        return result

    if result["added"]:
        rows = ", ".join(_row_label(i) for i in result["added"])
        print(f"{prefix}Da THEM {len(result['added'])} dong: {rows}")

    if result["removed"]:
        rows = ", ".join(_row_label(i) for i in result["removed"])
        print(f"{prefix}Da XOA {len(result['removed'])} dong: {rows}")

    if result["changed"]:
        print(f"{prefix}Da SUA {len(result['changed'])} dong:")
        for idx, cols in result["changed"].items():
            print(f"{prefix}  - dong {_row_label(idx)}: cot {', '.join(cols)}")

    return result
