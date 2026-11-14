# Pipeline Python — Truyện Kiều

Hướng dẫn setup, lệnh từ gốc repo và kết quả đầy đủ ở [README gốc](../README.md). Đã triển khai đọc/chuẩn hóa, chia chunk, embedding local, pgvector và đánh giá dev/test; các nhãn audit có AI hỗ trợ đã được học viên xác nhận.

## Entry point

Từ thư mục `starter/`, dùng môi trường `.venv` đã cài theo README gốc:

```bash
.venv/bin/python -m src.run
.venv/bin/python -m src.run --help
```

Mặc định `verify`: kiểm tra các artifacts offline. Các stage có sẵn:

| Stage | Tác dụng |
|---|---|
| `verify` | Kiểm tra hash, chỉ số và xác nhận audit; không cần model/database |
| `prepare-corpus` | Trích xuất/chuẩn hóa PDF theo manifest |
| `build-chunks` | Tạo A/B, C dùng lại B; giữ nhãn coherence có sẵn |
| `prepare-model` | Tải model công khai theo revision đã chốt |
| `ingest` | Tạo embedding local, nạp pgvector và kiểm tra lưu trữ |
| `dev` | Runner dev gốc; từ chối chạy nếu đã có quyết định chọn |
| `test` | Runner test gốc; kiểm tra cấu hình đã chốt, từ chối chạy lại |
| `reproduce` | Chạy lại cả hai split vào thư mục mới, giữ kết quả gốc |

Trong repo đã có kết quả, dùng `reproduce` nếu muốn tái lập benchmark; không xóa marker dev/test. Một lần replay trên tập đã xem không được coi là holdout độc lập mới.

## Thành phần

- `src/ingestion.py`, `src/corpus_metadata.py`: nguồn, trang, chuẩn hóa và thứ tự dòng thơ.
- `src/chunking.py`: cửa sổ cố định và chia theo đoạn, ID/offset ổn định.
- `src/embeddings.py`: model Sentence Transformers local, xử lý văn bản vượt token limit.
- `src/store.py`: snapshot upsert, cosine exact search, filter và transaction.
- `src/evaluation.py`: Hit@1/Hit@3 theo evidence, không suy ra nhãn thủ công.
- `scripts/`: các bước chạy, kiểm tra và replay; `tests/`: unit tests.
- [results/chunking](results/chunking/README.md), [results/vector_ingestion](results/vector_ingestion/README.md), [results/benchmark](results/benchmark/README.md), [results/audit](results/audit/README.md): minh chứng và phương pháp.

## Database local

Compose dùng PostgreSQL 16 + pgvector 0.8.7, cổng `127.0.0.1:55433`, volume bền vững. Copy `.env.example` thành `.env` chỉ khi chưa có; không commit `.env`. Mật khẩu trong Compose chỉ dùng local cho lab.

Từ thư mục `starter/`:

```bash
docker compose -p day6_student_starter up -d --wait
.venv/bin/python scripts/check_setup.py
```

`init.sql` chỉ chạy khi tạo volume lần đầu. Không xóa volume đang chứa dữ liệu để xử lý lỗi. Dừng container mà giữ dữ liệu:

```bash
docker compose -p day6_student_starter stop
```
