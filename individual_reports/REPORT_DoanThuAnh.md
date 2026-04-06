# Báo Cáo Cá Nhân: Lab 3 - Chatbot vs ReAct Agent

- **Tên Sinh Viên**: [Đoàn Thư Ánh]
- **Mã Số Sinh Viên**: [2A202600364]
- **Ngày**: [06/04/2026]

---

## I. Đóng Góp Kỹ Thuật (15 Điểm)

Trong Lab 3, em tập trung vào 4 phần: chuẩn hoá lớp provider để đổi LLM linh hoạt, xây dựng baseline chatbot 1 lần gọi model, thiết kế structured logger phục vụ quan sát hệ thống, và viết script phân tích lỗi từ log để phục vụ RCA.

- **Các Module Đã Triển Khai**:
	- `lab3/provider.py`
	- `lab3/chatbot.py`
	- `lab3/logger.py`
	- `lab3/analyze_logs.py`
- **Điểm Nổi Bật Trong Code**:
	- Thiết kế interface `LLMProvider` và factory `build_provider()` để chuyển OpenAI/Gemini mà không đổi logic nghiệp vụ.
	- Trong `GeminiProvider`, lọc các kwargs không tương thích (`logprobs`, `top_logprobs`) trước khi gọi API, giúp giảm lỗi runtime khi đổi provider.
	- Hàm `chat()` trong chatbot ghi đầy đủ vòng đời request (`CHATBOT_START`, `CHATBOT_RESPONSE`, `CHATBOT_ERROR`) kèm latency và token usage để đo hiệu năng.
	- `logger.py` ghi log JSON theo từng dòng, có `timestamp` UTC, `event`, `data`; định dạng này tương thích trực tiếp với script phân tích.
	- `analyze_logs.py` tổng hợp event counts, chatbot/agent stats, tool usage, failure traces và cảnh báo hallucination candidates cho câu hỏi real-time.
- **Tài Liệu**: Các module trên tạo thành pipeline quan sát hoàn chỉnh cho ReAct loop: khi agent hoặc chatbot chạy sẽ ghi event vào logs; sau đó `analyze_logs.py` đọc và thống kê các event `AGENT_PARSE_ERROR`, `AGENT_LLM_ERROR`, `AGENT_LOOP_DETECTED`, `CHATBOT_ERROR` để xác định nguyên nhân thất bại và đo mức cải thiện sau khi chỉnh prompt/tool.

---

## II. Nghiên Cứu Tình Huống Debug (10 Điểm)

Case debug tiêu biểu em tập trung là lỗi `AGENT_PARSE_ERROR`, khi model trả về output không đúng format ReAct nên hệ thống không parse được `Action` hợp lệ.

- **Mô Tả Vấn Đề**: Ở một số truy vấn nhiều bước, agent sinh câu trả lời tự do thay vì block hành động đúng schema (`Thought`/`Action`/`Action Input`), dẫn tới parser không trích xuất được tool call.
- **Nguồn Log**: Dựa trên thiết kế structured logging của hệ thống, trong đó event `AGENT_PARSE_ERROR` lưu thông tin `step` và `raw_output`; các event này được tổng hợp bởi hàm `failure_cases()` trong `analyze_logs.py` để phục vụ phân tích lỗi.
- **Chẩn Đoán**: Nguyên nhân chính đến từ ràng buộc format trong prompt chưa đủ chặt và khác biệt hành vi giữa provider/model ở các bước reasoning. Khi output trung gian không tuân thủ cấu trúc chuẩn, parser báo lỗi dù ý định của model có thể đúng về ngữ nghĩa.
- **Giải Pháp**:
	- Tăng tính ràng buộc trong system prompt: yêu cầu bắt buộc định dạng ReAct ở mọi step.
	- Thêm ví dụ few-shot cho cả trường hợp đúng và sai format để model bám schema ổn định hơn.
	- Dùng `analyze_logs.py` để theo dõi giảm dần các event `AGENT_PARSE_ERROR` sau mỗi lần chỉnh prompt.
	- Giữ loop guard (`AGENT_LOOP_DETECTED`) để ngăn chi phí tăng khi parse lỗi lặp lại.

---

## III. Góc Nhìn Cá Nhân: Chatbot vs ReAct (10 Điểm)

*Phản ánh sự khác biệt về năng lực suy luận.*

1.  **Suy Luận**: Khối `Thought` giúp agent nghĩ trước khi trả lời: phân rã bài toán, lập kế hoạch, giảm đoán mò.
→ Tốt hơn chatbot ở bài toán nhiều bước.
2.  **Độ Tin Cậy**: Trong các bài toán đơn giản như FAQ, câu hỏi lặp lại, hoặc ý định người dùng ổn định, chatbot tích hợp RAG thường cho kết quả nhất quán và tiết kiệm hơn. Ngược lại, nếu vẫn ép dùng agent cho các tác vụ này, hệ thống dễ rơi vào tình trạng "overkill": tăng độ trễ, tăng chi phí token và phát sinh thêm điểm lỗi do nhiều bước suy luận hoặc gọi tool không cần thiết. Tóm lại, với nhóm bài toán có quy trình trả lời rõ ràng, chatbot là lựa chọn đáng tin cậy và hiệu quả hơn.
3.  **Quan Sát**: Trong mô hình ReAct, `Observation` là tín hiệu phản hồi từ môi trường sau mỗi `Action`, đóng vai trò kiểm chứng kết quả trung gian. Nhờ observation, agent biết được bước vừa thực hiện đúng hay sai, dữ liệu đã đủ hay còn thiếu, từ đó điều chỉnh quyết định ở vòng lặp kế tiếp (đổi truy vấn, đổi công cụ, hoặc tinh chỉnh tham số). Cơ chế này giúp giảm lặp lỗi, tăng khả năng tự sửa sai và cải thiện chất lượng câu trả lời cuối cùng.

---

## IV. Cải Tiến Trong Tương Lai (5 Điểm)

*Bạn sẽ mở rộng hệ thống này như thế nào để đạt mức AI agent production?*

- **Khả Năng Mở Rộng**: Chuẩn hoá interface cho tools (tool registry) để dễ thêm hoặc xoá tool mà không ảnh hưởng đến các thành phần còn lại của hệ thống.
- **An Toàn**: Thêm cơ chế sandbox cho tool execution nhằm cô lập môi trường khi agent gọi tool, từ đó giảm rủi ro tác động lên hệ thống chính.
- **Hiệu Năng**: Áp dụng batching và parallel tool calls để gọi nhiều tool đồng thời thay vì tuần tự, giúp rút ngắn thời gian xử lý trong các tác vụ nhiều bước.

Mục tiêu: xây dựng hệ thống linh hoạt khi mở rộng, an toàn khi vận hành và nhanh trong xử lý thực tế.

---
