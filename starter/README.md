# Pipeline Python — Truyện Kiều

Hướng dẫn cài đặt và chạy bài làm của Nguyễn Minh Quân — MSSV 2A202603794 — lớp L3B.

[Đề bài](../README.md) · [Báo cáo kết quả và nhận xét](../report/individual/2A202603794_NguyenMinhQuan.md) · [Thông tin học viên](../STUDENT.md)

Các lệnh có tiền tố `starter/` chạy từ **gốc repository**, nơi có `STUDENT.md`. Trong phiên bản hiện tại, kết quả được lưu tại `starter/results/` tính từ gốc repo.

## 1. Cài đặt

Đã kiểm tra trên macOS arm64, Python **3.12**, Docker Desktop. Tất cả lệnh dưới đây chạy từ **thư mục gốc repo**, trừ khi ghi rõ khác. Lần cài đầu cần mạng để tải dependency/model/image; Python mặc định của máy có thể là 3.15 nên gọi rõ `python3.12`.

```bash
python3.12 -m venv starter/.venv
starter/.venv/bin/python -m pip install -r starter/requirements.txt -c starter/requirements-lock.txt
```

`requirements-lock.txt` ghi các phiên bản đã chạy. Không commit `.venv`, `.env`, model cache hoặc vector cache. `.env.example` và mật khẩu trong Compose chỉ dành cho database lab local.

## 2. Kiểm tra kết quả đã nộp — không cần model/database

```bash
starter/.venv/bin/python starter/scripts/verify_submission.py
PYTHONPATH=starter starter/.venv/bin/python -m unittest discover -s starter/tests -v
```

Lệnh verify kiểm tra hash dữ liệu/code/trace gốc, tính lại chỉ số từ trace, đối chiếu nhãn xác nhận và kiểm tra mẫu secret thường gặp. Đây là kiểm tra kỹ thuật, không xác minh quyền bản PDF hoặc việc đã nộp link. Có thể dùng entry point mặc định tương đương:

```bash
cd starter
.venv/bin/python -m src.run
```

## 3. Dựng vector store và tìm kiếm

Quay về gốc repo nếu đã `cd starter`. Tạo `.env` từ mẫu **chỉ khi chưa có**, rồi kiểm tra `DATABASE_URL` local:

```bash
if [ ! -f starter/.env ]; then cp starter/.env.example starter/.env; fi
docker compose -p day6_student_starter -f starter/docker-compose.yml up -d --wait
starter/.venv/bin/python starter/scripts/check_setup.py
starter/.venv/bin/python starter/scripts/prepare_model.py
starter/.venv/bin/python starter/scripts/ingest_vectors.py
```

