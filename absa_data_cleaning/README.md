# ABSA Data Cleaning Pipeline — Kiến trúc & Hướng xây dựng

> **Đây là bộ khung (skeleton) thư mục + interface, KHÔNG chứa logic xử lý dữ liệu thật.**
> Mọi hàm/class dưới đây chỉ có chữ ký (signature), docstring mô tả nhiệm vụ và `# TODO`.
> Mục tiêu: thống nhất kiến trúc trước khi bắt tay viết logic làm sạch dữ liệu theo
> `Taxonomy_lam_sach_du_lieu_ABSA_v2.xlsx` (4 tầng, 52 vấn đề).

## 1. Bối cảnh & phạm vi

Input: các file Excel thô trong `data/raw/` (danh sách + tên file khai báo tại
`config/settings.py::PRODUCT_FILES`, hiện gồm `ipad`, `buds`, `watch`, `pin`, `phone`,
`ao`, `quan`, `vay`, `non`, `vo`), mỗi file có schema 8 cột cố định:

```
Tác giả | Thời gian | Loại hàng (phân loại) | Tiêu chí đánh giá |
Nội dung tự do | Số sao | URL sản phẩm | Thời điểm cào
```

Phạm vi của bộ khung này = **giai đoạn làm sạch dữ liệu thô**, theo đúng 4 tầng trong
taxonomy đã thống nhất:

| Tầng | Chủ đề | Số vấn đề |
|---|---|---|
| 1 | Lỗi cấu trúc dữ liệu (Structural) | 8 |
| 2 | Chất lượng & nhiễu nội dung review (2.1 không giá trị, 2.2 nhiễu biểu diễn, 2.3 cần giữ lại) | 24 |
| 3 | Làm sạch & chuẩn hoá metadata | 12 |
| 4 | Tính nhất quán & khả năng sử dụng dữ liệu (liên file) | 8 |

Việc xây **Hierarchical Aspect Taxonomy** (Universal + Domain-specific) và các bước sau
(gán nhãn, huấn luyện mô hình...) **không** thuộc phạm vi khung này, nhưng khung có sẵn
thư mục `taxonomy/` để cắm nối tiếp mà không phải tái cấu trúc code.

## 2. Triết lý kiến trúc: OOP làm khung, FP làm lõi xử lý

Ý tưởng cốt lõi: **tách "cái gì điều phối / có trạng thái / có side-effect" (OOP) ra khỏi
"cái gì biến đổi dữ liệu" (FP)**.

- **Hướng đối tượng (OOP)** dùng cho phần *khung điều phối*, nơi cần trạng thái, vòng đời,
  kế thừa, cấu hình: `Pipeline`, `ProcessingStep`, `Reader`/`Writer`, `CleaningReport`.
  Đây là những thứ ít thay đổi và cần được chuẩn hoá hành vi (interface chung).
- **Lập trình hàm (FP)** dùng cho phần *lõi biến đổi dữ liệu*: mỗi vấn đề trong taxonomy
  (VD: "Teencode", "Review chỉ có emoji", "Rating không hợp lệ"...) được viết thành
  **một hàm thuần (pure function)** — nhận vào dữ liệu, trả về dữ liệu mới, không side-effect,
  không phụ thuộc trạng thái ngoài. Điều này giúp:
  - Dễ unit test độc lập từng vấn đề (đối chiếu với cột "Bằng chứng / Ví dụ cụ thể" trong taxonomy).
  - Dễ compose nhiều hàm nhỏ thành 1 bước xử lý lớn hơn (function composition / pipe).
  - Dễ bật/tắt hoặc thay thế 1 hàm mà không ảnh hưởng phần còn lại.

Cầu nối giữa hai thế giới: mỗi `ProcessingStep` (class OOP) **bọc** một hoặc nhiều
hàm thuần (FP) từ `transforms/`, và một `StepRegistry` (decorator) cho phép đăng ký
hàm thuần gắn với mã taxonomy (vd: `@register_step(tang=2, stt=17, name="teencode")`)
mà không cần sửa code điều phối.

## 3. Nguyên tắc "chạy từng bước một, không bắt buộc chạy hết"

- Mỗi `ProcessingStep` độc lập: có thể chạy riêng lẻ qua CLI, không phụ thuộc phải chạy
  tuần tự toàn bộ pipeline trong cùng 1 lần.
