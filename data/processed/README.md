# Corpus chuẩn hóa — Truyện Kiều

Chạy từ thư mục gốc repo:

```bash
python3.12 -m venv starter/.venv
starter/.venv/bin/python -m pip install 'pypdf>=5,<7'
starter/.venv/bin/python starter/scripts/prepare_corpus.py
```

`pages.jsonl` chứa một bản ghi mỗi trang PDF vật lý; `pages.txt` để đọc và chọn evidence. Script ghi đè đầu ra khi chạy lại, không nối thêm bản ghi. Manifest được bổ sung số ký tự; log ở `starter/results/corpus_validation.json` và `starter/results/ingestion_errors.jsonl` (file rỗng nghĩa là không ghi nhận lỗi trích xuất).

## Phạm vi kiểm chứng

- PDF có 190 trang; giữ 1–189 theo lựa chọn trong manifest, loại trang 190 ghi kết thúc. Trang 1 có cả tiêu đề và thơ.
- Chuẩn hóa NFC, khoảng trắng; giữ dòng thơ, dòng trống, dấu câu và số câu. Không sửa chính tả hoặc thay nội dung bằng một ấn bản khác.
- Sửa riêng lỗi trích xuất `ƣ` → `ư` cho bản PDF này (1.632 lần). Đã đối chiếu hình render trang 100 và 189: các từ như “trước”, “người”, “Vườn”, “được” hiển thị bằng `ư` trong PDF. Đây là kiểm tra mẫu, không phải soát thủ công toàn bộ văn bản.
- 189 trang đầu ra, 108.618 ký tự sau chuẩn hóa (gồm dấu cách, xuống dòng và số câu). Không có trang trích xuất rỗng/lỗi trong 190 trang.
- Học viên xác nhận được quyền chia sẻ PDF ngày 14/11/2026; lưu lời xác nhận trong manifest. Không tự gán giấy phép mở cụ thể hoặc gọi đây là xác minh pháp lý độc lập.

## Bước tiếp theo

Đã tạo 20 câu hỏi với evidence trích từ `pages.jsonl`, tách 15 dev / 5 test ở `benchmark/`. Học viên đã xác minh evidence trước khi chạy retrieval; embedding, dev/test và xác nhận audit đã hoàn tất. Xem README gốc và báo cáo cá nhân.

Corpus chỉ có một tác phẩm; trường author/language không phân biệt được phạm vi lọc. Đã thêm `verse_start`/`verse_end` theo thứ tự dòng thơ trích xuất và 4 câu hỏi có phạm vi dòng cung cấp trước. Xem `benchmark/README.md` về ngữ nghĩa filter, sai lệch mốc số in và giới hạn tại trang biên.
