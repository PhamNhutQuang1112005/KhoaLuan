"""
scripts/run_stage6.py — Giai đoạn 6 (chuẩn hoá từ vựng): liệt kê token nghi vấn rồi ÁP gợi ý vào cột
mới (không ghi đè cột gốc): đọc đầu ra Giai đoạn 5
(data/interim/v5_length_filtered/<tên>_step6_stage5_filter_short_reviews.xlsx),
liệt kê token không phải tiếng Việt chuẩn trong 'Nội dung tự do' (teencode/viết tắt, ngoại lai,
tiếng Anh, thiếu/sai dấu, lặp ký tự, sai chính tả, lẫn chữ số, âm tiết lạ, ngoài từ điển — xem
transforms.stage6_lexical.classify_token) và ghi ra data/interim/v6_lexical/:

    <tên>_stage6_suspect_tokens.xlsx   1 dòng / câu có token nghi vấn (+ cột Dòng Excel gốc,
                                       Token nghi vấn, Chi tiết token)
    stage6_token_frequency.xlsx        1 dòng / token, mọi file gộp lại, sắp theo số câu

Áp dụng: token có gợi ý đồng thuận (>= --min-votes nguồn cùng ý, mặc định 2; theo ngữ cảnh từng câu,
bỏ 'giữ nguyên') được thay vào CỘT MỚI, cột gốc giữ nguyên, ghi ra
    <tên>_stage6_corrected.xlsx        toàn bộ dòng + 'Nội dung chuẩn hoá' + 'Token đã thay' sau 'Nội dung tự do',
                                       và '<tiêu chí> (chuẩn hoá)' sau mỗi cột tiêu chí do T1.6 tách ra
Các cột tiêu chí được quét như nội dung (theo giá trị duy nhất, cùng 4 nguồn, chạy cả model):
    stage6_criteria_suspect_values.xlsx  1 dòng / (file, cột tiêu chí, giá trị) có token nghi vấn

Gợi ý sửa cho mỗi token = BỎ PHIẾU giữa 4 nguồn (stage6_lexical.vote_suggestion):
  - luật       : từ điển dictionary/ + luật âm tiết + thống kê dấu trên toàn dữ liệu.
  - ViLexNorm  : lib/ViLexNorm.csv, gợi ý không theo ngữ cảnh.
  - bmd1905    : model sửa chính tả bmd1905/vietnamese-correction-v2 (seq2seq), chỉ giữ từ model
                 thay (utils_text.apply_model_corrections — bỏ từ < 3 chữ cái và phép thay khác
                 hẳn từ gốc), nên chỉ chạy cho token >= 3 chữ cái thuộc BMD_KINDS.
  - model dấu  : peterhung/vietnamese-accent-marker-xlm-roberta (token classification, khôi
                 phục dấu theo ngữ cảnh), chỉ chạy cho token 'thiếu/sai dấu'; giữ nguyên dấu
                 thì bỏ phiếu 'giữ nguyên'.
Mỗi model chỉ chạy trên cửa sổ ±MODEL_WINDOW từ quanh token cần (cửa sổ chồng nhau được gộp,
trùng nhau chỉ chạy 1 lần), lần lượt từng model để không hết RAM (2 model cùng lúc cần > 8 GB).
Kết quả cache ở v6_lexical/stage6_model_cache.jsonl, stage6_accent_cache.jsonl nên ngắt giữa
chừng thì chạy lại sẽ tiếp tục. Đo trên CPU int8: bmd1905 ~16 phút, model dấu ~0.2 giây/cửa sổ
(chưa batch).

    pip install torch transformers sentencepiece
    python scripts/run_stage6.py                 # đủ 4 nguồn
    python scripts/run_stage6.py --no-model      # chỉ luật + ViLexNorm (vài giây)
    python scripts/run_stage6.py --no-quantize   # model chính xác hơn, chậm hơn
"""

import argparse
import gc
import json
import re
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")  # console Windows (cp1258) không in được 'Loại', 'Số câu'

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from transforms.stage1_structure import CONTENT_COL
from transforms.stage6_lexical import (
    _TOKEN_RE,
    CLEANED_CONTENT_COL,
    CLEANED_SUFFIX,
    DIACRITIC_KIND,
    KEEP,
    MIN_VOTES,
    REPLACED_TOKENS_COL,
    SOURCE_ACCENT,
    SOURCE_BMD,
    SUSPECT_TOKENS_COL,
    TOKEN_DETAIL_COL,
    annotate_suggestions,
    apply_replacements,
    build_token_stats,
    classify_token,
    criteria_columns,
    list_nonstandard_token_reviews,
    format_replaced,
    row_replacements,
    token_frequency_table,
)
from transforms.utils_text import apply_model_corrections

