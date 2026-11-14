# Phiếu đọc và kiểm chứng benchmark

Do AI biên soạn và đối chiếu văn bản; học viên đã xác nhận trong `student_review.json`. Dev/test đã có kết quả trong `starter/results/benchmark/`. Không dùng đáp án/evidence làm đầu vào tìm kiếm.

## q01 · dev · trang PDF 2

Người con trai trong gia đình viên ngoại họ Vương tên là gì?

**Đáp án:** Vương Quan.

**Evidence nguyên văn:**

> 13. Một trai con thứ rốt lòng,
> 14. Vương Quan là chữ, nối dòng nho gia.

## q02 · dev · trang PDF 3

Trong phạm vi 1.000 dòng thơ đầu của bản trích xuất, tiết Thanh minh diễn ra vào tháng nào, gồm lễ và hội gì?

**Đáp án:** Tháng ba; lễ tảo mộ và hội đạp Thanh.

**Evidence nguyên văn:**

> 43. Thanh minh trong tiết tháng ba,
> 44. Lễ là tảo mộ, hội là đạp Thanh.

**Filter đầu vào:** `{"verse_start": {"lte": 1000}, "verse_end": {"gte": 1}}`

## q03 · dev · trang PDF 4

Theo lời Vương Quan kể khi gặp ngôi mộ, Đạm Tiên trước kia làm nghề gì?

**Đáp án:** Đạm Tiên là ca nhi.

**Evidence nguyên văn:**

> 61. Vương Quan mới dẫn gần xa:
> 62. Đạm Tiên nàng ấy xưa là ca nhi.

## q04 · dev · trang PDF 9

Chàng trai mang họ Kim, tên Trọng được giới thiệu có xuất thân như thế nào?

**Đáp án:** Xuất thân nhà trâm anh, nền phú hậu, bậc tài danh.

**Evidence nguyên văn:**

> Nguyên người quanh quất đâu xa,
> Họ Kim tên Trọng vốn nhà trâm anh.
> Nền phú hậu, bậc tài danh,

## q05 · dev · trang PDF 12

Trong giấc chiêm bao, Kiều viết bao nhiêu khúc ngâm sau khi nhận đề bài?

**Đáp án:** Mười khúc ngâm.

**Evidence nguyên văn:**

> Kiều vâng lĩnh ý đề bài,
> Tay tiên một vẫy đủ mười khúc ngâm.

## q06 · dev · trang PDF 20

Sau khi nhận lời thủy chung, những vật nào được trao tay làm tín vật?

**Đáp án:** Kim thoa và khăn hồng.

**Evidence nguyên văn:**

> Một lời vâng tạc đá vàng thủy chung!”
> Được lời như cởi tấm lòng,
> Giở kim thoa với khăn hồng trao tay,

## q07 · dev · trang PDF 30

Khi từ chối sự vội vàng trong tình yêu, Kiều nói nếu còn thân thì sau này có thể làm gì?

**Đáp án:** Có thể đền bồi về sau, không cần vội ép chuyện tình duyên.

**Evidence nguyên văn:**

> Vội chi liễu ép hoa nài,
> Còn thân ắt lại đền bồi có khi!

## q08 · dev · trang PDF 35

Khi phải lựa chọn giữa tình và hiếu, Kiều quyết định làm gì để cứu cha?

**Đáp án:** Đặt ơn sinh thành lên trước và bán mình chuộc cha.

**Evidence nguyên văn:**

> Duyên hội ngộ, đức cù lao,
> Bên tình bên hiếu, bên nào nặng hơn?
> Để lời thệ hải minh sơn,
> Làm con trước phải đền ơn sinh thành.
> 
> 605.
> Quyết tình nàng mới hạ tình:
> Dẽ cho để thiếp bán mình chuộc cha!

## q09 · dev · trang PDF 60

Không gian bốn bề quanh lầu Ngưng Bích được miêu tả với những cảnh vật nào?

**Đáp án:** Non xa, trăng gần, cát vàng và bụi hồng.

**Evidence nguyên văn:**

> Trước lầu Ngưng bích khóa xuân,
> Vẻ non xa, tấm trăng gần, ở chung.
> 
> 1035.
> Bốn bề bát ngát xa trông,
> Cát vàng cồn nọ, bụi hồng dặm kia.

## q10 · dev · trang PDF 80

Việc chuộc Kiều khỏi Tú bà được miêu tả bằng những bước trao đổi và thủ tục nào?

**Đáp án:** Trao của rõ ràng, hoàn lương vào cửa công; cả việc công và tư đều xong.

**Evidence nguyên văn:**

> Rõ ràng của dẫn tay trao,
> Hoàn lương một thiếp thân vào cửa công.
> Công tư đôi lẽ đều xong,
> 
> 1380.
> Gót tiên phút đã thoát vòng trần ai.

