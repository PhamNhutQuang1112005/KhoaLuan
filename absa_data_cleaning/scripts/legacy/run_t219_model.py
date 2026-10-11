"""
run_t219_model.py — T2.19 sửa lỗi chính tả bằng mô hình
`bmd1905/vietnamese-correction-v2` (HuggingFace, MBart seq2seq ~396M tham số),
thay cho bộ luật/từ điển của run_t219.py (KHÔNG sửa/xoá file đó).

Đầu vào: kết quả T1.1 -> T2.18 tính lại trong bộ nhớ (giống run_t219.py). Đầu
ra: data/interim/Spelling_Correction_Model.xlsx — chỉ gồm dòng mà mô hình sửa
được >= 1 từ, các cột:
  - 'Sản phẩm', 'Dòng Excel gốc' : để truy vết về dòng trong file sản phẩm.
  - 'Nội dung tự do'      : văn gốc (bản sai chính tả).
  - 'Nội dung sau xử lý'  : văn gốc đã áp các từ được mô hình sửa.
  - 'Từ đã chỉnh'         : 'từ sai -> từ đúng; ...'.

Mô hình viết lại CẢ CÂU (thêm dấu câu, viết hoa, bỏ emoji, nối các dòng...)
và đôi khi đổi sai. Vì vậy 'Nội dung sau xử lý' KHÔNG phải nguyên văn đầu ra
của mô hình mà là văn gốc + chỉ các từ bị mô hình thay (xem
`transforms.utils_text.apply_model_corrections`): dấu câu/emoji/xuống dòng/
hoa-thường giữ nguyên để không lấn sang T2.22-T2.25. Mô hình cũng tự thêm dấu
cho từ thiếu dấu ('kiem' -> 'Kiểm') — phần nào của T2.20.

Chạy CPU: ~1.4 giây/review nếu không lượng tử hoá (>4 giờ cho toàn bộ dữ liệu).
Mặc định dùng lượng tử hoá int8 + batch theo độ dài + bỏ trùng câu; kết quả
từng câu ghi dần vào data/interim/spelling_model_cache.jsonl nên chạy lại sau
khi bị ngắt sẽ tiếp tục từ chỗ dở.

    pip install torch transformers sentencepiece
    python -m scripts.legacy.run_t219_model                 # toàn bộ
    python -m scripts.legacy.run_t219_model --sample 200    # chạy thử trên 200 review ngẫu nhiên
    python -m scripts.legacy.run_t219_model --no-quantize   # chính xác hơn, chậm hơn
"""

import argparse
import json
import re
import time

import pandas as pd

from config.settings import DATA_INTERIM_DIR, PRODUCT_FILES
from scripts.legacy.build_reviewed_t214 import PRODUCT_COL, SOURCE_ROW_COL
from scripts.legacy.build_reviewed_t218 import build_reviewed_t218_dataframe
from transforms.stage1_structure import CONTENT_COL
from transforms.stage6_lexical import CORRECTED_CONTENT_COL
from transforms.utils_text import apply_model_corrections

MODEL_NAME = "bmd1905/vietnamese-correction-v2"
CHANGES_COL = "Từ đã chỉnh"
OUT_PATH = DATA_INTERIM_DIR / "Spelling_Correction_Model.xlsx"
CACHE_PATH = DATA_INTERIM_DIR / "spelling_model_cache.jsonl"
CHUNK_MAX_WORDS = 50  # câu dài bị mô hình cắt cụt/bịa -> chia nhỏ theo câu/dòng
BATCH_SIZE = 16
_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def split_chunks(text: str, max_words: int = CHUNK_MAX_WORDS) -> list[str]:
    """Cắt `text` thành các đoạn liên tiếp (nối lại đúng bằng `text`), mỗi đoạn
    gồm các câu/dòng gộp cho tới khi vượt `max_words` từ."""
    cuts = [0] + [m.end() for m in _BOUNDARY_RE.finditer(text)] + [len(text)]
    chunks, current = [], ""
    for a, b in zip(cuts, cuts[1:]):
        piece = text[a:b]
        if current and len((current + piece).split()) > max_words:
            chunks.append(current)
            current = ""
        current += piece
    if current:
        chunks.append(current)
    return chunks


def load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    with open(CACHE_PATH, encoding="utf-8") as f:
        return {r["in"]: r["out"] for r in map(json.loads, f)}


def run_model(chunks: list[str], quantize: bool) -> dict:
    """{đoạn: đầu ra mô hình} cho mọi đoạn trong `chunks` (dùng/ghi cache)."""
    cache = load_cache()
    todo = sorted({c for c in chunks if c not in cache}, key=len)
    print(f"{len(chunks)} doan, {len(cache)} da co trong cache, {len(todo)} doan can chay mo hinh", flush=True)
    if not todo:
        return cache

    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    torch.set_num_threads(torch.get_num_threads())
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).eval()
    if quantize:
        model = torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)

    start = time.time()
    with open(CACHE_PATH, "a", encoding="utf-8") as cache_file:
        for i in range(0, len(todo), BATCH_SIZE):
            batch = todo[i:i + BATCH_SIZE]
            encoded = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=256)
            with torch.no_grad():
                generated = model.generate(**encoded, max_length=256, num_beams=1)
            for src, out in zip(batch, tokenizer.batch_decode(generated, skip_special_tokens=True)):
                cache[src] = out
                cache_file.write(json.dumps({"in": src, "out": out}, ensure_ascii=False) + "\n")
            cache_file.flush()
            done = i + len(batch)
            if (i // BATCH_SIZE) % 10 == 0 or done == len(todo):
                elapsed = time.time() - start
                print(f"  {done}/{len(todo)} doan, {elapsed / 60:.1f} phut, con ~{elapsed / done * (len(todo) - done) / 60:.1f} phut", flush=True)
    return cache


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=0, help="chi chay N review ngau nhien (chay thu)")
    parser.add_argument("--no-quantize", action="store_true")
    args = parser.parse_args()

    frames = []
    for name in PRODUCT_FILES:
        df = build_reviewed_t218_dataframe(name)
        df = df.loc[df[CONTENT_COL].notna() & (df[CONTENT_COL].astype(str).str.strip() != ""), [CONTENT_COL]]
        df.insert(0, SOURCE_ROW_COL, df.index + 2)
        df.insert(0, PRODUCT_COL, name)
        frames.append(df)
    reviews = pd.concat(frames, ignore_index=True)
    if args.sample:
        reviews = reviews.sample(args.sample, random_state=0).sort_index()

    texts = reviews[CONTENT_COL].astype(str).tolist()
    chunks_per_text = [split_chunks(t) for t in texts]
    outputs = run_model([c for chunks in chunks_per_text for c in chunks], quantize=not args.no_quantize)

    corrected, details = [], []
    for chunks in chunks_per_text:
        parts, changes = [], []
        for chunk in chunks:
            fixed, chunk_changes = apply_model_corrections(chunk, outputs[chunk])
            parts.append(fixed)
            changes += chunk_changes
        corrected.append("".join(parts))
        details.append("; ".join(f"{a} -> {b}" for a, b in changes))

    reviews[CORRECTED_CONTENT_COL] = corrected
    reviews[CHANGES_COL] = details
    result = reviews.loc[reviews[CHANGES_COL] != ""].reset_index(drop=True)
    result.to_excel(OUT_PATH, index=False)
    print(f"=== {OUT_PATH} ({len(result)}/{len(reviews)} review co tu duoc mo hinh sua) ===")


if __name__ == "__main__":
    main()
