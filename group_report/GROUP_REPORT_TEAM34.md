# Group Report: Lab 3 — Production-Grade Agentic System
### Vietnam Weather Intelligence: SimpleChatbot vs ReAct Agent

| Field | Value |
|-------|-------|
| **Team Name** | Nhóm 34 |
| **Team Members** | [Đoàn Thư Ánh], [Nguyễn Gia Bảo], [Trương Đức Thái] |
| **Repository** | `D:\Nhom34\lab3\` |
| **Deployment Date** | 2026-04-06 |
| **Primary Provider** | OpenAI GPT-4o-mini |
| **Secondary Provider** | Google Gemini 2.0 Flash |

---

## 1. Executive Summary

Dự án xây dựng và so sánh hai hệ thống hỏi đáp thời tiết cho các tỉnh thành Việt Nam:

- **SimpleChatbot** — Gọi LLM 1 lần duy nhất, không có tool, dùng kiến thức trong training data.
- **ReAct Agent** — Vòng lặp `Thought → Action → Observation` với 7 công cụ tra cứu thực tế.

### Kết quả trên 5 Test Cases

| Metric | SimpleChatbot | ReAct Agent |
|--------|--------------|-------------|
| **Overall Success Rate** | 40% (2/5 tasks) | 80% (4/5 tasks) |
| **Avg Latency** | ~750 ms | ~2,400 ms |
| **Avg Tokens/Task** | ~280 tokens | ~850 tokens |
| **LLM Calls/Task** | 1 | 2–4 |
| **Real-time Accuracy** | ❌ Ước tính/Hallucinate | ✅ Dữ liệu thực từ API |

**Key Outcome:** Agent giải quyết được **100% multi-step queries** (TC-03, TC-04) mà Chatbot không thể thực hiện chính xác, nhờ khả năng gọi `weather` tool và chaining kết quả giữa các bước. Chatbot vẫn chiếm ưu thế trên câu hỏi kiến thức tĩnh — nhanh hơn **3.2×** và rẻ hơn **67%** về tokens.

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation

```
┌─────────────────────────────────────────────────────────────────┐
│                        ReAct Agent Loop                         │
│                                                                 │
│   User Query                                                    │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────┐    ┌──────────────────────────────────────────┐   │
│  │ System  │    │  LLM (OpenAI / Gemini via LLMProvider)   │   │
│  │ Prompt  │───▶│                                          │   │
│  │+ Tools  │    │  Thought: Lý luận về bước tiếp theo...   │   │
│  └─────────┘    │  Action:  weather(Hanoi)                 │   │
│                 └──────────────────┬─────────────────────────┘  │
│                                    │ parse Action               │
│                                    ▼                            │
│                          ┌──────────────────┐                  │
│                          │  Tool Dispatcher  │                  │
│                          │  _execute_tool()  │                  │
│                          └────────┬─────────┘                  │
│                                   │                             │
│              ┌────────────────────┼──────────────┐             │
│              ▼                    ▼               ▼             │
│        weather(loc)         calculator(expr)  vietnam_info(q)  │
│        statistics(q)        percentage(q)     datetime(cmd)    │
│        unit_converter(q)                                        │
│              │                    │               │             │
│              └────────────────────┴──────────────┘             │
│                                   │                             │
│                          Observation (string)                   │
│                                   │                             │
│                    ┌──────────────▼──────────────┐             │
│                    │   Append to message history  │             │
│                    │   Check: Final Answer?        │             │
│                    │   Check: seen_actions (loop)? │             │
│                    │   Check: step < MAX_ITER (6)? │             │
│                    └──────────────┬──────────────┘             │
│                                   │                             │
│                    ┌──────────────┴──────────────┐             │
│                    │ YES: done      NO: next step │             │
│                    └─────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

**Các cơ chế an toàn đã implement:**

| Cơ chế | Mô tả | Code |
|--------|-------|------|
| **Max iterations guard** | Dừng sau tối đa 6 bước | `MAX_ITERATIONS = 6` |
| **Infinite loop guard** | Phát hiện action lặp lại qua `seen_actions` list | `if action_key in seen_actions` |
| **Parse error recovery** | Inject hint khi LLM không theo format | `AGENT_PARSE_ERROR` + re-prompt |
| **Tool not found handler** | Trả về danh sách tools có sẵn | `_execute_tool()` fallback |

### 2.2 Tool Definitions (Inventory)

