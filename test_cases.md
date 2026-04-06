# Test Cases — Lab 3: Simple Chatbot vs ReAct Agent

## Thiết kế 5 Test Cases Có Mục Đích

Mỗi test case được chọn có chủ đích để chứng minh một điểm khác biệt cụ thể
giữa Simple Chatbot (1 LLM call, không có tool) và ReAct Agent (Thought → Action → Observation loop).

```
┌─────────────────────┬────────────────────────────────────────────┐
│  2 cases            │  Query đơn giản, 1 bước, không cần tool    │
│  CHATBOT ĐỦ TỐT     │  → Chatbot nhanh hơn, rẻ hơn, đủ chính xác│
├─────────────────────┼────────────────────────────────────────────┤
│  2 cases            │  Multi-step, bước sau phụ thuộc bước trước  │
│  AGENT VƯỢT TRỘI    │  → Agent tạo giá trị nhờ grounding thực tế │
├─────────────────────┼────────────────────────────────────────────┤
│  1 edge case        │  Tool fail, input mơ hồ, boundary test     │
│                     │  → Test error handling & graceful degrad.  │
└─────────────────────┴────────────────────────────────────────────┘
```

---

## TC-01 — Chatbot Đủ Tốt: Kiến thức khí hậu học

| Trường | Giá trị |
|--------|---------|
| **Query** | `Hà Nội có bao nhiêu mùa trong năm? Đặc điểm từng mùa là gì?` |
| **Loại** | Kiến thức tĩnh / địa lý khí hậu |
| **Tool cần** | Không |
| **Kết quả kỳ vọng (Chatbot)** | Trả lời chính xác và đầy đủ (4 mùa, đặc điểm từng mùa) |
| **Kết quả kỳ vọng (Agent)** | Cũng đúng, nhưng tốn thêm 1-2 LLM call không cần thiết |

**Tại sao chọn test case này?**
- Thông tin về số lượng mùa và đặc điểm khí hậu là kiến thức ổn định, không thay đổi hàng ngày.
- Chatbot có trong training data → trả lời ngay, nhanh hơn, rẻ hơn.
- Agent đôi khi vẫn cố gọi weather tool → lãng phí step không cần thiết.
- **Kết luận**: Simple = tốt hơn với câu hỏi kiến thức tĩnh.

**Kết quả mẫu:**

```
Chatbot: Hà Nội có 4 mùa rõ rệt:
  - Xuân (tháng 2-4): ấm áp, ẩm, mưa phùn.
  - Hạ (tháng 5-8): nóng ~32-36°C, mưa nhiều.
  - Thu (tháng 9-11): mát mẻ ~22-28°C, khô thoáng.
  - Đông (tháng 12-1): lạnh ~12-18°C, ít mưa.
Latency: ~800ms | 1 LLM call

Agent: [Thought] Đây là câu hỏi kiến thức khí hậu...
       [Final Answer] Hà Nội có 4 mùa... (kết quả tương đương)
Latency: ~1500ms | 2 LLM calls (lãng phí)
```

---

## TC-02 — Chatbot Đủ Tốt: Mùa du lịch tốt nhất

| Trường | Giá trị |
|--------|---------|
| **Query** | `Tháng mấy là thời điểm đẹp nhất để du lịch Đà Lạt và tại sao?` |
| **Loại** | Tư vấn du lịch dựa trên kiến thức mùa vụ |
| **Tool cần** | Không |
| **Kết quả kỳ vọng (Chatbot)** | Tháng 11-12 (mùa khô, hoa nở), lý giải rõ ràng |
| **Kết quả kỳ vọng (Agent)** | Có thể gọi weather tool nhưng không cần thiết |

**Tại sao chọn test case này?**
- Câu hỏi về "tháng đẹp nhất" là kiến thức mùa vụ, không phụ thuộc thời tiết hôm nay.
- Chatbot biết rõ Đà Lạt tháng 11-12 là mùa khô, hoa dã quỳ nở.
- Agent có thể lấy dự báo hiện tại nhưng không giúp ích gì cho câu hỏi về "tháng đẹp nhất trong năm".
- **Kết luận**: Chatbot rẻ hơn và đủ chính xác cho loại câu hỏi này.

---

## TC-03 — Agent Vượt Trội: So sánh thực tế 2 thành phố

| Trường | Giá trị |
|--------|---------|
| **Query** | `So sánh nhiệt độ hiện tại của Hà Nội và Hồ Chí Minh. Chênh lệch bao nhiêu độ?` |
| **Loại** | Multi-step, real-time, tính toán |
| **Tool cần** | `weather` (×2) → `calculator` |
| **Kết quả kỳ vọng (Chatbot)** | Ước tính "HCM thường nóng hơn HN ~5-8°C" (có thể sai) |
| **Kết quả kỳ vọng (Agent)** | Lấy nhiệt độ thực tế cả 2, tính chênh lệch chính xác |

**Tại sao chọn test case này?**
- Đây là **multi-step query**: bước 3 (tính chênh lệch) phụ thuộc vào kết quả bước 1 và bước 2.
- Chatbot chỉ có 1 call → bịa hoặc ước tính dựa vào kiến thức mùa vụ → không chính xác.
- Agent thực hiện:
  ```
  Step 1: Action: weather(Hanoi)       → Observation: 29°C
  Step 2: Action: weather(Ho Chi Minh) → Observation: 34°C
  Step 3: Action: calculator(34-29)    → Observation: 5
  Final Answer: HCM nóng hơn HN 5°C
  ```
