# Truyện Kiều — Data Ingestion Engineering

**Nguyễn Minh Quân · 2A202603794 · L3B**

Pipeline Python: PDF → chuẩn hóa → chunk → embedding local → PostgreSQL/pgvector → benchmark dev/test. Corpus gồm **189 trang nội dung**, **20 câu hỏi** (15 dev / 5 test), **3 cấu hình**. Đã chạy thực tế và lưu đủ trace, nhãn đánh giá có AI hỗ trợ được học viên xác nhận.

[Báo cáo cá nhân](report/individual/2A202603794_NguyenMinhQuan.md) · [Thông tin học viên](STUDENT.md) · [Checklist nộp bài](SUBMISSION.md)

## Kết quả

| Cấu hình | Dev Hit@1 | Dev Hit@3 | Test Hit@1 | Test Hit@3 | Chunk |
|---|---:|---:|---:|---:|---:|
| A: fixed 500, overlap 50 | 1/15 | 3/15 | 1/5 | 3/5 | 377 |
| B: theo đoạn, tối đa 500 | 2/15 | 5/15 | 2/5 | 4/5 | 379 |
| C: B + filter khi có yêu cầu | 3/15 | 6/15 | 3/5 | 4/5 | 379 |

**Chọn C trên dev trước test.** Hit yêu cầu một chunk đúng nguồn/trang và chứa đủ evidence; đúng trang đơn thuần không đủ. Grounding là chất lượng bằng chứng, không phải độ chính xác câu trả lời LLM. [Phân tích kết quả](starter/results/benchmark/README.md) và [phương pháp audit](starter/results/audit/README.md).

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

Model là `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, **384 chiều**, revision chốt trong [embedding_config.json](starter/embedding_config.json). Chạy local CPU, không cần API key. `prepare_model.py` tải model; `ingest_vectors.py` dùng model offline. Cùng model và cách xử lý query/document cho A/B/C. Chunk vượt 128 token được chia nội bộ và gộp embedding, không cắt cụt; xem [chi tiết](starter/results/vector_ingestion/README.md).

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
| [data/manifest.json](data/manifest.json) | Nguồn, quyền, snapshot, trang hợp lệ và số ký tự |
| [starter/data/truyen_kieu_tron_bo.pdf](starter/data/truyen_kieu_tron_bo.pdf) | PDF local do học viên cung cấp |
| [data/processed/](data/processed/README.md) | 189 trang chuẩn hóa, 108.618 ký tự |
| [benchmark/](benchmark/README.md) | 20 câu, gold, split, quyết định chọn và bản ghi test |
| [starter/src/](starter/src/) | Ingestion, chunking, embedding, vector store, evaluator |
| [starter/scripts/](starter/scripts/) | Các lệnh chuẩn bị, chạy, replay và kiểm tra |
| [starter/results/chunking/](starter/results/chunking/README.md) | Chunk A/B dùng cho A/B/C, cấu hình/thống kê |
| [starter/results/vector_ingestion/](starter/results/vector_ingestion/README.md) | Model/store, log nạp và smoke checks |
| [starter/results/benchmark/](starter/results/benchmark/README.md) | Dev/test: 60 trace, 180 kết quả top-3 |
| [starter/results/audit/](starter/results/audit/README.md) | 30 coherence + 15 grounding + 45 metadata; đã xác nhận |
| [artifacts/experiment_log.csv](artifacts/experiment_log.csv) | Giả thuyết, tham số và kết quả A/B/C |
| [report/individual/2A202603794_NguyenMinhQuan.md](report/individual/2A202603794_NguyenMinhQuan.md) | Báo cáo đầy đủ |

Tài liệu nguồn được lấy từ [URL ghi trong manifest](https://kholuu.wordpress.com/wp-content/uploads/2015/07/truyen_kieu_tron_bo.pdf), hash PDF phải khớp manifest khi tái tạo. Cache model không đưa vào Git; tải bằng revision đã chốt. Nếu thiếu corpus, cần có bản được phép sử dụng và đúng snapshot; không thay âm thầm bằng ấn bản khác.

**Quyền PDF:** học viên đã xác nhận được quyền chia sẻ ngày 14/11/2026; nguồn xác nhận được ghi trong manifest.

**Mục còn mở trước khi nộp:** commit chốt bài và push; kiểm tra người chấm truy cập repo; nộp link theo hướng dẫn lớp. Hiện chưa có bằng chứng hoàn tất các mục này. Các nhận xét AI và sự xác nhận của học viên được ghi rõ trong báo cáo; không gọi đây là chấm độc lập/mù.

Tài liệu đề bài: [GUIDE](GUIDE.md), [BENCHMARK](BENCHMARK.md), [RUBRIC](RUBRIC.md), [RULES](RULES.md), [CHECKPOINTS](CHECKPOINTS.md).