- Sau **mỗi bước xử lý**, dữ liệu được **xuất ra file** ở `data/interim/<step_id>/`
  (không ghi đè lên input) — vừa để truy vết (so sánh trước/sau phục vụ báo cáo luận văn),
  vừa để bước sau có thể đọc lại mà không cần chạy lại từ đầu.
- `Pipeline` tự động tìm **input mới nhất có sẵn** cho một step (ưu tiên output của step
  liền trước nếu đã chạy, nếu chưa thì fallback về `data/raw/`), nên có thể chạy:
  - 1 hàm xử lý đơn lẻ trên 1 file,
  - 1 tầng (VD toàn bộ Tầng 2) trên tất cả file,
  - hoặc toàn bộ 4 tầng nối tiếp — tuỳ lựa chọn ở `cli.py` / `pipeline_config.yaml`.
- Idempotent: chạy lại một step đã chạy sẽ ghi đè output của chính step đó, không ảnh
  hưởng các step khác.

## 4. Cây thư mục (sắp xếp theo kế hoạch tiền xử lý, Giai đoạn 0–7)

Thứ tự xử lý: **cấu trúc → lọc rẻ → làm sạch ký tự → chuẩn hoá từ vựng → khử trùng lặp lần cuối**
(xem `Kế hoạch tiền xử lý dữ liệu review tiếng Việt cho bài toán ABSA.md` ở thư mục gốc repo).

```
absa_data_cleaning/
├── README.md
├── cli.py                            # entry point (stub)
├── config/
│   ├── settings.py                   # đường dẫn, PRODUCT_FILES, CHECKPOINT_VERSIONS (v0_raw … v7_final)
│   └── pipeline_config.yaml          # tham số từng bước
├── core/                             # khung OOP (stub): pipeline, registry, report, ...
├── dataio/
│   ├── checkpoint.py                 # Giai đoạn 0: lưu checkpoint + log số dòng (stub)
│   └── ...                           # excel reader/writer, dictionary_loader, file_registry
├── transforms/                       # LÕI FP — 1 file / giai đoạn
│   ├── utils_text.py                 # hàm chuỗi dùng chung
│   ├── stage0_prepare.py             # GĐ0: review_id, review_raw
│   ├── stage1_structure.py           # GĐ1: lệch cột, dòng trống, ép kiểu thời gian, tách tiêu chí
│   ├── stage2_normalize.py           # GĐ2: NFC/HTML, khoảng trắng lượt 1, text_norm
│   ├── stage3_coarse_filter.py       # GĐ3: trùng chính xác, emoji-only, URL/spam, ngôn ngữ
│   ├── stage4_char_noise.py          # GĐ4: emoji xen câu, ký tự đặc biệt, lặp ký tự
│   ├── stage5_short_filter.py        # GĐ5: review <= 4 từ
│   ├── stage6_lexical.py             # GĐ6: teencode, protected tokens, khôi phục dấu, chính tả, tiếng lóng
│   └── stage7_final_dedup.py         # GĐ7: gần trùng trong/giữa file, kiểm tra cuối
├── pipelines/
│   └── pipeline_full.py              # STAGES: thứ tự bước + checkpoint (run() là stub)
├── scripts/legacy/                   # luồng chạy cũ đã dùng để sinh data/interim/*_t*.xlsx
│   ├── run_t*.py                     # chạy: python -m scripts.legacy.run_t16
│   ├── Merge_*_Checked.py            # merge kết quả kiểm duyệt (theo 'Dòng Excel gốc')
│   └── build_reviewed_t2*.py         # dựng lại chuỗi trong bộ nhớ
├── dictionary/                       # teencode, chính tả, whitelist
├── lib/                              # tài nguyên tải ngoài: vi_VN.dic (LibreOffice, GPL), ViLexNorm.csv (CC BY-NC-SA), english_10000.txt
├── data/{raw,raw_markdown,interim,processed}/
├── logs/
└── tests/
    ├── test_stage1_structure.py
    └── test_stage_text_transforms.py
```

Chạy script legacy **từ thư mục `absa_data_cleaning/`** bằng `python -m scripts.legacy.<tên>` (không chạy
trực tiếp đường dẫn file, vì các script import `config`, `transforms`, … từ thư mục gốc này).

### Ánh xạ kế hoạch → code