IN_DIR = DATA_INTERIM_DIR / "v5_length_filtered"
OUT_DIR = DATA_INTERIM_DIR / "v6_lexical"
MODEL_CACHE_PATH = OUT_DIR / "stage6_model_cache.jsonl"
ACCENT_CACHE_PATH = OUT_DIR / "stage6_accent_cache.jsonl"
OLD_MODEL_CACHE_PATH = DATA_INTERIM_DIR / "Old" / "spelling_model_cache.jsonl"  # cache của run_t219_model
ACCENT_MODEL = "peterhung/vietnamese-accent-marker-xlm-roberta"
BMD_KINDS = {"ngoài từ điển", "âm tiết lạ (ngoài vi_VN.dic)", DIACRITIC_KIND, "sai chính tả", "lặp ký tự"}
SHORT_VALUE_WORDS = 3  # gia tri tieu chi ngan: chi can 1 tu khoi phuc dau
MODEL_WINDOW = 5  # số từ mỗi bên token; nhỏ hơn thì nhanh hơn nhưng model ít ngữ cảnh hơn
MODEL_BATCH_SIZE = 32
_WORD_RE = re.compile(r"\S+")


def model_windows(text: str, needed: set) -> list[str]:
    """Các đoạn nguyên văn của `text` gồm ±MODEL_WINDOW từ quanh mỗi từ chứa
    token trong `needed` (đoạn chồng/liền nhau được gộp)."""
    words = list(_WORD_RE.finditer(text))
    spans: list = []
    for i, w in enumerate(words):
        if not any(t.lower() in needed for t in _TOKEN_RE.findall(w.group())):
            continue
        a, b = max(0, i - MODEL_WINDOW), min(len(words) - 1, i + MODEL_WINDOW)
        if spans and a <= spans[-1][1] + 1:
            spans[-1][1] = b
        else:
            spans.append([a, b])
    return [text[words[a].start():words[b].end()] for a, b in spans]


def _windows_for(suspects: dict, stats: dict, wanted) -> tuple[dict, dict]:
    """({tên: [set token cần cho từng dòng]}, {tên: [list cửa sổ cho từng dòng]}),
    `wanted(token, loại)` quyết định token nào cần model."""
    kinds: dict = {}
    needed, windows = {}, {}
    for name, df in suspects.items():
        needed[name], windows[name] = [], []
        for text, tokens in zip(df[CONTENT_COL], df[SUSPECT_TOKENS_COL]):
            need = set()
            for t in tokens.split(", "):
                if t not in kinds:
                    kinds[t] = classify_token(t, stats)[0]
                if wanted(t, kinds[t]):
                    need.add(t)
            needed[name].append(need)
            windows[name].append(model_windows(str(text), need))
    return needed, windows


def bmd_context(suspects: dict, stats: dict, quantize: bool) -> dict:
    """{tên: [ {token: từ bmd1905 thay} cho từng dòng ]}."""
    from scripts.legacy import run_t219_model as model

    model.CACHE_PATH, model.BATCH_SIZE = MODEL_CACHE_PATH, MODEL_BATCH_SIZE
    if not MODEL_CACHE_PATH.exists() and OLD_MODEL_CACHE_PATH.exists():
        shutil.copy(OLD_MODEL_CACHE_PATH, MODEL_CACHE_PATH)  # đoạn văn trùng thì khỏi chạy lại
    needed, windows = _windows_for(suspects, stats, lambda t, kind: len(t) >= 3 and t.isalpha() and kind in BMD_KINDS)
    print(f"\n[{SOURCE_BMD}]")
    outputs = model.run_model([w for rows in windows.values() for ws in rows for w in ws], quantize)
    result = {}
    for name in suspects:
        result[name] = []
        for need, ws in zip(needed[name], windows[name]):
            pairs = [pair for w in ws for pair in apply_model_corrections(w, outputs[w])[1]]
            result[name].append({old.lower(): new.lower() for old, new in pairs if old.lower() in need})
    return result


def _apply_accent_tags(word: str, tag_ids: list, labels: list) -> str:
    """Theo model card: áp tag đầu tiên ('raw-vowel', vd 'a-ắ') làm đổi được từ."""
    for tag_id in dict.fromkeys(tag_ids):
        raw, vowel = labels[tag_id].split("-")
        if raw and raw in word:
            return word.replace(raw, vowel)
    return word


