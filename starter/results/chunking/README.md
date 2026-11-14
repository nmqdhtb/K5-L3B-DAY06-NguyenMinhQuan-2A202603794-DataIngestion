# Chia chunk A/B/C

Chạy từ thư mục gốc dự án:

```bash
starter/.venv/bin/python starter/scripts/build_chunks.py
PYTHONPATH=starter starter/.venv/bin/python -m unittest discover -s starter/tests -v
```

| Cấu hình | Cách chia | Giới hạn ký tự | Overlap | File |
|---|---|---:|---:|---|
| A | Cửa sổ cố định | 500 | 50 | `chunks_A.jsonl` |
| B | Gộp các đoạn cách nhau bằng dòng trắng | 500 | 0 | `chunks_B.jsonl` |
| C | Giống B; bật filter khi truy xuất | 500 | 0 | Dùng lại `chunks_B.jsonl` |

Các tham số được đặt trước khi chạy retrieval, chưa phải cấu hình tối ưu. A–B so sánh hai cách chia, bao gồm khác biệt overlap; không tách riêng được tác động overlap. B–C chỉ thay filter. Chưa chọn model hoặc chạy embedding, vector store, retrieval.

Chunk luôn nằm trong một trang PDF. Với B, đoạn quá dài được cắt ở cuối dòng thơ; nếu một dòng vẫn dài hơn giới hạn thì cắt theo ký tự. Khoảng trắng và số câu được giữ nguyên. Các đoạn này phản ánh xuống dòng của bản PDF, không đảm bảo là khổ thơ hoặc đơn vị ý nghĩa hoàn chỉnh. Đầu/cuối trang có thể cắt ngang ý.

`char_start`/`char_end` là offset ký tự Python trong trang chuẩn hóa, đầu bao gồm/cuối không bao gồm. `verse_start`/`verse_end` vẫn là khoảng dòng của cả trang như protocol đã chốt. ID chunk là SHA-256 từ nguồn, trang, cấu hình, hash nội dung trang và offset; chạy lại cùng dữ liệu tạo cùng ID. Khi trang thay đổi, ID đổi; bước vector store sau này vẫn phải xóa chunk cũ.

`statistics.json` có số chunk, phân bố độ dài, tổng ký tự và thời gian chia + kiểm tra (không phải thời gian ingest/embedding). A có ký tự lặp do overlap, B giữ đúng tổng số ký tự nguồn. C dùng lại B nên không đo một lượt build riêng. `config.json` ghi nguồn dữ liệu và đường dẫn các bộ chunk; đường dẫn chunk tính từ thư mục này.

`coherence_review.json` chứa 30 mẫu: 10 vị trí nguồn đã chốt × A/B/C. Nếu nhiều chunk phủ vị trí, chọn chunk bắt đầu sớm nhất. Điểm/lý do/người chấm để trống; học viên chấm 0–2 theo GUIDE. Script giữ nhãn hiện có khi chạy lại và báo lỗi nếu mẫu nguồn thay đổi. Chưa dùng mẫu này để kết luận B tốt hơn A.

Script kiểm tra mọi ký tự nguồn được phủ, giới hạn độ dài, metadata, tính duy nhất ID và khả năng ghép B trở lại đúng trang. Nó chỉ đọc corpus, protocol và vị trí coherence; không dùng đáp án test để điều chỉnh chunking.
