# Embedding local và PostgreSQL + pgvector

## Tái lập từ thư mục gốc

```bash
python3.12 -m venv starter/.venv
starter/.venv/bin/python -m pip install -r starter/requirements.txt -c starter/requirements-lock.txt
# Nếu chưa có .env: cp starter/.env.example starter/.env
# Kiểm tra DATABASE_URL trỏ tới PostgreSQL local của lab.
docker compose -p day6_student_starter -f starter/docker-compose.yml up -d --wait
starter/.venv/bin/python starter/scripts/check_setup.py
starter/.venv/bin/python starter/scripts/prepare_model.py
starter/.venv/bin/python starter/scripts/ingest_vectors.py
```

Lần đầu tải thư viện và trọng số cần mạng. Model, tokenizer và vector cache nằm trong `starter/.cache/` (đã gitignore). Sau khi model đã có, `ingest_vectors.py` buộc chế độ offline cho Hugging Face; chỉ kết nối database theo `.env`. Không dùng API embedding trả phí. Nếu thiếu model hoặc database lỗi, chương trình báo lỗi, không thay bằng vector giả.

## Model và xử lý văn bản

Dùng `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, vector 384 chiều, CPU; revision được chốt trong `starter/embedding_config.json`. Tên model/số chiều và cách sử dụng được đối chiếu với [model card chính thức](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2).

Model giới hạn 128 token (gồm token đặc biệt), còn chunk dùng giới hạn ký tự. Để tránh cắt mất phần cuối, văn bản vượt giới hạn được chia đệ quy tại khoảng trắng gần giữa, tới khi từng đoạn vừa token limit. Encode từng đoạn, chuẩn hóa L2, lấy trung bình có trọng số số token nội dung rồi chuẩn hóa L2 lần nữa. Cách tổng hợp này là lựa chọn của bài làm, không phải cấu hình mặc định được model card đánh giá. Có thể mất quan hệ giữa các đoạn; ghi đây là hạn chế.

Query và document dùng cùng quy trình, không thêm prefix. Phần chia nội bộ chỉ phục vụ embedding; chunk, evidence, offset và văn bản lưu trong database không đổi. Log ghi số văn bản cần chia, số token/đoạn thực đã encode. Không đọc câu hỏi test để chọn model hoặc tham số.

## Lưu trữ và kiểm tra

Schema `day6_pipeline`, bảng `chunks` và `embedding_config`. Khóa `(strategy, chunk_id)`; lưu ID tài liệu, nguồn, trang, text, metadata JSONB và vector. A có bộ chunk riêng; B/C dùng cùng embedding nhưng lưu theo strategy để truy xuất độc lập. Chữ ký model được kiểm tra khi khởi tạo schema để tránh trộn model khác.

`upsert` nhận **toàn bộ snapshot của một strategy**, không phải một batch tùy ý. Trong một transaction, ghi các chunk mới/cập nhật rồi xóa ID không còn trong snapshot; khóa bảng khi ghi để tránh hai lần nạp xen kẽ. Snapshot rỗng có nghĩa xóa toàn bộ strategy tương ứng. Khi đổi tài liệu, phải truyền lại toàn bộ tập chunk còn hiệu lực của strategy. Cache embedding có khóa theo hash file chunk và chữ ký model.

Tìm kiếm **exact cosine** bằng toán tử `<=>` của [pgvector](https://github.com/pgvector/pgvector); chưa tạo ANN index. `score = 1 - cosine_distance`, điểm cao hơn tốt hơn. Lọc JSONB bằng các tham số SQL, chỉ cho phép `verse_start`/`verse_end` với `lte`/`gte`. Các giá trị filter nối bằng AND. SQL có tie-break theo chunk ID.

`run.json` chỉ được tạo sau khi hoàn thành các kiểm tra thực tế: số lượng sau hai lần nạp, kết nối mới đọc được dữ liệu, B/C không filter giống nhau, ba khoảng filter, xóa chunk cũ, từ chối vector sai, rollback transaction và từ chối model khác. Kiểm tra xóa/rollback dùng schema tạm riêng rồi dọn schema đó.

`smoke_traces.json` dùng vector chunk đầu của B làm probe kỹ thuật, **không phải câu hỏi benchmark hoặc số đo chất lượng retrieval**. Không suy diễn Hit@1/Hit@3 từ smoke test. Tập dev/test chưa được chạy trong bước này.

Chi phí API là 0 USD; không bao gồm điện, máy và mạng. Log ghi phiên bản thư viện thực tế, PostgreSQL/pgvector, thời gian model/cache và hai lần upsert. Dữ liệu bền vững nằm trong Docker volume của starter; không cần đưa volume hoặc model weights vào Git.

## Truy vấn một câu

```bash
starter/.venv/bin/python starter/scripts/search_vectors.py --strategy C --question "Tìm đoạn thơ nói về cảnh thiên nhiên" --verse-range 1 1000
```

Chỉ truyền câu hỏi và phạm vi người dùng cung cấp. Không đưa đáp án, trang gold hoặc evidence vào câu truy vấn. Chưa dùng lệnh này để chạy tập test trước khi cố định cấu hình.

## Lần chạy đã kiểm chứng

Đã lưu A: 377, B: 379, C: 379 vector 384 chiều. Log `run.json` ghi 188 chunk A và 129 chunk B vượt token limit, được chia nội bộ trước encode; không cắt cụt phần cuối. Các kiểm tra lưu trữ đều đạt. Thời gian log không gồm tải/cài đặt thư viện và thời gian import Python.

`query_smoke.json` là truy vấn văn bản ngoài benchmark với filter dòng 1–1.000, dùng để xác nhận đường đi query → embedding → vector search. Chưa chấm mức liên quan của kết quả này. `requirements-lock.txt` chốt phiên bản dependency đã chạy trên macOS arm64/Python 3.12.