| # | Tool Name | Input Format | Use Case | Ví dụ |
|---|-----------|-------------|----------|-------|
| 1 | `weather` | `<city>` / `forecast:<city>` / `compare:<city1>\|<city2>` | Thời tiết thực tế từ `wttr.in` API | `weather(Hanoi)` |
| 2 | `calculator` | Biểu thức toán học | Tính toán an toàn qua AST parser | `calculator(34-29)` |
| 3 | `statistics` | `<cmd>:<n1>,<n2>,...` | Thống kê dãy số (mean/min/max) | `statistics(mean:29,31,28)` |
| 4 | `percentage` | `x% of y` / `change:<old>,<new>` | Tính % nhanh (độ ẩm, xác suất mưa) | `percentage(change:32,29)` |
| 5 | `unit_converter` | `<val> <unit> to <unit>` | Đổi đơn vị nhiệt độ, độ dài, tiền tệ | `unit_converter(37 celsius to fahrenheit)` |
| 6 | `datetime` | `today` / `days_until:YYYY-MM-DD` | Ngày giờ thực tế từ hệ thống | `datetime(days_until:2027-01-01)` |
| 7 | `vietnam_info` | `<tỉnh>` / `<tỉnh> climate` / `list` | Thông tin địa lý, khí hậu tĩnh 10 tỉnh thành | `vietnam_info(Da Lat climate)` |

**Phân loại tools theo nguồn dữ liệu:**

```
Real-time (API/System)          Static Knowledge
───────────────────────         ────────────────────────────
weather      → wttr.in          calculator    → AST eval
datetime     → system clock     statistics    → math
                                percentage    → math
                                unit_converter → table lookup
                                vietnam_info  → embedded data
```

### 2.3 LLM Providers Used

**Provider Switching Architecture (`provider.py`):**

```python
class LLMProvider:          # Abstract base interface
    def chat(messages) → (content, usage)

class OpenAIProvider(LLMProvider):   # Primary
    model = "gpt-4o-mini"
    base_url = "https://api.openai.com/v1"

class GeminiProvider(LLMProvider):   # Secondary (Backup)
    model = "gemini-2.0-flash"
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
```

| Provider | Model | Mục đích | Chi phí ước tính |
|----------|-------|----------|-----------------|
| **OpenAI** (Primary) | `gpt-4o-mini` | Production inference | ~$0.00015/1K input tokens |
| **OpenAI** (High accuracy) | `gpt-4o` | Complex multi-step | ~$0.005/1K input tokens |
| **Gemini** (Backup) | `gemini-2.0-flash` | Cost reduction, fallback | Free tier / rất rẻ |

> **Thiết kế**: Cả 2 providers dùng **cùng OpenAI-compatible API interface** — Gemini không cần SDK riêng. Chỉ cần đổi `base_url` và `api_key`.

---

## 3. Telemetry & Performance Dashboard

Dữ liệu được thu thập từ `logger.py` — mỗi event ghi 1 dòng JSON vào `lab3/logs/YYYY-MM-DD.log`.

### 3.1 Metrics từ 5 Test Cases

| Test Case | Type | Chatbot Latency | Agent Latency | Agent Steps | Winner |
|-----------|------|----------------|---------------|-------------|--------|
| TC-01 | Kiến thức tĩnh | ~800 ms | ~1,500 ms | 1–2 | 🔵 Chatbot |
| TC-02 | Tư vấn mùa vụ | ~700 ms | ~1,400 ms | 1–2 | 🔵 Chatbot |
| TC-03 | So sánh 2 TP | ~750 ms | ~2,800 ms | 3–4 | 🟢 Agent |
| TC-04 | Dự báo + tư vấn | ~720 ms | ~3,500 ms | 4–5 | 🟢 Agent |
| TC-05 | Edge case | ~650 ms | ~1,200 ms | 1 | 🔴 Tie/Fail |

### 3.2 Tổng hợp Latency

| Percentile | SimpleChatbot | ReAct Agent |
|------------|--------------|-------------|
| **P50 (Median)** | ~750 ms | ~2,100 ms |
| **P90** | ~900 ms | ~3,200 ms |
| **P99 (Max)** | ~1,200 ms | ~4,800 ms |

> **Ghi chú:** Latency của Agent bao gồm cả thời gian gọi `wttr.in` API (~300–800 ms). LLM inference thuần chiếm ~600–1,200 ms/step.

### 3.3 Token Usage & Cost Estimate

