"""
scripts/run_stage4.py — chạy Giai đoạn 4 (nhiễu ký tự) trên đầu ra Giai đoạn 3
(data/interim/v3_filtered/<tên>_step19_stage3_filter_non_vietnamese.xlsx), mỗi bước ghi ra
data/interim/v4_char_cleaned/<tên>_<bước>_stage4_<xử lý gì>.xlsx và in diff theo số dòng Excel:

    step14 handle_inline_emoji   emoji -> nghĩa_nối_gạch_dưới + cột emojis/emoji_sentiment
                                 (+ file suspect_inline_emoji, emoji_unknown.xlsx)
    step15 remove_meaningless_special_chars    (+ file suspect_special_chars)
    step13 normalize_repeated_characters       (+ file suspect_repeated_chars)
    step16 strip_extra_whitespace (lượt 2)
    step17 add_text_norm_column   (làm mới text_norm sau khi content đã đổi)

File suspect = các dòng bị đổi, kèm cột "Nội dung đã làm sạch" để kiểm tra; dữ liệu vẫn đi
tiếp bản đã làm sạch. Kết quả cuối mỗi file: <tên>_step17_stage4_refresh_text_norm.xlsx (= v4_char_cleaned).

    python scripts/run_stage4.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from core.diff_report import print_row_diff
from transforms.stage2_normalize import add_text_norm_column, strip_extra_whitespace
from transforms.stage4_char_noise import (
    changed_rows,
    handle_inline_emoji,
    normalize_repeated_characters,
    remove_meaningless_special_chars,
    unknown_emojis,
)

IN_DIR = DATA_INTERIM_DIR / "v3_filtered"
OUT_DIR = DATA_INTERIM_DIR / "v4_char_cleaned"
# (tag, hàm, hậu tố file suspect hoặc None)
STEPS = [
    ("step14_stage4_inline_emoji", handle_inline_emoji, "step14_stage4_suspect_inline_emoji"),
    ("step15_stage4_remove_special_chars", remove_meaningless_special_chars, "step15_stage4_suspect_special_chars"),
    ("step13_stage4_normalize_repeated_chars", normalize_repeated_characters, "step13_stage4_suspect_repeated_chars"),
    ("step16_stage4_strip_whitespace", strip_extra_whitespace, None),
    ("step17_stage4_refresh_text_norm", add_text_norm_column, None),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    unknown = []
    for name in PRODUCT_FILES:
        src = IN_DIR / f"{name}_step19_stage3_filter_non_vietnamese.xlsx"
        if not src.exists():
            print(f"\n[bo qua] {name}: chua co {src} — chay scripts/run_stage3.py truoc")
            continue
        df = pd.read_excel(src)
        print(f"\n########## {name}: {len(df)} dong ##########")
        for tag, fn, suspect_tag in STEPS:
            result = fn(df)
            if fn is handle_inline_emoji:
                unknown.append(unknown_emojis(df))
            if suspect_tag:
                suspect = changed_rows(df, result)
                path = OUT_DIR / f"{name}_{suspect_tag}.xlsx"
                suspect.to_excel(path, index=False)
                print(f"[{name}] {suspect_tag}: {len(suspect)} dong can kiem tra -> {path}")
            out_path = OUT_DIR / f"{name}_{tag}.xlsx"
            result.to_excel(out_path, index=False)
            print(f"=== {name} [{tag}] {fn.__name__} -> {out_path} ===")
            print_row_diff(df, result, label=f"{name} {tag}", excel_row_offset=2, max_list=20)
            df = result
    if unknown:
        u = pd.concat(unknown).groupby(level=0).sum().sort_values(ascending=False)
        path = OUT_DIR / "emoji_unknown.xlsx"
        u.rename_axis("emoji").reset_index(name="count").to_excel(path, index=False)
        print(f"\nemoji chua co trong dictionary/emoji_meaning.txt: {len(u)} -> {path}")


if __name__ == "__main__":
    main()
