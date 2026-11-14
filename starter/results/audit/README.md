# Audit coherence, metadata và grounding

Trạng thái: **học viên đã xác nhận toàn bộ đề xuất AI và kết quả đối chiếu metadata**. Đây là đánh giá có AI hỗ trợ, không phải chấm độc lập/mù. Xác nhận và thời điểm nằm trong `student_confirmation.json`. Xem `REVIEW.md` để đọc đầy đủ các chunk/top-3 cùng lý do, không chỉ điểm tổng hợp.

## Các file

- `coherence_review.json`: 30 mẫu theo 10 vị trí đã chốt trước khi truy xuất × A/B/C. Điểm đề xuất ở `ai_proposed_score`; trường `score`, `reason`, `reviewer` đã ghi theo xác nhận của học viên.
- `grounding_review.json`: 15 trường hợp, 5 câu test × A/B/C, đủ text top-3. Trường điểm người chấm đã được điền bằng điểm đề xuất được học viên chấp nhận.
- `metadata_review.json`: 45 bản ghi top-3, kiểm tra tự động nguồn/trang/text/offset/khoảng dòng; xác nhận của học viên được ghi vào `student_complete_and_correct`, `student_notes`, `reviewer`.
- `summary.json`: giữ tổng hợp đề xuất AI và bổ sung các trường `confirmed_*` theo xác nhận, không coi là chấm độc lập.

## Phương pháp và giới hạn

Trợ lý AI đã đọc các chunk coherence và toàn bộ top-3 test, dùng thang 0–2 trong GUIDE để đề xuất điểm và viết lý do từng trường hợp. Không dùng công thức Hit@3 để gán grounding/coherence. Các điểm grounding ở lượt này tình cờ chỉ có 0 và 2; trường hợp `q20` được đề xuất 0 vì đoạn nói về tài nhưng thiếu mệnh đề so sánh với tâm, không chỉ vì phép khớp chuỗi thất bại. Học viên có thể phản biện và sửa điểm nếu có căn cứ.

AI vừa triển khai pipeline vừa chấm và đã thấy điểm retrieval, nên không phải đánh giá mù hay độc lập. B/C dùng cùng chunk ở mẫu coherence và có cùng top-3 ở câu không filter; những trường hợp trùng dùng cùng đề xuất để nhất quán. Chưa thay nhãn gold, chỉ số retrieval hoặc cấu hình sau test.

Metadata được so với PDF local có SHA-256 khớp manifest, trích lại theo từng trang vật lý; chuẩn hóa NFC/khoảng trắng và sửa lỗi `ƣ` → `ư` theo quy tắc đã công bố. Kiểm tra URL dựa trên manifest, không phải xác minh độc lập quyền tài liệu hoặc website. Khoảng dòng là thứ tự dòng trích xuất, không phải số câu in luôn đúng. Các kiểm tra tự động không thay thế việc học viên tự xem nguồn.

Metadata `source`/`page`/offset giúp truy đoạn về trang vật lý; khoảng dòng giúp C thu hẹp phạm vi theo yêu cầu người dùng. Hạn chế: filter ở mức trang có thể giữ vài dòng ngoài biên, và một tác phẩm không đủ kiểm tra giá trị phân biệt tác giả/ngôn ngữ.

## Đề xuất để học viên xem xét

| Strategy | Coherence AI /2 (10 mẫu) | Grounding AI /2 (5 câu) | Grounding 0/1/2 | Metadata tự động |
|---|---:|---:|---|---:|
| A | 1,1 | 1,2 | 2 / 0 / 3 | 15/15 |
| B | 1,4 | 1,6 | 1 / 0 / 4 | 15/15 |
| C | 1,4 | 1,6 | 1 / 0 / 4 | 15/15 |

Học viên đã xác nhận các đề xuất trong `REVIEW.md`; điểm/lý do đã được ghi lại, giữ nguyên đề xuất gốc. Việc xác nhận benchmark trước đây chỉ áp dụng đáp án/evidence của 20 câu, không tự động xác nhận các đánh giá đầu ra mới này.

Tạo phiếu ban đầu bằng `starter/.venv/bin/python starter/scripts/prepare_audit.py` từ gốc repo. Script từ chối ghi đè file hiện có để giữ nhãn và nhận xét. Điểm AI là nhận xét trong cuộc trò chuyện được lưu lại, không do script tự tính.