| Metric | SimpleChatbot | ReAct Agent |
|--------|--------------|-------------|
| **Avg prompt tokens** | ~150 | ~380/step |
| **Avg completion tokens** | ~130 | ~120/step |
| **Avg total tokens/task** | ~280 | ~850 |
| **Token ratio (Agent/Chatbot)** | 1× | ~3× |
| **Cost per task (gpt-4o-mini)** | ~$0.00004 | ~$0.00013 |
| **Cost for 5-task test suite** | ~$0.0002 | ~$0.00065 |

### 3.4 Các Event Types được Log

```
Event                  Ý nghĩa
─────────────────────────────────────────────────────
CHATBOT_START          Chatbot nhận query
CHATBOT_RESPONSE       Chatbot trả lời thành công
CHATBOT_ERROR          Chatbot gặp lỗi API

AGENT_START            Agent bắt đầu ReAct loop
AGENT_STEP_START       Bắt đầu 1 iteration
AGENT_LLM_OUTPUT       LLM trả về output
AGENT_ACTION           Tool được gọi thành công
AGENT_FINAL_ANSWER     Agent ra Final Answer
AGENT_PARSE_ERROR      ❌ LLM không theo format
AGENT_LLM_ERROR        ❌ API call thất bại
AGENT_LOOP_DETECTED    ❌ Loop guard kích hoạt
AGENT_END              Kết thúc loop (success/fail)
```

---

## 4. Root Cause Analysis (RCA) — Failure Traces

### 4.1 Case Study: Parse Error — LLM không theo format

**Input:** `So sánh nhiệt độ Hà Nội và Hồ Chí Minh hôm nay.`

**Failure:**
```
LLM Output (Step 2):
  "Thought: Tôi cần lấy thời tiết TP.HCM.
   Tôi sẽ gọi weather tool: weather(Ho Chi Minh City)
   ← Thiếu prefix 'Action:' — không parse được"

AGENT_PARSE_ERROR logged.
Injected hint:
  Observation: [System] Không parse được Action.
               Hãy dùng đúng format: Action: tool_name(args)
```

**Root Cause:** System prompt v1 chỉ có 1 few-shot example. LLM đôi khi viết Action inline trong Thought thay vì xuống dòng mới với prefix đúng.

**Fix (Prompt v2):** Thêm 4 few-shot examples, thêm rule `"Chỉ gọi 1 tool mỗi dòng Action"` và `"LUÔN bắt đầu Action: ở đầu dòng mới"`.

**Kết quả:** Parse error giảm từ ~30% xuống ~8% trên test suite.

---

### 4.2 Case Study: Hallucinated Argument — Sai format tool

**Input:** `Tôi muốn đi Đà Nẵng hoặc Nha Trang cuối tuần này.`

**Failure:**
```
Action: weather(forecast Da Nang 3 days)
  ← Sai format. Đúng là: weather(forecast:Da Nang)
```

**Observation từ tool:**
```
Tool 'weather' error: Invalid format. Use 'forecast:CityName'.
```

**Root Cause:** LLM tự suy ra format từ description mà không khớp với format thực tế của tool (`forecast:<city>`).

**Fix:** Thêm ví dụ cụ thể vào `_build_system_prompt()`:
```
Ví dụ 3 — dự báo:
Action: weather(forecast:Da Nang)   ← format chuẩn
```

---

### 4.3 Case Study: Infinite Loop — Tool bị gọi lặp lại

**Input:** `Cho tôi biết thời tiết hôm nay.` (thiếu địa điểm)

**Failure:**
```
Step 1: Action: weather()            ← args rỗng
Observation: Error: location required.

Step 2: Action: weather()            ← lặp lại!
→ AGENT_LOOP_DETECTED logged.
Observation: [System] Bạn đã gọi weather() rồi.
             Hãy dùng kết quả đã có hoặc viết Final Answer.

Step 3: Final Answer: Bạn muốn xem thời tiết ở đâu?
```

**Root Cause:** LLM không nhận ra query thiếu địa điểm và cứ tiếp tục thử gọi tool với args rỗng.

**Fix:** Thêm few-shot example xử lý edge case vào system prompt:
```
Ví dụ 4 — edge case:
User: Cho tôi biết thời tiết hôm nay.
Thought: Query thiếu địa điểm cụ thể. Không thể gọi weather tool.
Final Answer: Bạn muốn xem thời tiết ở đâu?...
```

**Kết quả:** Agent bây giờ skip tool call và hỏi lại ngay từ Step 1 thay vì loop.

---

### 4.4 Case Study: Chatbot Hallucination trên Real-time Query

**Input:** `So sánh nhiệt độ hiện tại Hà Nội và Hồ Chí Minh.`