| GĐ | Bước kế hoạch | Hàm | Taxonomy cũ | Trạng thái |
|---|---|---|---|---|
| 0 | Gán `review_id`, giữ `review_raw` | `stage0_prepare.assign_review_id` | — | ✅ |
| 0 | Checkpoint + log | `dataio.checkpoint.save_checkpoint`, `append_step_log` | — | TODO |
| 1 | Bước 1 — lệch cột | `stage1_structure.fix_field_misalignment` | T1.1 | ✅ |
| 1 | Bước 2 — dòng trống / thiếu cột | `stage1_structure.drop_empty_rows` | T1.2+T1.3 | ✅ |
| 1 | Bước 3 — ép kiểu thời gian | `stage1_structure.fix_data_types` | T1.5 | ✅ |
| 1 | Bước 4 — tách tiêu chí | `stage1_structure.split_merged_fields` | T1.6 | ✅ |
| 2 | Unicode NFC, dấu thanh, HTML | `stage2_normalize.normalize_unicode_and_html` | — | ✅ |
| 2 | Bước 16 — khoảng trắng (lượt 1) | `stage2_normalize.strip_extra_whitespace` | T2.24 | ✅ |
| 2 | Bước 17 — `text_norm` | `stage2_normalize.add_text_norm_column` | T2.25 | ✅ |
| 3 | Bước 8a — trùng chính xác trong file | `stage3_coarse_filter.drop_exact_duplicates` | T2.15 | ✅ (khoá: nội dung + tác giả) |
| 3 | Bước 21a — trùng chính xác giữa file | `stage3_coarse_filter.drop_exact_duplicates_across_files` | — | TODO |
| 3 | Bước 5 — chỉ emoji / ký tự đặc biệt | `stage3_coarse_filter.drop_emoji_or_special_char_only_reviews` | T2.9+T2.10 | ✅ |
| 3 | Bước 7 — URL / spam (thủ công) | `stage3_coarse_filter.split_url_hotline_or_spam_reviews` | T2.13+T2.14 | ✅ |
| 3 | Bước 19 — không phải tiếng Việt | `stage3_coarse_filter.split_non_vietnamese_reviews` | T2.27 | TODO |
| 4 | Bước 14 — emoji xen câu | `stage4_char_noise.handle_inline_emoji` | T2.22 | TODO |
| 4 | Bước 15 — ký tự đặc biệt | `stage4_char_noise.remove_meaningless_special_chars` | T2.23 | TODO |
| 4 | Bước 13 — lặp ký tự | `stage4_char_noise.normalize_repeated_characters` | T2.21 | TODO |
| 4 | Bước 16 — khoảng trắng (lượt 2) | `stage2_normalize.strip_extra_whitespace` | T2.24 | ✅ |
| 5 | Bước 6 — review <= 4 từ (thủ công) | `stage5_short_filter.split_short_reviews` | T2.11+T2.12 | ✅ (`scripts/run_stage5.py`) |
| 6 | Kiểm duyệt cấp token (9+10, 18, 12, 11) — chỉ liệt kê + gợi ý bỏ phiếu từ luật, ViLexNorm, model bmd1905, model dấu XLM-R; áp gợi ý đồng thuận (>= 2 nguồn) vào cột mới `Nội dung chuẩn hoá` / `<tiêu chí> (chuẩn hoá)`, không ghi đè cột gốc (`scripts/run_stage6.py`) | `stage6_lexical.list_nonstandard_token_reviews`, `annotate_suggestions`, `token_frequency_table` | — | ✅ |
| 6 | Bước 9+10 — teencode, viết tắt | `stage6_lexical.normalize_teencode_and_abbreviations`, `split_suspect_teencode_reviews` | T2.17+T2.18 | ✅ |
| 6 | Bước 18 — tiếng Anh / từ mượn | `stage6_lexical.mark_protected_tokens` | T2.26 | TODO |
| 6 | Bước 12 — khôi phục dấu | `stage6_lexical.restore_diacritics` | T2.20 | TODO |
| 6 | Bước 11 — chính tả | `stage6_lexical.fix_spelling_errors`, `split_spelling_error_reviews` | T2.19 | ✅ |
| 6 | Bước 20 — tiếng lóng cảm xúc | `stage6_lexical.normalize_emotional_slang` | T2.31 | TODO |
| 7 | Bước 8b — gần trùng trong file (thủ công) | `stage7_final_dedup.split_near_duplicate_reviews` | T2.16 | ✅ |
| 7 | Bước 21b — gần trùng giữa file | `stage7_final_dedup.split_cross_file_near_duplicates` | — | ✅ (`scripts/run_stage7.py`) |
| 7 | Kiểm tra cuối | `stage7_final_dedup.final_check` | — | ✅ (`scripts/run_stage7.py`) |

