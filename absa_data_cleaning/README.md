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

## 4. Cây thư mục

```
absa_data_cleaning/
├── README.md                         # (file này) kiến trúc & hướng xây dựng
├── requirements.txt
├── cli.py                            # entry point: chạy 1 step / 1 tầng / toàn bộ
│
├── config/
│   ├── settings.py                   # đường dẫn, danh sách sản phẩm (PRODUCT_FILES), schema 8 cột chuẩn
│   └── pipeline_config.yaml          # khai báo step nào bật/tắt, tham số từng step
│
├── core/                             # === KHUNG OOP ===
│   ├── schema.py                     # ReviewRecord: mô tả 1 dòng dữ liệu chuẩn (8 cột)
│   ├── io_base.py                    # abstract class Reader / Writer
│   ├── step_base.py                  # abstract class ProcessingStep (interface run())
│   ├── pipeline.py                   # class Pipeline: điều phối, quản lý input/output từng step
│   ├── registry.py                   # StepRegistry + decorator @register_step
│   └── report.py                     # class CleaningReport: log số liệu trước/sau mỗi step
│
├── dataio/                           # đọc / ghi file
│   ├── excel_reader.py               # ExcelReader(Reader): đọc .xlsx theo schema 8 cột
│   ├── excel_writer.py               # ExcelWriter/CsvWriter(Writer): xuất file sau mỗi step
│   └── file_registry.py              # danh sách file input + quy ước đặt tên output
│
├── transforms/                       # === LÕI FP: mỗi hàm = 1 vấn đề trong taxonomy ===
│   ├── utils_text.py                 # hàm dùng chung (regex, chuẩn hoá unicode, v.v.)
│   ├── tang1_structural.py           # 8 hàm — Tầng 1: lỗi cấu trúc
│   ├── tang2_content_quality.py      # 24 hàm — Tầng 2: chất lượng & nhiễu nội dung
│   ├── tang3_metadata.py             # 12 hàm — Tầng 3: chuẩn hoá metadata
│   └── tang4_consistency.py          # 8 hàm — Tầng 4: nhất quán liên file
│
├── taxonomy/                         # === CHỖ DÀNH SẴN CHO GIAI ĐOẠN SAU ===
│   ├── aspect_taxonomy.py            # (placeholder) cây Aspect Taxonomy Universal + Domain
│   └── taxonomy_loader.py            # (placeholder) đọc file taxonomy nghiệp vụ
│
├── pipelines/                        # lắp ráp step theo từng tầng / toàn bộ
│   ├── pipeline_tang1.py
│   ├── pipeline_tang2.py
│   ├── pipeline_tang3.py
│   ├── pipeline_tang4.py
│   └── pipeline_full.py              # nối 4 tầng (tuỳ chọn — không bắt buộc dùng)
│
├── data/
│   ├── raw/                          # copy file xlsx gốc vào đây (tên file khai báo ở PRODUCT_FILES)
│   ├── interim/                      # output trung gian, 1 thư mục con / step
│   └── processed/                    # output cuối cùng, sẵn sàng cho bước xây taxonomy khía cạnh
│
├── logs/                             # log chạy + report json từng lần chạy
│
└── tests/                            # unit test cho từng hàm transform
    ├── test_tang1_structural.py
    ├── test_tang2_content_quality.py
    ├── test_tang3_metadata.py
    └── test_tang4_consistency.py
```

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