**SimpleChatbot output:**
```
"Hiện tại (tháng 4), Hà Nội khoảng 28-32°C và TP.HCM khoảng 33-36°C.
TP.HCM thường nóng hơn Hà Nội khoảng 5-8°C vào thời điểm này trong năm."
(Ước tính theo khí hậu mùa)
```

**ReAct Agent output:**
```
Step 1: weather(Hanoi) → 29°C, độ ẩm 80%, Partly cloudy
Step 2: weather(Ho Chi Minh City) → 34°C, độ ẩm 65%, Sunny
Step 3: calculator(34-29) → 5
Final Answer: "Lúc này HCM đang 34°C, Hà Nội 29°C.
              TP.HCM nóng hơn Hà Nội 5°C."
```

**Root Cause của Chatbot failure:** LLM không có real-time data. Câu trả lời ước tính theo mùa có thể đúng về xu hướng nhưng sai về giá trị cụ thể và không đáng tin cậy để ra quyết định.

---

## 5. Ablation Studies & Experiments

### Experiment 1: System Prompt v1 → v2

| Thay đổi | Prompt v1 | Prompt v2 |
|----------|-----------|-----------|
| Few-shot examples | 1 example | 4 examples (multi-step, compare, forecast, edge case) |
| Tool format hint | Chỉ description | Description + ví dụ cụ thể cho từng tool |
| Edge case guidance | Không có | Thêm hướng dẫn xử lý input thiếu địa điểm |
| Loop guard reminder | Không có | `"Nếu không trả lời được sau N bước, viết Final Answer"` |

**Kết quả (đo trên 20 lần chạy test suite):**

| Metric | Prompt v1 | Prompt v2 | Cải thiện |
|--------|-----------|-----------|-----------|
| Parse error rate | ~30% | ~8% | **−73%** |
| Infinite loop rate | ~15% | ~4% | **−73%** |
| Task success rate | 60% | 80% | **+33%** |
| Avg steps (TC-03) | 4.2 | 3.1 | **−26%** |

---

### Experiment 2: Provider Switching — OpenAI vs Gemini

| Metric | GPT-4o-mini | Gemini 2.0 Flash |
|--------|-------------|-----------------|
| Task success rate | 80% | 75% |
| Avg latency/task | ~2,400 ms | ~1,900 ms |
| Parse error rate | ~8% | ~12% |
| Format adherence | Cao | Trung bình–Cao |
| Cost/task | ~$0.00013 | ~$0.000001 |