Model là `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, **384 chiều**, revision chốt trong [embedding_config.json](embedding_config.json). Chạy local CPU, không cần API key. `prepare_model.py` tải model; `ingest_vectors.py` dùng model offline. Cùng model và cách xử lý query/document cho A/B/C. Chunk vượt 128 token được chia nội bộ và gộp embedding, không cắt cụt; xem [chi tiết](results/vector_ingestion/README.md).

Database dùng schema `day6_pipeline`, exact cosine search và metadata filter. Upsert nhận toàn bộ snapshot một strategy, nạp lại không trùng và xóa chunk lỗi thời. Dữ liệu bền vững trong Docker volume. Không xóa volume để xử lý lỗi kết nối. Câu lệnh ingest cập nhật log ingestion của lần chạy đó; giữ bản sao log gốc nếu cần so sánh thời gian với lần nộp.

Truy vấn thử ngoài benchmark:

```bash
starter/.venv/bin/python starter/scripts/search_vectors.py --strategy C --question "Tìm đoạn thơ nói về cảnh thiên nhiên" --verse-range 1 1000
```

A/B không dùng filter. C chỉ nhận phạm vi do người dùng cung cấp trước truy xuất, không dùng gold để lọc.

## 4. Tái lập benchmark mà giữ nguyên kết quả gốc

Sau khi database/model đã sẵn sàng:

```bash
starter/.venv/bin/python starter/scripts/reproduce_benchmark.py --split both
```

Hoặc chọn `--split dev` / `--split test`. Script kiểm tra các hash đã chốt, dùng cùng query/model/store/evaluator rồi ghi **thư mục mới** trong `starter/results/reproductions/`. Không sửa lựa chọn C, gold, trace gốc hoặc nhật ký thí nghiệm. So sánh chỉ số với lần chạy gốc. Đây là replay tập đã biết kết quả, không phải một lần holdout độc lập mới.

Các lệnh tạo kết quả gốc đã dùng:

```bash
starter/.venv/bin/python starter/scripts/prepare_corpus.py
starter/.venv/bin/python starter/scripts/build_chunks.py
starter/.venv/bin/python starter/scripts/validate_benchmark.py
starter/.venv/bin/python starter/scripts/run_dev_benchmark.py
starter/.venv/bin/python starter/scripts/run_test_benchmark.py
```

Trong repo bài nộp, kết quả gốc đã tồn tại: runner dev/test cố ý từ chối chạy lại để giữ lịch sử. Dùng lệnh `reproduce_benchmark.py` ở trên; không xóa marker để lách bảo vệ. Hai lệnh chuẩn bị corpus/chunk là tùy chọn khi muốn kiểm tra lại quá trình tạo dữ liệu, không cần chạy để xem điểm đã lưu. Audit có nhãn đã xác nhận, không chạy lại script khởi tạo phiếu để ghi đè.

## Dữ liệu, minh chứng và cấu trúc

| Đường dẫn | Nội dung |
|---|---|
| [data/manifest.json](../data/manifest.json) | Nguồn, quyền, snapshot, trang hợp lệ và số ký tự |
| [starter/data/truyen_kieu_tron_bo.pdf](data/truyen_kieu_tron_bo.pdf) | PDF local do học viên cung cấp |
| [data/processed/](../data/processed/README.md) | 189 trang chuẩn hóa, 108.618 ký tự |
| [benchmark/](../benchmark/README.md) | 20 câu, gold, split, quyết định chọn và bản ghi test |
| [starter/src/](src) | Ingestion, chunking, embedding, vector store, evaluator |
| [starter/scripts/](scripts) | Các lệnh chuẩn bị, chạy, replay và kiểm tra |
| [starter/results/chunking/](results/chunking/README.md) | Chunk A/B dùng cho A/B/C, cấu hình/thống kê |
| [starter/results/vector_ingestion/](results/vector_ingestion/README.md) | Model/store, log nạp và smoke checks |
| [starter/results/benchmark/](results/benchmark/README.md) | Dev/test: 60 trace, 180 kết quả top-3 |
| [starter/results/audit/](results/audit/README.md) | 30 coherence + 15 grounding + 45 metadata; đã xác nhận |
| [artifacts/experiment_log.csv](../artifacts/experiment_log.csv) | Giả thuyết, tham số và kết quả A/B/C |
| [report/individual/2A202603794_NguyenMinhQuan.md](../report/individual/2A202603794_NguyenMinhQuan.md) | Báo cáo đầy đủ |

Tài liệu nguồn được lấy từ [URL ghi trong manifest](https://kholuu.wordpress.com/wp-content/uploads/2015/07/truyen_kieu_tron_bo.pdf), hash PDF phải khớp manifest khi tái tạo. Cache model không đưa vào Git; tải bằng revision đã chốt. Nếu thiếu corpus, cần có bản được phép sử dụng và đúng snapshot; không thay âm thầm bằng ấn bản khác.

**Quyền PDF:** học viên đã xác nhận được quyền chia sẻ ngày 14/11/2026; nguồn xác nhận được ghi trong manifest.


## Entry point

Từ thư mục `starter/`, dùng môi trường `.venv` đã cài theo mục cài đặt ở trên:

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
