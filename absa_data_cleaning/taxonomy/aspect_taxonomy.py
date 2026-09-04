"""
taxonomy/aspect_taxonomy.py
=============================
PLACEHOLDER — chưa triển khai trong giai đoạn làm sạch dữ liệu.

Theo kế hoạch luận văn (T8, tuần 3-4): sau khi có Clean dataset, bước tiếp theo
là xây "Hierarchical Aspect Taxonomy (Universal + Domain-specific)".

File này chỉ giữ chỗ để khi bắt đầu bước đó, không phải tạo lại cấu trúc thư mục.
Gợi ý hướng thiết kế (chưa triển khai):

- Universal aspects: khía cạnh chung cho mọi ngành hàng (VD: Giá cả, Vận chuyển,
  Đóng gói, Dịch vụ người bán, Chất lượng chung).
- Domain-specific aspects: khía cạnh riêng theo từng ngành hàng trong số 5 ngành
  hiện có (điện thoại, tai nghe, đồng hồ, pin sạc, iPad) — VD điện thoại có
  "Camera", "Hiệu năng", "Pin"; tai nghe có "Chống ồn", "Kết nối Bluetooth".
- Cấu trúc cây gợi ý: dùng dataclass lồng nhau (Aspect có children: list[Aspect])
  tương tự tinh thần ReviewRecord ở core/schema.py, để tận dụng lại pattern OOP
  đã thống nhất trong bộ khung này.
- Việc gán nhãn khía cạnh cho từng review (bước sau clean) nên là step riêng,
  KHÔNG gộp vào pipeline làm sạch hiện tại — giữ ranh giới rõ giữa "làm sạch dữ
  liệu thô" và "gán nhãn theo taxonomy".

TODO (khi tới giai đoạn này): định nghĩa class Aspect, load taxonomy từ file
nghiệp vụ (xem taxonomy_loader.py), xây cơ chế gán nhãn tự động/hỗ trợ LLM.
"""
