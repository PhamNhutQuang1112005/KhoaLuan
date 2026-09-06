"""
core/diff_report.py
=====================
Tiện ích so sánh 2 DataFrame (truoc/sau khi ap dung 1 ham lam sach) va IN RA
CONSOLE danh sach dong da THEM / da XOA / da SUA (kem SO DONG CU THE) VA cot da
THEM/XOA (vd buoc tach 1 cot thanh nhieu cot nhu T1.6), de co the quan sat truc
tiep khi chay test (tests/test_*.py) hoac file chay thuc te (run_*.py).

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
    """So sanh 2 DataFrame theo index VA theo cot, tra ve:
      {"added": [idx, ...], "removed": [idx, ...], "changed": {idx: [cot, ...]},
       "added_columns": [ten_cot, ...], "removed_columns": [ten_cot, ...]}

    "changed" chi xet cac COT CHUNG giua 2 DataFrame — buoc nao chi THEM cot
    moi (vd T1.6 tach 1 cot thanh nhieu cot) se khong co dong nao trong
    "changed", nhung se the hien qua "added_columns".
    """
    before_idx = set(df_before.index)
    after_idx = set(df_after.index)

    added = sorted(after_idx - before_idx)
    removed = sorted(before_idx - after_idx)

    common_cols = [c for c in df_before.columns if c in df_after.columns]
    added_columns = [c for c in df_after.columns if c not in df_before.columns]
    removed_columns = [c for c in df_before.columns if c not in df_after.columns]

    changed: dict = {}
    for idx in sorted(before_idx & after_idx):
        changed_cols = [
            col
            for col in common_cols
            if not _values_equal(df_before.at[idx, col], df_after.at[idx, col])
        ]
        if changed_cols:
            changed[idx] = changed_cols

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "added_columns": added_columns,
        "removed_columns": removed_columns,
    }


def print_row_diff(
    df_before: pd.DataFrame,
    df_after: pd.DataFrame,
    label: str = "",
    excel_row_offset: int = 0,
    max_list: int | None = None,
) -> dict:
    """In ra console cac dong da THEM / da XOA / da SUA (kem so dong cu the).

    `excel_row_offset`: cong them vao index truoc khi in, de so dong hien thi
    khop voi so dong khi mo file .xlsx goc bang Excel. Truyen 2 khi du lieu
    doc tu file .xlsx that (1 vi Excel danh so tu 1, +1 vi dong 1 la header).
    Mac dinh 0 -> in dung index cua DataFrame (dung cho DataFrame dung trong
    test, khong ung voi file Excel nao).

    `max_list`: neu so dong THEM/XOA/SUA vuot qua nguong nay, chi in gon
    "tu dong #dau -> #cuoi (N dong)" thay vi liet ke tung dong. Dung cho cac
    buoc ep kieu/chuan hoa toan bo cot (vd T1.5) — vi hau nhu MOI dong con lai
    deu bi tinh la "thay doi" (do doi kieu du lieu) nen liet ke het se rat dai
    va khong con nhieu y nghia. Mac dinh None -> luon liet ke day du (dung cho
    cac buoc chi sua vai dong cu the nhu T1.1).

    Tra ve dict ket qua tu `diff_rows` de co the assert them neu can trong test
    (cac idx trong dict tra ve LUON la index goc cua DataFrame, chua cong offset).
    """
    result = diff_rows(df_before, df_after)
    prefix = f"[{label}] " if label else ""

    def _row_label(idx) -> str:
        return f"#{idx + excel_row_offset}" if excel_row_offset else f"#{idx}"

    def _format_indices(indices) -> str:
        if max_list is not None and len(indices) > max_list:
            return f"{_row_label(indices[0])} -> {_row_label(indices[-1])} ({len(indices)} dong)"
        return ", ".join(_row_label(i) for i in indices)

    if result["added_columns"]:
        print(f"{prefix}Da THEM {len(result['added_columns'])} cot: {', '.join(result['added_columns'])}")

    if result["removed_columns"]:
        print(f"{prefix}Da XOA {len(result['removed_columns'])} cot: {', '.join(result['removed_columns'])}")

    if not result["added"] and not result["removed"] and not result["changed"]:
        if not result["added_columns"] and not result["removed_columns"]:
            print(f"{prefix}Khong co dong nao thay doi.")
        return result

    if result["added"]:
        print(f"{prefix}Da THEM {len(result['added'])} dong: {_format_indices(result['added'])}")

    if result["removed"]:
        print(f"{prefix}Da XOA {len(result['removed'])} dong: {_format_indices(result['removed'])}")

    if result["changed"]:
        changed_indices = sorted(result["changed"])
        if max_list is not None and len(changed_indices) > max_list:
            print(f"{prefix}Da SUA {len(changed_indices)} dong: {_format_indices(changed_indices)}")
        else:
            print(f"{prefix}Da SUA {len(changed_indices)} dong:")
            for idx in changed_indices:
                cols = result["changed"][idx]
                print(f"{prefix}  - dong {_row_label(idx)}: cot {', '.join(cols)}")

    return result
