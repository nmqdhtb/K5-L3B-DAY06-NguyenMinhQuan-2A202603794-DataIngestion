# Kết quả benchmark

Đã chạy **dev**, chưa chạy test. Cấu hình đã chọn và hash các đầu vào/code được chốt ở `benchmark/selected_strategy.json`. Đường dẫn lần chạy cụ thể nằm trong trường `dev_run_directory` của file đó.

| Strategy | Hit@1 | Evidence Hit@3 | Chunk count | Top-3 tuân thủ phạm vi yêu cầu |
|---|---:|---:|---:|---:|
| A | 1/15 (6,67%) | 3/15 (20%) | 377 | 0/3 |
| B | 2/15 (13,33%) | 5/15 (33,33%) | 379 | 0/3 |
| C | 3/15 (20%) | 6/15 (40%) | 379 | 3/3 |

**Chọn C** vì Evidence Hit@3 dev cao nhất theo tiêu chí có trước khi chạy. Không dùng test để lựa chọn. Chưa thể kết luận C tốt nhất trên dữ liệu khác hoặc đã đủ chất lượng để triển khai thực tế.

## Cách tính và kiểm soát

Mỗi câu có top-3 nguyên văn, score cosine, metadata, evidence gold và nhãn hit tự động trong `traces.jsonl`. Một hit cần đúng document ID + trang PDF và chứa đủ evidence sau chuẩn hóa NFC/khoảng trắng. Không nối nhiều chunk để tạo hit. Điểm hiện tại dựa trên khớp evidence đã ghi, chưa được bổ sung bằng chứng tương đương do người chấm xác nhận; trường hợp diễn đạt/bằng chứng khác hợp lệ cần audit riêng, không mặc định là câu trả lời sai.

Dùng chung model, corpus và 15 vector câu hỏi cho cả ba cấu hình. Câu hỏi embedding không kèm gold hoặc expected answer. A/B bỏ filter; C chỉ áp dụng phạm vi có sẵn trong input. Trước chạy, đối chiếu toàn bộ nội dung và metadata của các chunk trong database với file chunk đã tạo. Kiểm tra không phải chỉ đếm số dòng.

Tỷ lệ tuân thủ filter ở đây là kiểm tra điều kiện phạm vi trên metadata đã lưu, không thay cho chấm thủ công metadata đủ/đúng so với PDF. A/B không áp dụng filter nên 0/3 phản ánh hành vi baseline, không phải lỗi triển khai filter. Các câu không có filter có kết quả B/C giống nhau.

## Phân tích từ trace dev

- **A–B:** B tăng Hit@3 từ 3 lên 5 câu. B tìm đủ evidence cho `q06`, `q08`, `q14` trong khi A miss; nhưng `q10` hit ở A và miss ở B. Vì A/B khác cả cách chia và overlap, chưa thể tách riêng tác động từng yếu tố.
- **B–C:** chỉ `q15` đổi từ miss thành hit. B trả các trang 58, 51, 52; C lọc phạm vi dòng 2.001–3.254 và đưa trang 130 có đủ evidence lên hạng 1. Hai câu filter còn lại vẫn miss, dù cả ba câu đều tuân thủ phạm vi.
- **Lỗi sai đoạn dù đúng trang — `q02`, C:** gold là trang 3, câu Thanh minh/tháng ba/tảo mộ/đạp Thanh. Top-2 thuộc trang 3 nhưng chỉ chứa đoạn trước đó, đến câu 40, thiếu câu 43–44; đúng trang vẫn tính miss.
- **Lỗi evidence bị chia — `q09`, B/C:** gold trang 60 gồm cả “Vẻ non xa, tấm trăng gần” và “Cát vàng cồn nọ, bụi hồng dặm kia”. Chunk trả về có vế sau nhưng thiếu vế trước; không có một chunk B chứa đủ toàn bộ gold. Điều này giới hạn Hit@3 ngay cả khi tìm đúng trang.
- **Đánh đổi — `q10`:** A có một chunk chứa toàn bộ gold trang 80 và truy xuất được ở hạng 3. B/C chia gold qua ranh giới đoạn nên miss theo định nghĩa bắt buộc. Đoạn B/C trả về vẫn có thông tin liên quan; chưa gán nhãn grounding thủ công cho trường hợp này.

Điểm thấp là kết quả thực tế; không sửa nhãn/gold hoặc đổi model để che kết quả. Các giả thuyết như model chưa phù hợp thơ cổ cần thí nghiệm riêng, không xem là nguyên nhân đã chứng minh.

## Artifacts và chạy lại

Trong thư mục lần chạy:

- `metrics.json` / `metrics.csv`: tử số, mẫu số, tỷ lệ, số chunk và thời gian truy vấn.
- `traces.jsonl`: 45 lượt truy vấn, tổng 135 kết quả chunk top-3.
- `run.json`: model, số token query, thời gian và chi phí API.
- `per_question.csv`: bảng đối chiếu từng câu, trang gold/top-3 và nguyên nhân miss tự động.

Lệnh dùng cho lần chạy này (từ gốc repo):

```bash
starter/.venv/bin/python starter/scripts/run_dev_benchmark.py
```

Script từ chối chạy lại khi đã có `benchmark/selected_strategy.json` để tránh ghi đè quyết định đã chốt. Nếu cần thí nghiệm dev mới, lưu phiên bản kết quả và quyết định cũ, ghi lý do rõ ràng; không xóa lịch sử. Dùng trace đã lưu để kiểm tra lại chỉ số mà không cần gọi model hoặc database.

Chi phí API của lượt dev là 0 USD; thời gian query embedding được tính một lần cho cả A/B/C. Thời gian truy vấn có cả mở kết nối local và chỉ là một lượt đo; không suy luận cấu hình nào nhanh hơn một cách tổng quát từ chênh lệch nhỏ.

Bước tiếp theo: kiểm tra hash cấu hình đã chọn, chạy 5 câu test cho A/B/C sau khi cố định, rồi chấm thủ công coherence, metadata và grounding. Không điều chỉnh cấu hình theo kết quả test.
