"""
scripts/run_stage3.py — chạy Giai đoạn 3 (lọc thô) trên đầu ra Giai đoạn 2
(data/interim/v2_normalized/<tên>_step17_stage2_add_text_norm.xlsx, sinh bởi run_stage2.py), mỗi
bước ghi ra data/interim/v3_filtered/<tên>_<bước>_stage3_<xử lý gì>.xlsx và in diff theo số dòng
Excel:

    step8a  drop_exact_duplicates                (từng file)
    step21a drop_exact_duplicates_across_files   (giữa các file)
    step5   drop_emoji_or_special_char_only_reviews
    step7   split_url_hotline_or_spam_reviews    (+ file suspect_url)
    step19  split_non_vietnamese_reviews         (+ file suspect_non_vietnamese)

Không bước nào xoá mất dòng: mọi dòng bị loại đều được lưu ra file suspect/
*_removed (8a/21a: kèm cả dòng giữ lại để đối chiếu) để kiểm tra thủ công (nếu loại nhầm thì merge lại theo review_id).

step21a cần mọi file cùng lúc nên chạy theo thứ tự: step8a cho tất cả file,
rồi step21a, rồi các bước còn lại cho từng file. Kết quả cuối mỗi file:
<tên>_step19_stage3_filter_non_vietnamese.xlsx (= v3_filtered).

    python scripts/run_stage3.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from core.diff_report import print_row_diff
from transforms.stage1_structure import AUTHOR_COL, CONTENT_COL
from transforms.stage2_normalize import TEXT_NORM_COL
from transforms.stage3_coarse_filter import (
    _dedup_key_series,
    drop_emoji_or_special_char_only_reviews,
    drop_exact_duplicates,
    drop_exact_duplicates_across_files,
    split_non_vietnamese_reviews,
    split_url_hotline_or_spam_reviews,
)

IN_DIR = DATA_INTERIM_DIR / "v2_normalized"
OUT_DIR = DATA_INTERIM_DIR / "v3_filtered"
# (tag, hàm, hậu tố file suspect hoặc None nếu hàm chỉ trả về 1 df)
PER_FILE_STEPS = [
    ("step5_stage3_drop_emoji_special_only", drop_emoji_or_special_char_only_reviews, None),
    ("step7_stage3_filter_url_spam", split_url_hotline_or_spam_reviews, "step7_stage3_suspect_url_spam"),
    ("step19_stage3_filter_non_vietnamese", split_non_vietnamese_reviews, "step19_stage3_suspect_non_vietnamese"),
]


def _save(df: pd.DataFrame, name: str, tag: str) -> Path:
    path = OUT_DIR / f"{name}_{tag}.xlsx"
    df.to_excel(path, index=False)
    return path


def _save_removed(before: pd.DataFrame, after: pd.DataFrame, name: str, tag: str) -> None:
    """Bước xoá thẳng không có cặp (step5): lưu dòng bị loại ra file *_removed."""
    removed = before.loc[~before.index.isin(after.index)]
    print(f"[{name}] {tag}: {len(removed)} dong bi loai -> {_save(removed, name, tag + '_removed')}")


def _save_duplicate_evidence(before: dict, after: dict, col: str, tag: str) -> None:
    """Steps 8a/21a: với mỗi nhóm trùng, lưu CẢ dòng giữ lại LẪN dòng bị xoá
    (cột `dup_group`, `action` = keep/remove, `source` = file sản phẩm) để
    người kiểm duyệt đối chiếu trực tiếp. Mỗi sản phẩm một file *_removed,
    gồm các nhóm có dòng bị xoá thuộc sản phẩm đó."""
    allrows = pd.concat(
        [d.assign(source=n, orig_row=d.index) for n, d in before.items() if col in d.columns],
        ignore_index=True,
    )
    kept_ids = {(n, i) for n, d in after.items() for i in d.index}
    allrows["action"] = [
        "keep" if (n, i) in kept_ids else "remove" for n, i in zip(allrows["source"], allrows["orig_row"])
    ]
    key, has_key = _dedup_key_series(allrows, col, AUTHOR_COL)
    allrows["dup_group"] = pd.Series(key.where(has_key).map(hash))  # chỉ để gom nhóm
    removed_groups = allrows.loc[allrows["action"] == "remove", "dup_group"].dropna().unique()
    ev = allrows[allrows["dup_group"].isin(removed_groups)].copy()
    ev["dup_group"] = ev["dup_group"].rank(method="dense").astype(int)
    ev["excel_row"] = ev["orig_row"] + 2  # số dòng khi mở file bước trước bằng Excel
    ev = ev.sort_values(["dup_group", "action", "source", "orig_row"], ascending=True)
    for name in before:
        groups = ev.loc[(ev["source"] == name) & (ev["action"] == "remove"), "dup_group"].unique()
        out = ev[ev["dup_group"].isin(groups)]
        print(f"[{name}] {tag}: {(out['action'] == 'remove').sum()} dong bi xoa, {len(groups)} nhom trung -> {_save(out, name, tag + '_removed')}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dfs = {}
    for name in PRODUCT_FILES:
        src = IN_DIR / f"{name}_step17_stage2_add_text_norm.xlsx"
        if not src.exists():
            print(f"\n[bo qua] {name}: chua co {src} — chay scripts/run_stage2.py truoc")
            continue
        dfs[name] = pd.read_excel(src)

    steps = [
        ("step8a_stage3_drop_exact_duplicates", lambda d: {n: drop_exact_duplicates(x) for n, x in d.items()}),
        ("step21a_stage3_drop_cross_file_duplicates", drop_exact_duplicates_across_files),
    ]
    for (tag, step), col in zip(steps, (CONTENT_COL, TEXT_NORM_COL)):
        after = step(dfs)
        _save_duplicate_evidence(dfs, after, col, tag)
        for name, d in after.items():
            print(f"=== {name} [{tag}] -> {_save(d, name, tag)} ===")
            print_row_diff(dfs[name], d, label=f"{name} {tag}", excel_row_offset=2, max_list=20)
        dfs = after

    for name, df in dfs.items():
        for tag, fn, suspect_tag in PER_FILE_STEPS:
            result = fn(df)
            if suspect_tag:
                result, suspect = result
                _save(suspect, name, suspect_tag)
                print(f"[{name}] {suspect_tag}: {len(suspect)} dong can kiem duyet thu cong")
            else:
                _save_removed(df, result, name, tag)
            print(f"=== {name} [{tag}] {fn.__name__} -> {_save(result, name, tag)} ===")
            print_row_diff(df, result, label=f"{name} {tag}", excel_row_offset=2, max_list=20)
            df = result


if __name__ == "__main__":
    main()
