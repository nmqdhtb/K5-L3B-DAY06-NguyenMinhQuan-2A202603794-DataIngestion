# Báo cáo cá nhân — Data Ingestion Engineering

**Học viên:** Nguyễn Minh Quân · **MSSV:** 2A202603794 · **Lớp:** L3B  
**Chủ đề:** Truy xuất bằng chứng trong Truyện Kiều của Nguyễn Du  
**Ngày thực nghiệm:** 14/11/2026, múi giờ Asia/Ho_Chi_Minh  
**Repo:** [nmqdhtb/K5-L3B-DAY06-NguyenMinhQuan-2A202603794-DataIngestion](https://github.com/nmqdhtb/K5-L3B-DAY06-NguyenMinhQuan-2A202603794-DataIngestion)

## 1. Mục tiêu và kết luận

Xây pipeline Python đọc PDF, chuẩn hóa, chia chunk, tạo embedding thật, lưu pgvector và so sánh ba cấu hình trên cùng dữ liệu/model. Chọn **C — chia theo đoạn + metadata filter khi câu hỏi cung cấp phạm vi** bằng kết quả dev: Evidence Hit@3 = 6/15, cao hơn A = 3/15 và B = 5/15. C được cố định trước khi chạy test, đạt Hit@1 = 3/5 và Hit@3 = 4/5 trên test; không chọn lại cấu hình bằng test.

Kết quả đủ minh họa tác động chunking/filter nhưng chất lượng còn hạn chế: một số truy vấn trả đúng trang mà sai đoạn, một số evidence bị chia qua chunk. Đây là đánh giá bằng chứng truy xuất, không phải độ chính xác câu trả lời LLM. Không xây chatbot trong phạm vi bài.

## 2. Dữ liệu và quyền sử dụng

Nguồn: [bản PDF Truyện Kiều do học viên cung cấp](https://kholuu.wordpress.com/wp-content/uploads/2015/07/truyen_kieu_tron_bo.pdf). Bản local có 190 trang vật lý, dung lượng 1.015.246 byte, SHA-256 `b27aa63630e85c1bbe0a3f9752eac4214a39f7bdeb18a8f82d47d7e1a6a4deee`.

Chọn trang **1–189** có thơ; trang 1 có hình/tiêu đề nhưng đồng thời chứa sáu câu thơ đầu. Loại trang 190 chỉ ghi số câu và kết thúc. Không đếm bìa trống hoặc nhân bản trang. Sau chuẩn hóa có **108.618 ký tự** và **3.254 dòng thơ** theo thứ tự trích xuất. Ký tự tính cả khoảng trắng, dấu câu, số câu và xuống dòng. Danh sách trang và số ký tự từng trang nằm trong [manifest](../../data/manifest.json).

**Quyền:** tác phẩm gốc được học viên ghi nhận là public domain. Ngày 14/11/2026, học viên xác nhận “được quyền chia sẻ pdf” đối với bản PDF đang sử dụng; manifest lưu nguồn xác nhận và thời điểm. Không tự gán tên giấy phép mở cho bản PDF hoặc coi lời xác nhận này là xác minh pháp lý độc lập của trợ lý.

## 3. Pipeline và metadata

1. Đọc từng trang bằng pypdf 6.21.4; giữ trang vật lý và nguồn. Log trang rỗng/lỗi: không ghi nhận lỗi trích xuất ở 190 trang.
2. Chuẩn hóa Unicode NFC, khoảng trắng, giữ dòng thơ/dòng trống. Sửa lỗi font trích xuất `ƣ` → `ư` riêng cho snapshot này, **1.632 lần**, có đối chiếu mẫu trang PDF; không sửa chính tả theo một ấn bản khác.
3. Tạo chunk trong từng trang, không nối qua trang. Mỗi chunk giữ `document_id`, `source`, `page`, `char_start`, `char_end`, `verse_start`, `verse_end` và tham số chia. Offset bắt đầu bao gồm, kết thúc không bao gồm, theo ký tự Python.
4. Tạo embedding local; lưu bảng `day6_pipeline.chunks` trong PostgreSQL. Khóa `(strategy, chunk_id)`; ID ổn định theo hash trang/cấu hình/offset. Nạp lại nhận toàn bộ snapshot một strategy, upsert và xóa ID lỗi thời trong transaction. Kiểm tra thực tế nạp hai lần không trùng, xóa cũ và rollback khi ghi lỗi đều đạt.
5. Truy xuất exact cosine top-3, lưu ID/text/score/metadata và nhãn evidence tự động.

`verse_start`/`verse_end` là thứ tự dòng thơ đầu/cuối **của trang**, bỏ dòng trắng, tiêu đề và dòng chỉ có số câu. Mốc số in sai lệch tại trang 8, 28, 30 được ghi log; không sửa văn bản hoặc tự coi các số này là số câu chuẩn. `source`/`page`/offset giúp truy vết. Khoảng dòng giúp lọc phạm vi học tập do người dùng yêu cầu; A/B không dùng filter, C dùng điều kiện giao khoảng trang với khoảng hỏi. Trang sát biên có thể chứa vài dòng ngoài phạm vi: đây là giới hạn của metadata ở mức trang.

## 4. Model, lưu trữ và cấu hình

Embedding: [sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2), revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, **384 chiều**, CPU local, không API key. Sentence Transformers 5.7.0, Transformers 5.23.0, PyTorch 2.15.0, NumPy 2.5.4; toàn bộ phiên bản ở [requirements-lock.txt](../../starter/requirements-lock.txt).

Giới hạn model là 128 token gồm token đặc biệt. Chunk quá dài được chia nội bộ tại khoảng trắng cho vừa giới hạn; encode từng đoạn, chuẩn hóa L2, trung bình có trọng số số token nội dung rồi chuẩn hóa L2 lại. Cách xử lý query và document giống nhau, không prefix. Không cắt cụt nội dung và không dùng vector giả; cách tổng hợp có thể làm mất quan hệ giữa các đoạn nên là một hạn chế cần kiểm chứng thêm.

Store: PostgreSQL **16.16**, pgvector **0.8.7**, metric **cosine**, truy xuất **exact**, không ANN index. Score = 1 − cosine distance, cùng điểm thì sắp theo chunk ID. Database chạy local `127.0.0.1:55433`, lưu bền vững trong Docker volume. Giá trị filter được truyền bằng tham số SQL; chỉ cho phép trường/operator đã định nghĩa. Schema kiểm tra chữ ký model để tránh trộn vector không tương thích.

| Cấu hình | Chunking | Giới hạn ký tự | Overlap | Filter |
|---|---|---:|---:|---|
| A | Cửa sổ cố định | 500 | 50 | Không |
| B | Gộp đoạn theo dòng trắng, cắt đoạn dài theo dòng thơ | 500 | 0 | Không |
| C | Dùng đúng chunk/vector B | 500 | 0 | Phạm vi dòng trong câu hỏi |

B–C chỉ thay filter. A–B thay cả cách chia và overlap, nên kết quả không tách riêng được ảnh hưởng overlap. Các đoạn theo dòng trắng của PDF không luôn là đơn vị ý nghĩa trọn vẹn.

## 5. Benchmark và trình tự thử nghiệm

[20 câu hỏi](../../benchmark/questions.json) có expected answer, nguồn/trang vật lý, evidence và offset. Học viên đã xác nhận bộ gold. Tách trước thành **15 dev (`q01`–`q15`) / 5 test (`q16`–`q20`)**. Dev lấy đoạn trang 2–130, test lấy các đoạn khác trang 140–189; không trùng trang gold nhưng vẫn có nhân vật/chủ đề chung trong cùng tác phẩm.

Có **4 câu filter**: `q02`, `q11`, `q15` ở dev và `q17` ở test. Phạm vi 1–1.000, 1.001–2.000, 2.001–3.254 là ngữ cảnh học tập giả định được ghi trong câu hỏi, không phải chương tác giả đặt. Không lấy trang gold hoặc đáp án làm filter/query.

Tiêu chí có trước thử nghiệm: ưu tiên dev Hit@3, rồi Hit@1, rồi số chunk ít hơn, cuối cùng thứ tự tên cấu hình nếu vẫn hòa. C được chốt lúc **11:32:55**, test kết thúc lúc **11:37:21** ngày 14/11/2026. [Quyết định chọn](../../benchmark/selected_strategy.json) và [bản ghi test](../../benchmark/test_execution.json) có checksum xác nhận cấu hình/code/dữ liệu và kết quả dev không đổi trước test.

Hit@1/Hit@3 yêu cầu **một chunk** đúng nguồn/trang và chứa toàn bộ evidence sau NFC/chuẩn hóa khoảng trắng. Không cộng hai chunk để tính hit. Hiện dùng các evidence đã ghi; bằng chứng tương đương phải được đối chiếu và ghi nhận riêng, không mặc định mọi đoạn khác nguồn gold đều sai. Không thay gold hoặc cấu hình sau test.

## 6. Kết quả thực tế

| Strategy | Split | Hit@1 | Evidence Hit@3 | Chunk count | Tổng thời gian search (giây) | Chi phí API |
|---|---|---:|---:|---:|---:|---:|
| A | dev | 1/15 (6,67%) | 3/15 (20%) | 377 | 0,2564 | 0 USD |
| B | dev | 2/15 (13,33%) | 5/15 (33,33%) | 379 | 0,2252 | 0 USD |
| C | dev | 3/15 (20%) | 6/15 (40%) | 379 | 0,2058 | 0 USD |
| A | test | 1/5 (20%) | 3/5 (60%) | 377 | 0,1124 | 0 USD |
| B | test | 2/5 (40%) | 4/5 (80%) | 379 | 0,0724 | 0 USD |
| C | test | 3/5 (60%) | 4/5 (80%) | 379 | 0,0631 | 0 USD |

Query embedding dùng chung: dev 0,3608 giây, test 0,2788 giây. Thời gian search gồm mở kết nối local; đây là một lượt đo, không phải benchmark hiệu năng đủ lặp. Không bao gồm tải model, cài thư viện, điện, máy hoặc mạng trong chi phí 0 USD.

| Strategy | Tổng ký tự chunk | Độ dài min / trung bình / max | Token nội dung encode | Thời gian embedding | Upsert 2 lần + kiểm tra |
|---|---:|---|---:|---:|---:|
| A | 118.018 | 60 / 313,05 / 500 | 37.961 | 7,9359 giây | 0,4440 giây |
| B | 108.618 | 36 / 286,59 / 500 | 34.821 | 6,1926 giây | 0,3802 giây |
| C | 108.618 | 36 / 286,59 / 500 | Dùng lại B | Dùng lại B | 0,5421 giây |

A có 188 chunk phải chia nội bộ theo token; B có 129. C không gọi embedding lại cho document. Số token trên không gồm token đặc biệt; A cao hơn do overlap. Thời gian toàn lượt ingest ghi 16,7998 giây, không gồm import/cài đặt/tải model. Nguồn: [log ingestion](../../starter/results/vector_ingestion/run.json), [thống kê chunk](../../starter/results/chunking/statistics.json).

## 7. Coherence, metadata và grounding

**Phương pháp chấm:** AI đọc mẫu, đề xuất điểm/lý do theo GUIDE; học viên đã xác nhận toàn bộ đề xuất ngày 14/11/2026. Giữ cả đề xuất gốc và nhãn xác nhận. Đây là đánh giá có AI hỗ trợ, không phải chấm mù hoặc độc lập; AI đã thấy kết quả truy xuất và cũng tham gia viết pipeline. [Xác nhận học viên](../../starter/results/audit/student_confirmation.json).

Coherence dùng cùng 10 vị trí đầu nội dung ở 10 trang PDF đầu, chốt trước khi xem retrieval; nếu nhiều chunk phủ vị trí thì chọn chunk bắt đầu sớm nhất. Chấm 0–2: không hiểu / hiểu một phần / tự hiểu và trọn ý. Grounding xét đủ top-3 cho 5 câu test mỗi cấu hình theo độ đủ bằng chứng, không phải câu trả lời LLM. Metadata gồm 45 bản ghi test, đối chiếu nguồn/trang/offset/text/khoảng dòng với PDF trích lại; học viên xác nhận kết quả được trình bày, không ghi nhận một lượt kiểm tra nguồn độc lập mới.

| Strategy | Coherence /2 (n) | Metadata đủ/đúng test | Filter dev / test | Grounding số câu 0 / 1 / 2 | Grounding trung bình /2 |
|---|---:|---:|---|---|---:|
| A | 1,1 (10) | 15/15 | 0/3 · 0/1 | 2 / 0 / 3 | 1,2 |
| B | 1,4 (10) | 15/15 | 0/3 · 0/1 | 1 / 0 / 4 | 1,6 |
| C | 1,4 (10) | 15/15 | 3/3 · 1/1 | 1 / 0 / 4 | 1,6 |

Filter tuân thủ tính trên câu có yêu cầu phạm vi, không trên tất cả câu. A/B không bật filter nên 0 không phải lỗi triển khai. Metadata đầy đủ không bảo đảm tìm đúng bằng chứng. B giữ dòng tốt hơn nhưng vẫn có chủ thể/ý nghĩa phụ thuộc trang trước; coherence chưa đạt 2/2. Mẫu tập trung đầu tác phẩm có thể không đại diện toàn corpus.

## 8. Phân tích năm khía cạnh và đánh đổi

**Retrieval:** C tốt nhất dev theo tiêu chí đã định; test B/C cùng Hit@3 nhưng C cao hơn Hit@1. Không coi 4/5 test là 80% độ chính xác chatbot hay kết quả có thể suy rộng. Test có 5 câu, mỗi câu thay đổi tỷ lệ 20 điểm phần trăm.

**Coherence:** B/C giữ nguyên dòng thơ nên ít lỗi cắt từ hơn A, nhưng ranh giới dòng trắng và trang vẫn có thể chia ý. Điểm 1,4/2 cao hơn 1,1/2 trên mẫu đã chọn, chưa đủ để kết luận mọi chunk B đều tốt hơn.

**Metadata:** nguồn/trang/offset hỗ trợ đối chiếu; phạm vi dòng giúp đưa `q15` dev từ miss của B thành hit top-1 của C, và đưa `q17` test từ hạng 2 của B lên hạng 1 của C. Các trường nguồn hợp lệ vẫn không cứu được câu sai đoạn. Filter giả định người dùng cung cấp phạm vi trước, không thử suy ra phạm vi tự động.

**Grounding:** test A có 3 câu đủ bằng chứng, B/C có 4. `q20` được chấm 0: các chunk không chứa mệnh đề so sánh tâm/tài, dù B/C đã tìm đúng trang; không dùng điểm similarity để tự suy ra đủ grounding.

**Tác động chiến lược:** B tăng Hit@3 dev 2 câu so với A, giảm 9.400 ký tự phải encode nhờ không overlap nhưng tăng 2 chunk. C dùng lại tài nguyên embedding B và thêm chi phí lọc. Lợi ích filter tùy câu: `q02` và `q11` dev vẫn miss ở C. Không kết luận C nhanh hơn từ vài mili giây chênh lệch một lượt.

### Các lỗi có bằng chứng

| Trường hợp | Nguồn gold | Quan sát | Giải thích có căn cứ |
|---|---|---|---|
| `q02`, dev, C | Trang 3, câu 43–44 | Top-2 đúng trang nhưng đoạn chỉ đến câu 40 | Đúng trang chưa đủ; chunk không chứa evidence Thanh minh/tảo mộ/đạp Thanh |
| `q09`, dev, B/C | Trang 60 | Có phần cát vàng/bụi hồng, thiếu non xa/trăng gần | Gold bị tách qua ranh giới chunk, không có một chunk đủ evidence |
| `q10`, dev, A so với B/C | Trang 80 | A hit ở hạng 3; B/C miss | Chia theo đoạn làm gold qua hai chunk, cho thấy B không luôn cải thiện |
| `q20`, test, B/C | Trang 189 | Top-3 đúng trang nhưng dừng trước câu tâm/tài | Sai đoạn trong cùng trang, không được tính hit theo định nghĩa chính |

Không khẳng định model không phù hợp thơ cổ là nguyên nhân đã chứng minh; đó chỉ là giả thuyết cho nghiên cứu sau.

## 9. Tái lập, artifacts và sử dụng AI

Lệnh setup, kiểm tra offline, dựng database và replay kết quả nằm trong [README gốc](../../README.md). `python -m src.run` từ thư mục `starter` mặc định kiểm tra artifacts đã lưu, không tự chạy lại holdout. Replay ghi thư mục mới và giữ nguyên quyết định chọn/trace gốc; kết quả replay trên tập đã quan sát không phải một holdout mới.

- [Trace dev](../../starter/results/benchmark/dev/20261114T113255829181/traces.jsonl), [metrics dev](../../starter/results/benchmark/dev/20261114T113255829181/metrics.csv).
- [Trace test](../../starter/results/benchmark/test/20261114T113721286471/traces.jsonl), [metrics test](../../starter/results/benchmark/test/20261114T113721286471/metrics.csv).
- [Nhãn coherence](../../starter/results/audit/coherence_review.json), [grounding](../../starter/results/audit/grounding_review.json), [metadata](../../starter/results/audit/metadata_review.json), [tổng hợp](../../starter/results/audit/summary.json).
- [Nhật ký thí nghiệm](../../artifacts/experiment_log.csv), [manifest](../../data/manifest.json), [log lỗi trích xuất](../../starter/results/ingestion_errors.jsonl). File lỗi rỗng biểu thị không ghi nhận lỗi, không phải thiếu log.

Dùng trợ lý Codex để giải thích yêu cầu, viết code, chuẩn bị benchmark, chạy kiểm tra, phân tích trace và đề xuất nhãn. Học viên xác minh gold rồi xác nhận các đề xuất đánh giá. Kiểm tra bằng đối chiếu evidence/offset, hash dữ liệu/code, unit tests, nạp lại database, filter và rollback. Không tự tạo số liệu chưa chạy. Quy trình không dùng lấy mẫu ngẫu nhiên; chunk/split cố định và có tie-break; các phiên bản model/thư viện được ghi lại, vẫn có thể có sai số số học khác phần cứng.

## 10. Giới hạn, cải tiến và tình trạng nộp

Giới hạn chính: một tác phẩm, ít câu hỏi; diễn đạt văn xuôi khác ngôn ngữ thơ; evidence dài dễ vượt ranh giới chunk; pooling các đoạn token có thể giảm ngữ cảnh; filter thô theo trang; nhãn có AI hỗ trợ và không độc lập; quyền chia sẻ PDF dựa trên xác nhận của học viên, chưa có xác minh độc lập.

Nếu làm thí nghiệm mới: thử chia theo cặp lục bát và ngữ cảnh lân cận; kiểm tra model retrieval tiếng Việt/hybrid; tăng câu hỏi và thêm tài liệu có giấy phép rõ; có người chấm độc lập. Mọi thay đổi phải tạo phiên bản và tập kiểm tra mới, không chỉnh theo test đã xem rồi báo như holdout độc lập.

Đã hoàn thiện nội dung báo cáo và artifacts kỹ thuật. Còn cần tạo commit chốt bài, đẩy repo và nộp link theo kênh giảng viên. Không tự suy ra deadline hoặc trạng thái repo công khai từ remote URL.

Kiểm chứng tái lập: [lượt replay ngày 14/11/2026](../../starter/results/reproductions/20261114T115206601986/summary.json) chạy lại đủ 60 trace dev/test và cho chỉ số trùng lần gốc. Đây là kiểm chứng tái lập trên tập đã quan sát, không phải holdout mới.
