# Báo Cáo Nhóm: Lab 3 - Hệ Thống Agentic Mức Độ Production

- **Tên Nhóm**: [TEAM 34]
- **Thành Viên Nhóm**: [Nguyễn Gia Bảo, Trương Đức Thái, Đoàn Thư Ánh]
- **Ngày Triển Khai**: [2026-04-06]

---

## 1. Tóm Tắt Điều Hành

*Tổng quan ngắn gọn về mục tiêu của agent và tỷ lệ thành công so với chatbot baseline.*

- **Tỷ Lệ Thành Công**: [ví dụ: 85% trên 20 test case]
- **Kết Quả Chính**: [ví dụ: "Agent của nhóm xử lý được nhiều hơn 40% truy vấn nhiều bước so với chatbot baseline nhờ sử dụng đúng công cụ Search."]

---

## 2. Kiến Trúc Hệ Thống & Công Cụ

### 2.1 Triển Khai Vòng Lặp ReAct
*Sơ đồ hoặc mô tả vòng lặp Thought-Action-Observation.*

### 2.2 Định Nghĩa Công Cụ (Danh Mục)
| Tên Công Cụ | Định Dạng Đầu Vào | Trường Hợp Sử Dụng |
| :--- | :--- | :--- |
| `calc_tax` | `json` | Tính VAT dựa trên mã quốc gia. |
| `search_api` | `string` | Lấy thông tin thời gian thực từ Google Search. |

### 2.3 Nhà Cung Cấp LLM Đã Dùng
- **Chính**: [ví dụ: GPT-4o]
- **Phụ (Dự Phòng)**: [ví dụ: Gemini 1.5 Flash]

---

## 3. Bảng Điều Khiển Telemetry & Hiệu Năng

*Phân tích các chỉ số chuẩn công nghiệp thu thập trong lần chạy kiểm thử cuối cùng.*

- **Độ Trễ Trung Bình (P50)**: [ví dụ: 1200ms]
- **Độ Trễ Tối Đa (P99)**: [ví dụ: 4500ms]
- **Số Token Trung Bình Mỗi Tác Vụ**: [ví dụ: 350 tokens]
- **Tổng Chi Phí Bộ Test**: [ví dụ: $0.05]

---

## 4. Phân Tích Nguyên Nhân Gốc (RCA) - Dấu Vết Lỗi

*Phân tích sâu lý do agent thất bại.*

### Nghiên Cứu Tình Huống: [ví dụ: Hallucinated Argument]
- **Đầu Vào**: "Thuế cho 500 ở Việt Nam là bao nhiêu?"
- **Quan Sát**: Agent gọi `calc_tax(amount=500, region="Asia")` trong khi công cụ chỉ chấp nhận mã quốc gia 2 ký tự.
- **Nguyên Nhân Gốc**: System prompt thiếu đủ ví dụ `Few-Shot` cho định dạng tham số nghiêm ngặt của công cụ.

---

## 5. Nghiên Cứu Ablation & Thực Nghiệm

### Thực Nghiệm 1: Prompt v1 vs Prompt v2
- **Khác Biệt**: [ví dụ: Thêm câu "Luôn kiểm tra lại tham số công cụ trước khi gọi".]
- **Kết Quả**: Giảm lỗi gọi công cụ không hợp lệ [ví dụ: 30%].

### Thực Nghiệm 2 (Bonus): Chatbot vs Agent
| Trường Hợp | Kết Quả Chatbot | Kết Quả Agent | Bên Thắng |
| :--- | :--- | :--- | :--- |
| Câu hỏi đơn giản | Đúng | Đúng | Hòa |
| Nhiều bước | Hallucinated | Đúng | **Agent** |

---

## 6. Đánh Giá Mức Sẵn Sàng Production

*Các điểm cần cân nhắc để đưa hệ thống vào môi trường thực tế.*

- **Bảo Mật**: [ví dụ: Làm sạch đầu vào cho tham số công cụ.]
- **Cơ Chế Bảo Vệ**: [ví dụ: Tối đa 5 vòng lặp để tránh chi phí billing vô hạn.]
- **Khả Năng Mở Rộng**: [ví dụ: Chuyển sang LangGraph cho luồng rẽ nhánh phức tạp hơn.]

---

