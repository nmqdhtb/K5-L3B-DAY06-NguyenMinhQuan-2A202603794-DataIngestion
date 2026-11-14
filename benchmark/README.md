# Benchmark Truyện Kiều — phiên bản 1

Đã tạo trước khi chạy embedding/retrieval: 20 câu, 15 dev (`q01`–`q15`) và 5 test (`q16`–`q20`). Có 4 câu filter: `q02`, `q11`, `q15` (dev), `q17` (test). Các câu gồm hỏi trực tiếp, diễn đạt lại và điều kiện trong lời thơ.

## File và cách sử dụng

- `questions.json`: câu hỏi, đáp án, trang gold, evidence nguyên văn và offset ký tự (start inclusive, end exclusive) trong trang chuẩn hóa. Đây là dữ liệu chấm điểm, không truyền toàn bộ vào retrieval.
- `dev_queries.json`, `test_queries.json`: chỉ ID, câu hỏi và filter; là đầu vào được phép cho retrieval. Chạy dev trước; chỉ chạy test sau khi cố định cấu hình.
- `protocol.json`: split, tiêu chí chọn và SHA-256 của dữ liệu/câu hỏi đã chốt. Nếu thay đổi, phải ghi phiên bản và lý do; không tự ghi đè hash để che thay đổi sau khi xem test.
- `coherence_positions.json`: 10 vị trí nguồn chọn trước, ở dòng nội dung đầu của 10 trang PDF đầu. Chưa có nhãn coherence; chấm cùng vị trí cho A/B/C sau khi tạo chunk.
- `student_review.json`: bảng để học viên tự đối chiếu đáp án và evidence. Học viên đã xác nhận hoàn tất kiểm chứng trong cuộc trò chuyện; bản ghi ghi rõ nguồn xác nhận và thời điểm. Trường `student_review: pending` trong `questions.json` là trạng thái lúc tạo snapshot, được giữ nguyên để bảo toàn hash; trạng thái hiện tại xem `student_review.json`.

Chạy kiểm tra từ gốc repo:

```bash
starter/.venv/bin/python starter/scripts/validate_benchmark.py
```

Script kiểm tra evidence/offset, split, filter, query không chứa gold và hash. Kết quả ở `starter/results/benchmark_validation.json`. Khớp chuỗi không tự chứng minh đáp án đúng về nghĩa; trợ lý đã đọc các đoạn để biên soạn, học viên vẫn cần kiểm chứng trước thử nghiệm. Ghi việc dùng AI và cách xác minh trong báo cáo.

## Metadata filter

`verse_start` / `verse_end` là số nguyên: thứ tự dòng thơ đầu/cuối của trang trong bản trích xuất, đếm từ 1. Bỏ tiêu đề, dòng trắng và dòng chỉ có số câu; dòng có số kèm thơ vẫn tính một dòng. Tổng 3.254 dòng. Đây là vị trí tính từ văn bản, không phải tên chương hoặc số câu chuẩn của mọi ấn bản.

Ví dụ, câu hỏi yêu cầu phạm vi dòng 1.001–2.000 cung cấp filter trước retrieval:

```json
{"verse_start": {"lte": 2000}, "verse_end": {"gte": 1001}}
```

Hai điều kiện nối bằng AND: chọn trang giao với khoảng được yêu cầu. A/B không dùng filter; C dùng filter chỉ khi câu hỏi có yêu cầu. Chunk kế thừa khoảng dòng của trang. Đây là lọc phạm vi trang: trang cắt qua biên có thể chứa vài dòng ngoài khoảng, cần ghi hạn chế khi đánh giá. Không dùng trang gold hoặc evidence để tạo filter lúc truy xuất.

Các khoảng học tập rộng được đặt rõ trong câu hỏi: 1–1.000, 1.001–2.000, 2.001–3.254. Đây là ngữ cảnh người dùng giả định, không phải chương do Nguyễn Du đặt. Metadata có căn cứ từ vị trí văn bản; hiệu quả lọc chưa được đo.

Phát hiện mốc số in không khớp thứ tự trích xuất: trang 8 ghi 130 khi dòng tiếp theo là thứ 131; trang 28 ghi 490 khi dòng tiếp theo là thứ 489; trang 30 ghi 505 khi dòng tiếp theo là thứ 515. Giữ nguyên văn bản; ghi sai lệch trong log, không khẳng định nguyên nhân là lỗi bản in hay trích xuất.

## Chọn cấu hình và giới hạn

Dev lấy các đoạn ở trang 2–130; test lấy các đoạn khác ở trang 140–189. Không có trang gold chung giữa hai tập, nhưng vẫn cùng tác phẩm, nhân vật và chủ đề nên chưa độc lập như chia theo tài liệu.

Chọn cấu hình bằng dev: ưu tiên Evidence Hit@3, sau đó Hit@1, sau đó ít chunk hơn; nếu vẫn bằng nhau dùng thứ tự tên A/B/C. Sau đó cố định và đánh giá test của cả ba để báo cáo, không chọn lại theo test. Ghi thời gian/chi phí để phân tích riêng.

Hit yêu cầu một chunk vừa đúng nguồn/trang vừa chứa đủ evidence. Có thể chuẩn hóa khoảng trắng khi khớp; không chấp nhận chỉ trùng vài từ hoặc chỉ đúng trang. `alternative_gold` hiện rỗng: chưa xác định bằng chứng thay thế, không có nghĩa mọi nguồn khác đều sai. Nếu tìm thấy evidence tương đương, đối chiếu nguồn, ghi vào phiên bản gold mới và áp dụng đồng nhất cho cả ba cấu hình; không tinh chỉnh chiến lược dựa trên kết quả test.

Chưa có điểm retrieval, grounding, coherence hoặc metadata audit. Các nhãn thủ công chỉ ghi sau khi đọc kết quả thực tế.