def run_accent_model(windows: list, quantize: bool) -> dict:
    """{cửa sổ: [từ đã thêm dấu, căn 1-1 với cửa sổ.split()]} (dùng/ghi cache)."""
    cache = {}
    if ACCENT_CACHE_PATH.exists():
        with open(ACCENT_CACHE_PATH, encoding="utf-8") as f:
            cache = {r["in"]: r["out"] for r in map(json.loads, f)}
    todo = sorted({w for w in windows if w not in cache}, key=len)
    print(f"{len(set(windows))} doan, {len(todo)} doan can chay mo hinh", flush=True)
    if not todo:
        return cache

    import torch
    from huggingface_hub import hf_hub_download
    from transformers import AutoModelForTokenClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(ACCENT_MODEL, add_prefix_space=True)
    model = AutoModelForTokenClassification.from_pretrained(ACCENT_MODEL).eval()
    if quantize:
        model = torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
    with open(hf_hub_download(ACCENT_MODEL, "selected_tags_names.txt"), encoding="utf-8") as f:
        labels = [line.strip() for line in f if line.strip()]

    start = time.time()
    with open(ACCENT_CACHE_PATH, "a", encoding="utf-8") as cache_file:
        for i in range(0, len(todo), MODEL_BATCH_SIZE):
            batch = todo[i:i + MODEL_BATCH_SIZE]
            words = [w.split() for w in batch]
            encoded = tokenizer(words, is_split_into_words=True, truncation=True, padding=True, return_tensors="pt")
            with torch.no_grad():
                predicted = model(**encoded).logits.argmax(-1).tolist()
            for b, (src, ws) in enumerate(zip(batch, words)):
                tags: dict = {}
                for j, word_id in enumerate(encoded.word_ids(b)):
                    if word_id is not None:
                        tags.setdefault(word_id, []).append(predicted[b][j])
                cache[src] = [_apply_accent_tags(w, tags.get(k, []), labels) for k, w in enumerate(ws)]
                cache_file.write(json.dumps({"in": src, "out": cache[src]}, ensure_ascii=False) + "\n")
            cache_file.flush()
            done = i + len(batch)
            if (i // MODEL_BATCH_SIZE) % 10 == 0 or done == len(todo):
                elapsed = time.time() - start
                print(f"  {done}/{len(todo)} doan, {elapsed / 60:.1f} phut, con ~{elapsed / done * (len(todo) - done) / 60:.1f} phut", flush=True)
    return cache


def _accented_token(token: str, window: str, accented_words: list) -> str:
    """Dạng model dấu chọn cho `token` (lần xuất hiện đầu trong `window`):
    KEEP nếu không đổi, '' nếu không căn được."""
    for word, accented in zip(window.split(), accented_words):
        src = [t.lower() for t in _TOKEN_RE.findall(word)]
        if token in src:
            dst = [t.lower() for t in _TOKEN_RE.findall(accented)]
            if len(dst) != len(src):
                return ""
            new = dst[src.index(token)]
            return KEEP if new == token else new
    return ""


def accent_context(suspects: dict, stats: dict, quantize: bool) -> dict:
    """{tên: [ {token: dạng model dấu chọn / KEEP} cho từng dòng ]} cho token 'thiếu/sai dấu'."""
    needed, windows = _windows_for(suspects, stats, lambda t, kind: kind == DIACRITIC_KIND)
    print(f"\n[{SOURCE_ACCENT}]")
    outputs = run_accent_model([w for rows in windows.values() for ws in rows for w in ws], quantize)
    result = {}
    for name in suspects:
        result[name] = []
        for need, ws in zip(needed[name], windows[name]):
            row = {}
            for t in need:
                row[t] = next((s for w in ws if (s := _accented_token(t, w, outputs[w]))), "")
            result[name].append(row)
    return result


def apply_corrections(frames: dict, suspects: dict, crit_suspects: dict, stats: dict, contexts: dict, min_votes: int) -> None:
    """Ghi <tên>_stage6_corrected.xlsx (cột mới, cột gốc giữ nguyên) và stage6_criteria_suspect_values.xlsx."""
    crit_rows, changes = [], Counter()
    for name, df in frames.items():
        out = df.copy()
        suspect = suspects[name]
        new, detail = df[CONTENT_COL].copy(), pd.Series("", index=df.index)
        for idx, text, repl in zip(suspect.index, suspect[CONTENT_COL], row_replacements(suspect, stats, contexts[name], min_votes)):
            new[idx], applied = apply_replacements(str(text), repl)
            detail[idx] = format_replaced(applied)
            changes.update(detail[idx].split("; ") if detail[idx] else [])
        pos = out.columns.get_loc(CONTENT_COL) + 1
        out.insert(pos, CLEANED_CONTENT_COL, new)
        out.insert(pos + 1, REPLACED_TOKENS_COL, detail)
        print(f"[{name}] {int((new != df[CONTENT_COL]).sum())}/{len(df)} cau co token duoc thay")

        for col in criteria_columns(df):
            key, mapping = f"{name}::{col}", {}
            found = crit_suspects.get(key)
            if found is not None:
                counts = df[col].astype(str).value_counts()
                strict = row_replacements(found, stats, contexts[key], min_votes)
                lenient = row_replacements(found, stats, contexts[key], min_votes, min_restorations=1)
                for text, tokens, info, strict_r, lenient_r in zip(
                    found[CONTENT_COL], found[SUSPECT_TOKENS_COL], found[TOKEN_DETAIL_COL], strict, lenient
                ):
                    repl = lenient_r if len(text.split()) <= SHORT_VALUE_WORDS else strict_r  # gia tri ngan: cot da cho ngu canh
                    mapping[text], applied = apply_replacements(text, repl)
                    crit_rows.append({"File": name, "Cột tiêu chí": col, "Giá trị": text, "Số dòng": counts[text],
                                      SUSPECT_TOKENS_COL: tokens, TOKEN_DETAIL_COL: info,
                                      "Giá trị chuẩn hoá": mapping[text], REPLACED_TOKENS_COL: format_replaced(applied)})
                    changes.update(f"{c} (tiêu chí)" for c in crit_rows[-1][REPLACED_TOKENS_COL].split("; ") if c)
            out.insert(out.columns.get_loc(col) + 1, col + CLEANED_SUFFIX, df[col].map(lambda v: mapping.get(str(v), v) if pd.notna(v) else v))
        path = OUT_DIR / f"{name}_stage6_corrected.xlsx"
        out.to_excel(path, index=False)
        print(f"[{name}] -> {path}")

    crit = pd.DataFrame(crit_rows).sort_values("Số dòng", ascending=False, ignore_index=True)
    path = OUT_DIR / "stage6_criteria_suspect_values.xlsx"
    crit.to_excel(path, index=False)
    print(f"\n{len(crit)} gia tri tieu chi co token nghi van -> {path}")
    print("Phep thay nhieu nhat:", changes.most_common(30))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-model", action="store_true", help="khong chay model bmd1905 / model dau")
    parser.add_argument("--no-quantize", action="store_true")
    parser.add_argument("--min-votes", type=int, default=MIN_VOTES, help="so nguon toi thieu cung goi y de thay token")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frames = {}
    for name in PRODUCT_FILES:
        src = IN_DIR / f"{name}_step6_stage5_filter_short_reviews.xlsx"
        if not src.exists():
            print(f"[bo qua] {name}: chua co {src} — chay scripts/run_stage5.py truoc")
            continue
        frames[name] = pd.read_excel(src)

    stats = build_token_stats(pd.concat([df[CONTENT_COL] for df in frames.values()]).dropna())
    suspects = {name: list_nonstandard_token_reviews(df, stats) for name, df in frames.items()}
    # cot tieu chi: quet theo gia tri duy nhat, moi (file, cot) la 1 "file" de dung chung code model
    crit_suspects = {}
    for name, df in frames.items():
        for col in criteria_columns(df):
            values = pd.DataFrame({CONTENT_COL: df[col].dropna().astype(str).unique()})
            found = list_nonstandard_token_reviews(values, stats)
            if len(found):
                crit_suspects[f"{name}::{col}"] = found
    suspects.update(crit_suspects)
    contexts: dict = {name: {} for name in suspects}
    if not args.no_model:
        for source, run in ((SOURCE_BMD, bmd_context), (SOURCE_ACCENT, accent_context)):
            for name, rows in run(suspects, stats, quantize=not args.no_quantize).items():
                contexts[name][source] = rows
            gc.collect()  # giải phóng model trước khi nạp model sau
    suspects = {name: annotate_suggestions(df, stats, contexts[name]) for name, df in suspects.items()}
    crit_suspects = {key: suspects.pop(key) for key in crit_suspects}

    print()
    for name, suspect in suspects.items():
        path = OUT_DIR / f"{name}_stage6_suspect_tokens.xlsx"
        try:
            suspect.to_excel(path, index=False)
        except PermissionError:  # dang mo trong Excel
            print(f"[{name}] CANH BAO: {path} dang mo trong Excel, bo qua file nay — dong file roi chay lai")
            continue
        print(f"[{name}] {len(suspect)}/{len(frames[name])} cau co token nghi van -> {path}")

    apply_corrections(frames, suspects, crit_suspects, stats, contexts, args.min_votes)

    freq = token_frequency_table(suspects, stats, contexts)
    path = OUT_DIR / "stage6_token_frequency.xlsx"
    freq.to_excel(path, index=False)
    print(f"\n{len(freq)} token nghi van -> {path}")
    print(freq.groupby("Loại")["Số câu"].agg(["count", "sum"]).to_string())


if __name__ == "__main__":
    main()