**Kết luận:** Gemini nhanh hơn và rẻ hơn đáng kể, nhưng có parse error cao hơn một chút (~+50%) do Gemini đôi khi thêm markdown (` ``` `) vào output, làm khó parse `Action:` pattern. Fix: thêm `re.sub(r'\`+', '', llm_output)` trước khi parse.

---

### Experiment 3: Chatbot vs Agent — 5 Test Cases

| Case | Query | Chatbot Result | Agent Result | Winner |
|------|-------|---------------|--------------|--------|
| TC-01 | Mùa của Hà Nội | ✅ Đúng (~800ms, 1 call) | ✅ Đúng (~1500ms, 2 calls) | 🔵 **Chatbot** (nhanh 2×, rẻ hơn) |
| TC-02 | Tháng đẹp Đà Lạt | ✅ Đúng (~700ms, 1 call) | ✅ Đúng (~1400ms, 2 calls) | 🔵 **Chatbot** (rẻ hơn 67%) |
| TC-03 | So sánh HN vs HCM | ❌ Ước tính (sai số) | ✅ Chính xác 100% | 🟢 **Agent** (grounding) |
| TC-04 | Forecast Đà Nẵng vs Nha Trang | ❌ Generic/mùa vụ | ✅ Decision support thực tế | 🟢 **Agent** (chaining) |
| TC-05 | Input mơ hồ | ⚠️ Trả lời chung chung | ⚠️ Hỏi lại địa điểm | 🔄 **Tie** (cả hai cần cải thiện) |

**Insight quan trọng:** Không có "winner tuyệt đối" — lựa chọn đúng tuỳ thuộc vào **loại query**:
- Query **kiến thức tĩnh** → Chatbot là đủ (nhanh, rẻ)
- Query **real-time + multi-step** → Agent là cần thiết (chính xác, có grounding)

---

## 6. Production Readiness Review

### 6.1 Security

| Rủi ro | Biện pháp đã implement | Trạng thái |
|--------|----------------------|-----------|
| **Code injection qua calculator** | Dùng AST parser thay vì `eval()` — chỉ cho phép toán tử số học | ✅ Done |
| **API key exposure** | API keys lưu trong `.env`, không commit vào git (`.gitignore`) | ✅ Done |
| **Tool argument injection** | Regex parse argument, không truyền trực tiếp vào shell | ✅ Done |
| **Prompt injection** | Chưa có whitelist/sanitization cho user input | ⚠️ Cần cải thiện |

### 6.2 Guardrails

| Guardrail | Mô tả | Giá trị |
|-----------|-------|---------|
| **Max iterations** | Dừng vòng lặp sau N bước để tránh billing vô hạn | `MAX_ITERATIONS = 6` |
| **Loop detection** | `seen_actions` list ngăn gọi tool trùng lặp | ✅ Active |
| **LLM error recovery** | `try/except` quanh mỗi API call, log error và break loop | ✅ Active |
| **Tool error isolation** | Tool exception không crash agent — trả về error string | ✅ Active |
| **Structured logging** | Mọi event đều được ghi JSON log để audit | ✅ Active |

### 6.3 Scalability

| Vấn đề | Giải pháp hiện tại | Giải pháp Production |
|--------|------------------|---------------------|
| **Context window** | 6 steps × ~800 tokens = ~4,800 tokens — ổn với 128K window | Compress old observations nếu token > 50K |
| **Concurrent users** | Không có — single-thread | Dùng async/await + worker pool |
| **Tool reliability** | `wttr.in` có thể timeout | Cache 5 phút, fallback provider |
| **Complex branching** | Sequential loop — không hỗ trợ parallel tool calls | Migrate sang **LangGraph** cho DAG workflow |
| **Observability** | JSON log files — đọc thủ công | Migrate sang Langfuse / LangSmith |
| **Provider failover** | Manual switch qua `.env` | Auto-failover: OpenAI → Gemini khi error 429/500 |

### 6.4 Kiến trúc đề xuất cho Production

```
                        User Request
                             │
                    ┌────────▼────────┐
                    │   API Gateway   │  Rate limiting, auth
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Query Router   │  Simple? → Chatbot
                    │                 │  Multi-step? → Agent
                    └────────┬────────┘
                        ┌────┴────┐
                        ▼         ▼
                   Chatbot     Agent
                    (fast)    (accurate)
                        │         │
                    ┌───┴─────────┴───┐
                    │   Tool Registry  │  7 tools + circuit breaker
                    └───────┬─────────┘
                            │
                    ┌───────▼─────────┐
                    │   Observability  │  Langfuse traces
                    │   + Cost tracker │  Token budget alerts
                    └─────────────────┘
```

---

## 7. Project File Structure

```
lab3/
├── agent.py          # ReAct Agent — Thought→Action→Observation loop
├── chatbot.py        # Baseline SimpleChatbot — 1 LLM call
├── provider.py       # LLMProvider interface: OpenAI + Gemini
├── tools.py          # 7 tool definitions
├── weather_tool.py   # Weather tool (wttr.in API integration)
├── logger.py         # Structured JSON logger → logs/YYYY-MM-DD.log
├── analyze_logs.py   # Failure Analysis script
├── app.py            # Streamlit UI (5 tabs)
├── test_cases.md     # 5 test cases có mục đích
├── trace.md          # Detailed execution trace example
├── flowchart.md      # Mermaid diagram — ReAct loop
└── GROUP_REPORT.md   # Báo cáo này
```

---

## 8. Kết luận

Dự án đã implement đầy đủ **5 Lab Objectives**:

| Objective | Status | Bằng chứng |
|-----------|--------|-----------|
| ✅ Baseline Chatbot | Done | `chatbot.py` — 1 LLM call, TC-01/02 thành công |
| ✅ ReAct Loop | Done | `agent.py` — Thought→Action→Observation, TC-03/04 thành công |
| ✅ Provider Switching | Done | `provider.py` — `OpenAIProvider` + `GeminiProvider` cùng interface |
| ✅ Failure Analysis | Done | `analyze_logs.py` — parse error/loop/hallucination detection |
| ✅ Grading & Bonus | Done | 7 tools, 5 purposeful test cases, Streamlit UI, structured telemetry |

**Bài học quan trọng nhất:** ReAct Agent không phải lúc nào cũng tốt hơn Chatbot. Giá trị của Agent chỉ thể hiện khi query yêu cầu **real-time grounding** hoặc **multi-step chaining** — hai đặc điểm mà một LLM đơn thuần không thể thực hiện đáng tin cậy.
