# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Trương Đức Thái
- **Student ID**: 2A202600328
- **Date**: 06/04/2026

---

## I. Technical Contribution (15 Points)

Trong Lab 3, em tập trung vào xây dựng core của ReAct agent, tập hợp công cụ hỗ trợ, và xây dựng giao diện web để so sánh chatbot vs agent.

- **Các Module Đã Triển Khai**:
	- `Flowchart.png` - Sơ đồ kiến trúc ReAct loop (Thought → Action → Observation)
	- `trace.md` - Ghi chép chi tiết từng bước execution của agent
	- `test_cases.md` - Các test cases so sánh chatbot vs agent với output
	- `group_report/GROUP_REPORT_TEAM34.md` - Báo cáo nhóm về kết quả Lab 3

- **Điểm Nổi Bật Trong Code**:
	- **Flowchart.png**: Vẽ sơ đồ chi tiết kiến trúc ReAct loop, giúp visualize:
		- Quy trình Thought → Action → Observation → Next Thought
		- Điểm kết thúc (Final Answer)
		- Error handling paths (parse error, tool error, max iteration)
	
	- **trace.md**: Ghi chép execution trace của từng test case:
		- Log tất cả LLM outputs, tool calls, observations
		- Thể hiện quá trình suy luận của agent step-by-step
		- Phân tích các failure cases khi agent sai lầm
	
	- **test_cases.md**: Thiết kế bộ test case toàn diện:
		- Cases đơn giản (FAQ: Thủ đô Việt Nam?)
		- Cases phức tạp (so sánh thời tiết 2 thành phố)
		- Cases edge case (query mơ hồ, tool fail, LLM timeout)
		- Ghi output mong đợi vs. actual output
	
	- **GROUP_REPORT_TEAM34.md**: Báo cáo tổng hợp nhóm:
		- Phân chia công việc và timeline
		- Tóm tắt kết quả so sánh chatbot vs agent
		- Performance metrics (latency, token usage)
		- Lessons learned và recommendations

---

## II. Nghiên Cứu Tình Huống Debug (10 Điểm)

Case debug tiêu biểu em ghi lại trong `trace.md` là lỗi **agent caught in infinite loop** khi gọi cùng một tool lặp đi lặp lại với cùng arguments.

- **Mô Tả Vấn Đề**: Khi user hỏi "So sánh thời tiết Hà Nội và TP.HCM", agent gọi `weather(Hanoi)` lần 1 → nhận observation → sau đó gọi `weather(Hanoi)` lần 2 mà lẽ ra phải gọi `weather(Ho Chi Minh City)`. Hệ thống không detect duplicate và cứ lặp lại.

- **Nguồn Log**: Từ `trace.md`, ta thấy pattern này ở step 3-5 khi agent vẫn lặp lại action `weather(Hanoi)` thay vì tiến hành bước kế tiếp.

- **Chẩn Đoán**: Nguyên nhân là:
	- System prompt chưa đủ rõ ràng về logic so sánh (phải gọi 2 lần với 2 địa điểm khác nhau)
	- Agent không nhận ra đã có observation từ lần gọi trước vì prompt không nhấn mạnh "dùng kết quả đã có"
	- Loop guard trong agent.py không bắt được case này vì arguments khác (do alias - "TP.HCM" vs "Ho Chi Minh City" → vẫn cùng địa điểm nhưng string khác)

- **Giải Pháp**:
	- Cập nhật prompt với ví dụ clear hơn cho multi-step queries (gọi 2 tools khác nhau, tránh lặp)
	- Chuẩn hoá location names trong prompt (ví dụ: "use canonical names like 'Hanoi', 'Ho Chi Minh City'")
	- Lọc duplicate actions bằng location name normalize thay vì raw string matching
	- Thêm max_iterations safeguard (hiện là 6, có thể hạ xuống 5 để fail fast)

---

## III. Góc Nhìn Cá Nhân: Chatbot vs ReAct (10 Điểm)

*Phản ánh sự khác biệt về năng lực suy luận dựa trên test cases.*

1.  **Suy Luận**: Khối `Thought` giúp agent nghĩ trước khi trả lời: phân rã bài toán, lập kế hoạch, giảm đoán mò.
	→ Tốt hơn chatbot ở bài toán nhiều bước. Từ test cases, thấy rõ agent xử lý "so sánh 2 thành phố" tốt hơn chatbot (mặc dù gặp bug ở trên).

2.  **Độ Tin Cậy**: Trong các bài toán đơn giản như FAQ, câu hỏi lặp lại, hoặc ý định người dùng ổn định, chatbot tích hợp RAG thường cho kết quả nhất quán và tiết kiệm hơn. Ngược lại, nếu vẫn ép dùng agent cho các tác vụ này, hệ thống dễ rơi vào tình trạng "overkill": tăng độ trễ, tăng chi phí token và phát sinh thêm điểm lỗi do nhiều bước suy luận hoặc gọi tool không cần thiết.

3.  **Quan Sát**: `Observation` là tín hiệu phản hồi từ môi trường sau mỗi `Action`, đóng vai trò kiểm chứng kết quả trung gian. Nhờ observation, agent biết được bước vừa thực hiện đúng hay sai, dữ liệu đã đủ hay còn thiếu, từ đó điều chỉnh quyết định ở vòng lặp kế tiếp (đổi truy vấn, đổi công cụ, hoặc tinh chỉnh tham số).

---

## IV. Cải Tiến Trong Tương Lai (5 Điểm)

*Bạn sẽ mở rộng hệ thống này như thế nào để đạt mức AI agent production?*

- **Khả Năng Mở Rộng**: 
	- Chuẩn hoá interface cho tools (tool registry) để dễ thêm hoặc xoá tool mà không ảnh hưởng đến các thành phần còn lại của hệ thống.
	- Implement parallel tool execution: nếu Thought lên kế hoạch gọi 3 tools độc lập, gọi async thay vì tuần tự.

- **An Toàn**: 
	- Thêm cơ chế sandbox cho tool execution nhằm cô lập môi trường khi agent gọi tool, từ đó giảm rủi ro tác động lên hệ thống chính.
	- Rate limit + quota mỗi user tối đa N steps, M tokens/ngày để control cost.

- **Hiệu Năng**: 
	- Áp dụng batching và caching layer (cache tool outputs như weather data với TTL).
	- Token optimization: compress system prompt, truncate conversation history sau N turns.

Mục tiêu: xây dựng hệ thống linh hoạt khi mở rộng, an toàn khi vận hành và nhanh trong xử lý thực tế.

---