- **Kết luận**: Agent tạo giá trị nhờ **grounding** (dữ liệu thực tế) và **chaining** (kết quả step sau phụ thuộc step trước).

---

## TC-04 — Agent Vượt Trội: Dự báo 2 điểm + tư vấn lựa chọn

| Trường | Giá trị |
|--------|---------|
| **Query** | `Tôi muốn đi Đà Nẵng hoặc Nha Trang cuối tuần này. Dự báo 3 ngày tới ở cả 2 nơi thế nào? Gợi ý tôi nên chọn đâu.` |
| **Loại** | Multi-step, forecast, decision support |
| **Tool cần** | `weather` (forecast Da Nang) → `weather` (forecast Nha Trang) → tư vấn |
| **Kết quả kỳ vọng (Chatbot)** | Tư vấn chung theo mùa (không có dự báo thực 3 ngày) |
| **Kết quả kỳ vọng (Agent)** | Dự báo thực tế cả 2 địa điểm, tư vấn dựa trên dữ liệu cụ thể |

**Tại sao chọn test case này?**
- Step 3 (tư vấn) **phụ thuộc hoàn toàn** vào kết quả Step 1 và Step 2.
- Nếu Đà Nẵng mưa 3 ngày nhưng Nha Trang nắng → Agent gợi ý Nha Trang.
- Chatbot không có dữ liệu thực tế → chỉ nói "Nha Trang tháng 4 ít mưa hơn" (generic, có thể sai).
- **Kết luận**: Agent cho phép **decision support có grounding**, giá trị rõ ràng hơn chatbot.

**Trace mẫu:**
```
User: Tôi muốn đi Đà Nẵng hoặc Nha Trang cuối tuần này...

Thought: Cần lấy dự báo 3 ngày của Đà Nẵng trước.
Action: weather(Da Nang 3-day forecast)
Observation: Thứ 6: Mưa 70%, 26°C. Thứ 7: Mưa 60%, 25°C. CN: Nắng, 29°C.

Thought: Bây giờ lấy dự báo 3 ngày của Nha Trang.
Action: weather(Nha Trang 3-day forecast)
Observation: Thứ 6: Nắng, 30°C. Thứ 7: Nắng, 31°C. CN: Nắng nhẹ, 30°C.

Thought: Đà Nẵng 2/3 ngày mưa, Nha Trang nắng cả tuần.
Final Answer: Nên chọn Nha Trang — 3 ngày tới đều nắng đẹp, thích hợp tắm biển.
  Đà Nẵng có mưa thứ 6 và thứ 7, chỉ CN mới nắng.
```

---

## TC-05 — Edge Case: Input mơ hồ, thiếu địa điểm

| Trường | Giá trị |
|--------|---------|
| **Query** | `Cho tôi biết thời tiết hôm nay.` |
| **Loại** | Boundary test — thiếu thông tin đầu vào |
| **Tool cần** | `weather` (nhưng không biết location) |
| **Kết quả kỳ vọng (Chatbot)** | Trả lời chung chung hoặc hỏi lại địa điểm |
| **Kết quả kỳ vọng (Agent)** | Tool fail / hỏi lại người dùng / graceful degradation |

**Tại sao chọn test case này?**
- Test **graceful degradation**: cả 2 hệ thống phải xử lý input thiếu thông tin.
- Chatbot có thể bịa địa điểm mặc định hoặc nói chung chung → không hữu ích.
- Agent nên:
  - Nhận ra thiếu location
  - Hỏi lại người dùng: "Bạn muốn xem thời tiết ở đâu?"
  - Hoặc nếu tool trả về lỗi → graceful fallback
- **Kết luận**: Test khả năng xử lý lỗi và ambiguous input.

**Kịch bản Agent xử lý tốt:**
```
Thought: Query thiếu địa điểm cụ thể. Không thể gọi weather tool.
Final Answer: Bạn muốn xem thời tiết ở đâu? Hãy cho tôi biết tên thành phố 
  (ví dụ: Hà Nội, Đà Nẵng, TP. Hồ Chí Minh...).
```

**Kịch bản Agent xử lý kém:**
```
Action: weather()   ← gọi tool với args rỗng
Observation: Error: location parameter required
[Lặp lại nhiều lần → hit max_iterations → "Đã đạt giới hạn bước"]
```

---

## Bảng Tổng Kết

| ID | Loại | Query | Chatbot | Agent | Winner |
|----|------|-------|---------|-------|--------|
| TC-01 | Kiến thức tĩnh | Mùa của Hà Nội | ✅ Đúng, ~800ms | ✅ Đúng, ~1500ms | 🔵 Chatbot (nhanh hơn) |
| TC-02 | Tư vấn mùa vụ | Tháng đẹp Đà Lạt | ✅ Đúng, ~700ms | ✅ Đúng, ~1400ms | 🔵 Chatbot (rẻ hơn) |
| TC-03 | Real-time + tính | So sánh HN vs HCM | ❌ Ước tính sai | ✅ Chính xác 100% | 🟢 Agent (grounding) |
| TC-04 | Multi-step forecast | Đà Nẵng vs Nha Trang | ❌ Generic | ✅ Decision support | 🟢 Agent (chaining) |
| TC-05 | Edge case | Input mơ hồ | ⚠️ Bịa/chung chung | ⚠️ Tool fail/hỏi lại | 🔴 Test degradation |

**Takeaway:**
- Chatbot phù hợp cho câu hỏi kiến thức, nhanh và rẻ.
- Agent tạo giá trị khi cần dữ liệu thực tế và multi-step reasoning.
- Edge case kiểm tra độ bền của cả 2 hệ thống.