Đã xoá (không có trong kế hoạch, chưa có code): toàn bộ stub Tầng 3 (metadata), Tầng 4, và các stub T1.4, T1.7,
T1.8, T2.28–T2.30, T2.32.

## 5. Vòng đời một bước xử lý (step)

1. `cli.py` nhận lệnh (VD: `python cli.py run --step teencode`).
2. `Pipeline` tra `StepRegistry` tìm `ProcessingStep` tương ứng.
3. `Pipeline` xác định input: output gần nhất của step trước đó nếu có, nếu không thì
   `data/raw/`.
4. `Reader` (từ `dataio/`) đọc dữ liệu → nạp vào cấu trúc `ReviewRecord` (hoặc DataFrame,
   xem mục 7).
5. `ProcessingStep.run()` gọi (các) hàm thuần trong `transforms/` để biến đổi dữ liệu.
   Hàm thuần **không** đọc/ghi file, không log — chỉ nhận dữ liệu vào, trả dữ liệu ra.
6. `CleaningReport` ghi lại số liệu thay đổi (số dòng bị sửa/xoá, ví dụ trước–sau...).
7. `Writer` xuất dữ liệu đã xử lý ra `data/interim/<step_id>/<product>.xlsx`.
8. Report được ghi ra `logs/<step_id>_<timestamp>.json`.

## 6. Quy ước đặt mã cho step (gắn với taxonomy)

Mỗi step/hàm transform mang mã `T<tầng>.<stt>` trùng với cột **STT** trong file taxonomy,
để khi viết luận văn có thể trích dẫn trực tiếp "áp dụng xử lý cho vấn đề T2.17 — Teencode".
`registry.py` lưu mapping `mã taxonomy -> hàm xử lý -> tên step`, phục vụ:

- Truy vết vấn đề nào đã có code xử lý, vấn đề nào còn thiếu (đối chiếu 52 mục).
- Tự sinh bảng "Đề xuất xử lý" → "Trạng thái triển khai" cho báo cáo.

## 7. Cấu trúc dữ liệu nội bộ

Chưa quyết định cứng giữa hai lựa chọn — để ngỏ ở `core/schema.py`:

- **Pandas DataFrame** (khuyến nghị cho giai đoạn làm sạch hàng loạt, dễ thao tác vector hoá,
  dễ export Excel) — hàm transform nhận/trả `pd.DataFrame`.
- **`ReviewRecord` dataclass** (dùng khi cần xử lý logic phức tạp theo từng dòng, hoặc khi
  sang giai đoạn gán nhãn/aspect sau này cần đối tượng có method riêng).

Gợi ý: dùng DataFrame làm đơn vị trao đổi giữa các step (hiệu năng, tương thích Excel I/O),
nhưng cho phép từng hàm trong `transforms/` áp dụng logic theo dòng qua `apply`/`map` khi cần —
đây chính là chỗ FP thể hiện rõ nhất (hàm thuần áp lên từng phần tử).

## 8. Hướng mở rộng sau này

- `taxonomy/aspect_taxonomy.py`: khi bắt đầu xây Hierarchical Aspect Taxonomy, định nghĩa
  cấu trúc cây (Universal aspects + Domain-specific theo từng ngành hàng) tại đây, không
  đụng vào `transforms/`.
- Thêm ngành hàng mới (kế hoạch crawl thêm 2–3 ngành): chỉ cần thêm entry vào
  `dataio/file_registry.py` + `config/settings.py`, toàn bộ step/pipeline dùng lại nguyên vẹn.
- Thêm vấn đề làm sạch mới phát sinh: thêm 1 hàm thuần vào đúng file `tang*_*.py`, đăng ký
  bằng `@register_step`, không cần sửa `core/`.
- Giai đoạn LLM-assisted labeling sau này có thể tái dùng `core/pipeline.py` và
  `core/step_base.py` theo cùng triết lý (step độc lập, có thể chạy riêng, export sau mỗi bước).

## 9. Việc cần làm tiếp theo (chưa làm trong bản này)

- [ ] Cài đặt logic thật cho 52 hàm trong `transforms/` theo cột "Đề xuất xử lý" của taxonomy.
- [ ] Viết `pipeline_config.yaml` cụ thể (bật/tắt, tham số ngưỡng near-duplicate, v.v.).
- [ ] Viết test đối chiếu case thật trong từng file (cột "Bằng chứng / Ví dụ cụ thể").
- [ ] Quyết định DataFrame vs dataclass sau khi thử nghiệm hiệu năng trên ~2000 dòng/file.
