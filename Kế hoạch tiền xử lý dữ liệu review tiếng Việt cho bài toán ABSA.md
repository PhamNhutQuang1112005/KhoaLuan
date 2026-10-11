# Kế hoạch tiền xử lý dữ liệu review tiếng Việt cho bài toán ABSA

Oct 9, 2026 · @Quang

## Nguyên tắc sắp xếp

Thứ tự xử lý đi theo nguyên tắc: **cấu trúc → lọc rẻ → làm sạch ký tự → chuẩn hóa từ vựng → khử trùng lặp lần cuối**. Sửa khung dữ liệu trước, bỏ sớm những dòng chắc chắn vô dụng để giảm khối lượng kiểm duyệt thủ công. Các bước dựa trên so khớp văn bản (near-duplicate, tiếng lóng) chạy sau cùng, khi văn bản đã đồng nhất.

## Giai đoạn 0 — Chuẩn bị

Bắt buộc làm trước mọi bước.

- **Gán `review_id` duy nhất cho mọi dòng và giữ nguyên cột `review_raw`.** Quy trình tách file → kiểm duyệt → merge lại chỉ an toàn khi merge theo ID, không merge theo nội dung hay số thứ tự dòng.
- **Lưu checkpoint sau mỗi giai đoạn** (v0\_raw, v1\_structured…) và ghi log số dòng bị xóa hay sửa ở từng bước. Bảng log này dùng được ngay cho phần mô tả dataset trong luận văn.

## Giai đoạn 1 — Sửa cấu trúc (tự động)

1. **Bước 1: Xử lý lệch cột.** Phải làm đầu tiên. Nếu xóa dòng thiếu dữ liệu trước, những dòng bị lệch (review nằm ở cột tác giả, cột review trống) sẽ bị xóa nhầm. Dòng nào cột thời gian không parse được thì rất có thể bị lệch.
2. **Bước 2: Xóa dòng trống hoặc thiếu cột bắt buộc.** Chỉ làm sau khi đã kéo dữ liệu về đúng cột.
3. **Bước 3: Ép kiểu cột thời gian.** Thời gian chuẩn hỗ trợ khử trùng lặp về sau (cùng tác giả, cùng thời điểm, cùng nội dung là trùng do crawl).
4. **Bước 4: Tách tiêu chí đánh giá thành các cột riêng.** Đây là thao tác cấu trúc, không phụ thuộc vào việc làm sạch văn bản review.

## Giai đoạn 2 — Chuẩn hóa nền an toàn (tự động)

5. **(Bổ sung) Chuẩn hóa Unicode về NFC và thống nhất vị trí dấu thanh** ("hoà" và "hòa", "thuỷ" và "thủy"). Nếu bỏ qua, hai chuỗi trông giống hệt nhau vẫn bị coi là khác nhau, làm hỏng mọi bước so khớp phía sau. Loại bỏ thẻ HTML cũng làm ở đây.
6. **Bước 16: Khoảng trắng thừa** (lượt 1).
7. **Bước 17: Chữ hoa/thường.** Tạo cột làm việc `text_norm` viết thường để so khớp từ điển, giữ nguyên bản gốc. PhoBERT phân biệt hoa thường, nên việc hạ chữ thường trong dữ liệu huấn luyện cuối cùng là một quyết định riêng, có thể đưa vào ablation.

## Giai đoạn 3 — Lọc bỏ thô

Mục tiêu là giảm khối lượng dữ liệu sớm nhất có thể.

8. **Bước 8a + 21a: Xóa trùng lặp chính xác** (exact match trên `text_norm`), trong từng file rồi giữa các file. Bước này rẻ và giảm đáng kể số dòng cần kiểm duyệt ở bước spam. Cùng nội dung nhưng khác tác giả (ví dụ "Hàng đẹp giao nhanh") có thể là review thật: cần quyết định giữ một bản hay giữ có giới hạn, và ghi rõ trong luận văn.
9. **Bước 5: Xóa review chỉ gồm emoji hoặc ký tự đặc biệt.** Những review này không có khía cạnh nào nên vô dụng với ABSA.
10. **Bước 7: Lọc URL quảng cáo và spam** (kiểm duyệt thủ công).
11. **Bước 19: Lọc review không phải tiếng Việt.** Công cụ nhận diện ngôn ngữ (langdetect, fastText) hay nhận nhầm tiếng Việt không dấu hoặc teencode thành tiếng nước ngoài. Chỉ xóa tự động khi mô hình chắc chắn cao **và** câu không chứa từ tiếng Việt nào (kể cả dạng không dấu như "hang", "dep", "khong"). Các trường hợp còn lại đưa vào file kiểm duyệt.

## Giai đoạn 4 — Làm sạch nhiễu ký tự trong câu

