# Kết quả bài nộp

Thư mục này cung cấp thống kê, trace, nhãn audit và log tại gốc repository theo `SUBMISSION.md`.

Đây là bản sao kết quả từ `starter/results/` tại thời điểm ghi trong [submission_snapshot.json](submission_snapshot.json). Pipeline tiếp tục sử dụng `starter/results/`; hai thư mục không tự đồng bộ. Các file được sao chép giữ nguyên nội dung, kể cả đường dẫn lịch sử trong log. Không chạy lại thí nghiệm hoặc thay đổi điểm khi tạo bản sao này.

| Nội dung | Đường dẫn |
|---|---|
| Cấu hình chunk, thống kê và chunk A/B | [chunking/](chunking/README.md) |
| Kết quả dev/test, metrics và trace top-3 | [benchmark/](benchmark/README.md) |
| Nhãn coherence, metadata, grounding và xác nhận | [audit/](audit/README.md) |
| Log nạp vector và kiểm tra truy xuất | [vector_ingestion/](vector_ingestion/README.md) |
| Kết quả tái lập đã chạy | [reproductions/](reproductions/) |
| Kiểm tra corpus | [corpus_validation.json](corpus_validation.json) |
| Kiểm tra benchmark | [benchmark_validation.json](benchmark_validation.json) |
| Log lỗi ingestion | [ingestion_errors.jsonl](ingestion_errors.jsonl) |

[Manifest dữ liệu](../data/manifest.json) · [Nhật ký thí nghiệm](../artifacts/experiment_log.csv) · [Báo cáo cá nhân](../report/individual/2A202603794_NguyenMinhQuan.md)

`submission_snapshot.json` liệt kê đường dẫn nguồn, đường dẫn bản sao và SHA-256 của từng file. Nếu kết quả nguồn thay đổi, cần cập nhật bản sao và danh sách checksum trước khi chốt bài nộp; không sửa riêng số liệu trong bản sao.
