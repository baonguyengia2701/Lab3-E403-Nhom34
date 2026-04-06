# Trace: TC-05 — Compound Math + Date Query

**Query**: `If I save 500,000 VND per day starting today, how much will I have saved by January 1, 2027?`

**Model**: GPT-4o | **Date run**: 2026-04-06 | **Max iterations**: 5

---

## Full Thought → Action → Observation Trace

```
User: If I save 500,000 VND per day starting today, how much will I have saved by January 1, 2027?

─── Step 1 ───────────────────────────────────────────────────────
Thought: To answer this, I first need to know how many days there
         are from today until January 1, 2027.
Action: datetime(days_until:2027-01-01)
Observation: There are 270 days remaining until 2027-01-01.

─── Step 2 ───────────────────────────────────────────────────────
Thought: I now know there are 270 days. I need to multiply this
         by 500,000 VND per day to get the total savings.
Action: calculator(270 * 500000)
Observation: 135000000

─── Step 3 ───────────────────────────────────────────────────────
Thought: The calculation is complete. 270 days × 500,000 VND = 135,000,000 VND.
Final Answer: Starting today (April 6, 2026), if you save 500,000 VND
              per day, you will have saved 135,000,000 VND (135 million VND)
              by January 1, 2027 — over the course of 270 days.
```

---

## Tóm tắt

| Thông số | Giá trị |
|:---------|:--------|
| Steps used | 2 / 5 |
| Tools called | `datetime`, `calculator` |
| Total latency | ~2,100 ms |
| Total tokens | ~420 |
| Success | ✅ Yes |

---

## So sánh với SimpleChatbot

**SimpleChatbot output** (cùng câu hỏi):

> *"If you save 500,000 VND per day, by January 1, 2027, you would have saved approximately 182,500,000 VND (assuming 365 days). However, the exact amount depends on today's date."*

**Vấn đề của Chatbot**:
1. Giả định sai số ngày (365 ngày thay vì 270 ngày thực tế).
2. Kết quả sai: 182,500,000 VND thay vì 135,000,000 VND.
3. Thêm disclaimer "depends on today's date" — tức là biết mình không chắc nhưng vẫn đoán.

---

## Phân tích lỗi tiềm năng (Failure Analysis)

### Lỗi 1: Parse Error

Nếu LLM xuất output không đúng format, ví dụ:

```
Thought: Let me calculate this...
I'll use the calculator: calculator(270 * 500000)   ← thiếu "Action:" prefix
```

→ Agent sẽ log `AGENT_PARSE_ERROR` và inject hint:
```
Observation: [System] Không parse được Action. Hãy dùng đúng format: Action: tool_name(args)
```

→ LLM được nhắc nhở và thử lại ở bước tiếp theo.

### Lỗi 2: Infinite Loop

Nếu LLM gọi cùng một tool hai lần:
```
Action: datetime(days_until:2027-01-01)   ← step 1
Action: datetime(days_until:2027-01-01)   ← step 3 (lặp lại)
```

→ `seen_actions` list phát hiện, inject warning:
```
Observation: [System] Bạn đã gọi datetime(days_until:2027-01-01) rồi.
             Hãy dùng kết quả đã có hoặc viết Final Answer.
```

### Lỗi 3: Hallucinated Tool

Nếu LLM gọi tool không tồn tại:
```
Action: web_search(current VND to USD rate)
```

→ `_execute_tool` trả về:
```
Observation: Tool 'web_search' không tìm thấy. Các tool có sẵn: ['calculator', 'datetime', 'unit_converter'].
```

---

## Kết luận từ trace này

- **ReAct thực sự cần thiết** cho bài toán này: không có cách nào Chatbot biết "hôm nay là ngày mấy" mà không có tool.
- **Mỗi Observation là grounding**: Sau khi nhận `270 days`, LLM không cần đoán — nó có dữ liệu cụ thể để tính tiếp.
- **Tính minh bạch**: Mọi bước lý luận đều có thể kiểm tra trong trace — đây là ưu điểm lớn so với Chatbot (black-box).