## q11 · dev · trang PDF 90

Trong phạm vi dòng thơ trích xuất 1.001–2.000, người nói “Giấu ta ta cũng liệu bài giấu cho” ví tình thế đối phương với hình ảnh nào?

**Đáp án:** Kiến trong miệng chén, không thể bò đi đâu.

**Evidence nguyên văn:**

> Tính rằng cách mặt khuất lời,
> Giấu ta ta cũng liệu bài giấu cho!
> Lo gì việc ấy mà lo,
> Kiến trong miệng chén có bò đi đâu?

**Filter đầu vào:** `{"verse_start": {"lte": 2000}, "verse_end": {"gte": 1001}}`

## q12 · dev · trang PDF 100

Khi nhân vật vừa tỉnh lại và bị gọi lên hầu, tấm bài treo trong tòa nhà ghi những chữ gì?

**Đáp án:** Thiên Quan Trủng Tể.

**Evidence nguyên văn:**

> Ngước trông tòa rộng dãy dài,
> Thiên Quan Trủng Tể có bài treo trên.

## q13 · dev · trang PDF 110

Tiểu thư giao cho ai việc tra hỏi thực tình khi thấy người hầu xót xa?

**Đáp án:** Thúc Sinh.

**Evidence nguyên văn:**

> Tiểu thư hỏi lại Thúc Sinh:
> 
> 1890.
> Cậy chàng tra lấy thực tình cho nao!

## q14 · dev · trang PDF 120

Điều gì ở đồ chuông khánh khiến Giác Duyên lo lường và hỏi lại lai lịch của nàng?

**Đáp án:** Khách đàn việt nhận xét đồ chuông khánh giống của nhà Hoạn nương.

**Evidence nguyên văn:**

> Giở đồ chuông khánh xem qua,
> Khen rằng: Khéo giống của nhà Hoạn nương!
> Giác Duyên thực ý lo lường,
> Đêm thanh mới hỏi lại nàng trước sau.

## q15 · dev · trang PDF 130

Trong phạm vi dòng thơ trích xuất 2.001–3.254, người sắp ra đi lấy lý do bốn bể không nhà để khuyên người ở lại thế nào, và hẹn chờ bao lâu?

**Đáp án:** Theo đi sẽ thêm bận; hãy chờ ít lâu, chậm thì một năm.

**Evidence nguyên văn:**

> Bằng ngay bốn bể không nhà,
> Theo càng thêm bận, biết là đi đâu?
> Đành lòng chờ đó ít lâu,
> Chầy chăng là một năm sau vội gì?

**Filter đầu vào:** `{"verse_start": {"lte": 3254}, "verse_end": {"gte": 2001}}`

## q16 · test · trang PDF 140

Khi từ biệt sau việc báo phục, Giác Duyên dự đoán bao lâu nữa sẽ gặp lại?

**Đáp án:** Trong năm năm.

**Evidence nguyên văn:**

> Sư rằng: Cũng chẳng bao lâu,
> Trong năm năm lại gặp nhau đó mà.

## q17 · test · trang PDF 150

Trong phạm vi dòng thơ trích xuất 2.001–3.254, khúc đàn được hỏi tên là khúc gì và được phổ vào đàn từ khi nào?

**Đáp án:** Khúc Bạc mệnh; được phổ vào đàn từ những ngày còn thơ.

**Evidence nguyên văn:**

> Thưa rằng: Bạc mệnh khúc này,
> Phổ vào đàn ấy những ngày còn thơ.

**Filter đầu vào:** `{"verse_start": {"lte": 3254}, "verse_end": {"gte": 2001}}`

## q18 · test · trang PDF 160

Kim Trọng đã ở đất Liêu Dương bao lâu trước khi trở về và sang vườn Thúy dò la?

**Đáp án:** Nửa năm.

**Evidence nguyên văn:**

> Nỗi chàng Kim Trọng bấy chầy mới thương.
> Từ ngày muôn dặm phù tang,
> Nửa năm ở đất Liêu dương lại nhà.
> Vội sang vườn Thúy dò la,

## q19 · test · trang PDF 170

Trong lời kể của Thúc Sinh, đại vương tên Hải họ gì, và gặp nàng ở đâu?

**Đáp án:** Họ Từ; gặp nàng ở châu Thai.

**Evidence nguyên văn:**

> Đại vương tên Hải họ Từ,
> 
> 2920.
> Đánh quen trăm trận sức dư muôn ngườị
> Gặp nàng khi ở châu Thai,

## q20 · test · trang PDF 189

Ở lời kết tác phẩm, chữ tâm được đặt cao hơn chữ tài như thế nào?

**Đáp án:** Một chữ tâm bằng ba chữ tài.

**Evidence nguyên văn:**

> Thiện căn ở tại lòng ta,
> Chữ tâm kia mới bằng ba chữ tài.