12. **Bước 14: Emoji xen giữa câu.** Với ABSA, emoji mang tín hiệu cảm xúc. Nên tách ra cột `emojis` hoặc thay bằng tag (ví dụ `<pos_emoji>`) thay vì xóa hẳn.
13. **Bước 15: Ký tự đặc biệt vô nghĩa.**
14. **Bước 13: Lặp ký tự** ("đẹppppp", "!!!!!"). Làm sau bước 14 và 15 vì emoji và ký tự đặc biệt cũng hay lặp, và phải đi trước teencode vì "khôngggg" cần được rút gọn mới khớp từ điển. Cần whitelist các từ có chữ lặp hợp lệ như "good", "free", "xoong".
15. **Bước 16: Khoảng trắng** (lượt 2). Các bước xóa ở trên thường để lại khoảng trắng thừa.

## Giai đoạn 5 — Lọc review quá ngắn

16. **Bước 6: Review ≤ 4 từ** (kiểm duyệt thủ công). Số từ chỉ đếm đúng sau khi đã bỏ emoji, ký tự rác và ký tự lặp. Lọc trước giai đoạn chuẩn hóa từ vựng giúp không tốn công sửa teencode cho những review sẽ bị loại. Khi duyệt tay, giữ lại các câu ngắn nhưng có khía cạnh rõ ràng: "giao nhanh, pin trâu" vẫn rất giá trị cho ABSA.

## Giai đoạn 6 — Chuẩn hóa từ vựng

Thứ tự trong giai đoạn này rất quan trọng: mỗi bước cần đầu ra của bước trước để hoạt động đúng.

17. **Bước 9 + 10: Teencode và từ viết tắt** ("ko", "dc", "j", "sp", "đt"). Làm đầu tiên vì công cụ khôi phục dấu và sửa chính tả cho kết quả sai nếu gặp "ko", "dc".
18. **Bước 18: Tiếng Anh xen lẫn và từ mượn.** Phải làm **trước** khôi phục dấu và sửa chính tả, nếu không "ship", "size", "pin", "case", "fullbox" sẽ bị thêm dấu hoặc sửa sai. Đánh dấu các từ cần bảo vệ (protected tokens) để các bước sau bỏ qua.
19. **Bước 12: Khôi phục dấu cho câu viết không dấu.** Làm trước sửa chính tả, vì sửa chính tả trên câu không dấu gần như vô nghĩa.
20. **Bước 11: Lỗi chính tả.**
21. **Bước 20: Tiếng lóng cảm xúc** ("xịn xò", "phèn", "đỉnh", "keo"). Làm cuối vì chỉ nhận diện đúng tiếng lóng khi văn bản đã có dấu và đúng chính tả. Không thay tiếng lóng bằng từ trung tính làm mất cường độ cảm xúc: ánh xạ sang từ chuẩn cùng sắc thái, hoặc giữ nguyên nếu đã phổ biến.

## Giai đoạn 7 — Khử trùng lặp lần cuối và kiểm tra

22. **Bước 8b: Gần trùng lặp trong từng file** (MinHash hoặc cosine similarity trên TF-IDF, kiểm duyệt thủ công). Phải làm sau khi chuẩn hóa, vì trước đó "sp ok lắm" và "sản phẩm ok lắm" chưa được nhận ra là giống nhau.
23. **Bước 21b: Gần trùng lặp giữa các file.** Review trùng giữa các ngành hàng gây rò rỉ dữ liệu (data leakage) giữa train và test trong thí nghiệm cross-domain. Bước này phải xong trước khi chia train/test và trước khi lấy mẫu Gold Dataset.
24. **Kiểm tra cuối:** chạy lại bước 16 và 17, kiểm tra không còn dòng trống, so số dòng với log.

## Gợi ý tối ưu khối lượng kiểm duyệt thủ công

Kế hoạch có khoảng 10 bước kiểm duyệt tay, sẽ rất nặng nếu duyệt theo từng review. Hai cách giảm đáng kể:

- **Với bước 9, 10, 18 và 20, kiểm duyệt ở cấp độ từ vựng thay vì từng câu.** Trích các token không có trong từ điển tiếng Việt, đếm tần suất, rồi duyệt tay danh sách token để xây file ánh xạ (ví dụ `ko → không`, `ship → giữ nguyên`). Dùng code áp dụng file ánh xạ cho toàn bộ dữ liệu. Vài nghìn token phổ biến thường bao phủ phần lớn các trường hợp, và file ánh xạ có thể đưa vào phụ lục hoặc dataset công bố.
- **Gộp các bước cùng giai đoạn vào một file kiểm duyệt duy nhất,** gồm các cột `review_id`, `text_before`, `text_after_auto`, `flag_type`, `text_final`. Mỗi dòng chỉ cần mở một lần, thay vì tách và merge mười lần.
