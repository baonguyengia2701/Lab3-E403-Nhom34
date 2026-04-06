"""
agent.py — ReAct Agent: Thought → Action → Observation loop.

Objective 2: ReAct Loop
  Implement Thought-Action-Observation cycle.
  So sánh với chatbot.py để thấy sức mạnh của tool-augmented LLM.

Objective 3: Provider Switching
  Dùng provider.py để swap giữa OpenAI và Gemini.

Cách chạy:
    python agent.py
    python agent.py --provider gemini      # dùng Gemini
    python agent.py --provider openai      # dùng OpenAI (mặc định)
"""

import os
import re
import sys
import time
from dotenv import load_dotenv
from provider import build_provider
from tools import ALL_TOOLS
from logger import log

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

# Đọc provider từ CLI arg hoặc .env
_cli_provider = None
for i, arg in enumerate(sys.argv[1:]):
    if arg == "--provider" and i + 1 < len(sys.argv) - 1:
        _cli_provider = sys.argv[i + 2]

provider = build_provider(_cli_provider)
MODEL    = provider.model
PROVIDER = provider.name

MAX_ITERATIONS = 6  # safeguard — tối đa 6 vòng lặp Thought/Action

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def _build_system_prompt() -> str:
    """Xây dựng system prompt với mô tả tool và few-shot examples."""
    tool_list = "\n".join(
        [f"- {t['name']}: {t['description']}" for t in ALL_TOOLS]
    )

    return f"""Bạn là trợ lý hỏi đáp thời tiết Việt Nam thông minh, có khả năng tra cứu dữ liệu thời tiết THỰC TẾ.

Bạn có quyền truy cập các tool sau:
{tool_list}

LUÔN dùng ĐÚNG format này (không được lệch):
Thought: <lý luận về bước tiếp theo>
Action: <tool_name>(<argument>)
Observation: <kết quả tool — được điền tự động>
... (lặp lại cho đến khi có đủ thông tin)
Final Answer: <câu trả lời đầy đủ bằng tiếng Việt>

Quy tắc:
- Chỉ gọi 1 tool mỗi dòng Action.
- KHÔNG tự bịa Observation — chúng sẽ được cung cấp tự động.
- Khi đã đủ thông tin, viết "Final Answer:" và trả lời bằng tiếng Việt, thân thiện.
- Nếu query thiếu thông tin (ví dụ: thiếu địa điểm), hỏi lại người dùng thay vì đoán mò.
- Nếu không trả lời được sau {MAX_ITERATIONS} bước, viết "Final Answer: Không thể xác định được thông tin yêu cầu."

Ví dụ 1 — thời tiết hiện tại:
User: Thời tiết Hà Nội hôm nay thế nào?
Thought: Tôi cần tra cứu thời tiết thực tế tại Hà Nội.
Action: weather(Hanoi)
Observation: 🌫️ Thời tiết tại Hanoi: Haze, 33°C, độ ẩm 67%, gió 11 km/h
Thought: Đã có đủ thông tin thời tiết Hà Nội.
Final Answer: Hôm nay Hà Nội đang có sương mù, nhiệt độ 33°C, độ ẩm 67%. Trời oi bức, nên mang nước uống.

Ví dụ 2 — so sánh 2 thành phố (multi-step):
User: Hà Nội và Hồ Chí Minh thành phố nào nóng hơn hôm nay, chênh lệch bao nhiêu?
Thought: Cần lấy nhiệt độ Hà Nội trước.
Action: weather(Hanoi)
Observation: 🌤️ Hà Nội: 29°C, độ ẩm 80%
Thought: Bây giờ lấy nhiệt độ TP.HCM.
Action: weather(Ho Chi Minh City)
Observation: 🌤️ TP. Hồ Chí Minh: 34°C, độ ẩm 70%
Thought: HCM 34°C, HN 29°C. Tính chênh lệch: 34 - 29 = 5.
Action: calculator(34-29)
Observation: 5
Final Answer: Hôm nay Hồ Chí Minh nóng hơn Hà Nội **5°C** (34°C vs 29°C).

Ví dụ 3 — dự báo + tư vấn:
User: Cuối tuần đi Đà Nẵng hay Nha Trang, nơi nào đẹp hơn?
Thought: Cần xem dự báo 3 ngày của cả 2 nơi.
Action: weather(forecast:Da Nang)
Observation: 📅 Đà Nẵng: Thứ 6 Mưa 70%, Thứ 7 Mưa 60%, CN Nắng 29°C
Action: weather(forecast:Nha Trang)
Observation: 📅 Nha Trang: Thứ 6 Nắng 30°C, Thứ 7 Nắng 31°C, CN Nắng 30°C
Final Answer: Nên chọn Nha Trang — 3 ngày tới đều nắng đẹp. Đà Nẵng có mưa thứ 6-7.

Ví dụ 4 — edge case (input mơ hồ):
User: Cho tôi biết thời tiết hôm nay.
Thought: Query thiếu địa điểm cụ thể. Không thể gọi weather tool.
Final Answer: Bạn muốn xem thời tiết ở đâu? Hãy cho tôi biết tên thành phố (VD: Hà Nội, Đà Nẵng, TP.HCM...).
"""


SYSTEM_PROMPT = _build_system_prompt()

# =============================================================================
# TOOL EXECUTION
# =============================================================================

def _execute_tool(tool_name: str, args: str) -> str:
    """Tìm tool theo tên và gọi hàm của nó."""
    normalized = tool_name.lower().strip()
    for tool in ALL_TOOLS:
        if tool["name"].lower() == normalized:
            try:
                return str(tool["func"](args))
            except Exception as e:
                return f"Tool '{tool_name}' error: {e}"
    available = [t["name"] for t in ALL_TOOLS]
    return f"Tool '{tool_name}' không tìm thấy. Các tool có sẵn: {available}."


# =============================================================================
# MAIN REACT LOOP — Objective 2
# =============================================================================

def run_agent(user_query: str, override_provider=None) -> dict:
    """
    Chạy vòng lặp ReAct (Thought → Action → Observation) cho câu hỏi của người dùng.

    Args:
        user_query:        Câu hỏi từ người dùng.
        override_provider: LLMProvider instance (dùng trong app.py để truyền từ UI).

    Returns:
        dict với 'answer', 'steps', 'trace', 'latency_ms', 'tokens', 'provider',
                 'step_log' (list các action/observation/error để hiển thị).
    """
    p = override_provider or provider
    log("AGENT_START", {
        "query": user_query,
        "model": p.model,
        "provider": p.name,
        "max_iterations": MAX_ITERATIONS,
    })

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_query},
    ]

    transcript    = f"User: {user_query}\n"
    total_tokens  = 0
    total_latency = 0
    seen_actions  = []     # infinite-loop guard
    final_answer  = None
    step_log      = []     # structured list for UI display

    for step in range(MAX_ITERATIONS):
        log("AGENT_STEP_START", {"step": step + 1, "provider": p.name})

        # ── Gọi LLM ──────────────────────────────────────────────────────────
        start = time.time()
        try:
            llm_output, usage = p.chat(messages)
        except Exception as e:
            log("AGENT_LLM_ERROR", {"step": step + 1, "error": str(e), "provider": p.name})
            transcript += f"\n[LLM Error step {step+1}: {e}]\n"
            step_log.append({"step": step + 1, "type": "llm_error", "error": str(e)})
            break

        latency_ms     = int((time.time() - start) * 1000)
        total_latency += latency_ms
        total_tokens  += usage["total_tokens"]
        transcript    += llm_output + "\n"

        log("AGENT_LLM_OUTPUT", {
            "step":               step + 1,
            "output":             llm_output,
            "latency_ms":         latency_ms,
            "prompt_tokens":      usage["prompt_tokens"],
            "completion_tokens":  usage["completion_tokens"],
            "total_tokens":       usage["total_tokens"],
            "provider":           p.name,
        })

        # ── Final Answer? ─────────────────────────────────────────────────────
        final_match = re.search(r"Final Answer\s*:\s*(.+)", llm_output, re.DOTALL | re.IGNORECASE)
        if final_match:
            final_answer = final_match.group(1).strip()
            log("AGENT_FINAL_ANSWER", {"step": step + 1, "answer": final_answer, "provider": p.name})
            step_log.append({"step": step + 1, "type": "final_answer", "answer": final_answer})
            break

        # ── Action? ───────────────────────────────────────────────────────────
        action_match = re.search(r"Action\s*:\s*(\w+)\s*\(([^)]*)\)", llm_output, re.IGNORECASE)
        if action_match:
            tool_name  = action_match.group(1).strip()
            tool_args  = action_match.group(2).strip()
            action_key = f"{tool_name.lower()}({tool_args})"

            if action_key in seen_actions:
                # Infinite-loop guard
                observation = (
                    f"[System] Bạn đã gọi {action_key} rồi. "
                    "Hãy dùng kết quả đã có hoặc viết Final Answer."
                )
                log("AGENT_LOOP_DETECTED", {"step": step + 1, "repeated_action": action_key})
                step_log.append({"step": step + 1, "type": "loop_detected", "action": action_key})
            else:
                seen_actions.append(action_key)
                observation = _execute_tool(tool_name, tool_args)
                log("AGENT_ACTION", {
                    "step":        step + 1,
                    "tool":        tool_name,
                    "args":        tool_args,
                    "observation": observation,
                    "provider":    p.name,
                })
                step_log.append({
                    "step": step + 1,
                    "type": "action",
                    "tool": tool_name,
                    "args": tool_args,
                    "obs":  observation,
                })

            transcript += f"Observation: {observation}\n"
            messages.append({"role": "assistant", "content": llm_output})
            messages.append({"role": "user",      "content": f"Observation: {observation}"})

        else:
            # Parse error
            hint = "Observation: [System] Không parse được Action. Dùng format: Action: tool_name(args)"
            transcript += hint + "\n"
            messages.append({"role": "assistant", "content": llm_output})
            messages.append({"role": "user",      "content": hint})
            log("AGENT_PARSE_ERROR", {"step": step + 1, "raw_output": llm_output, "provider": p.name})
            step_log.append({"step": step + 1, "type": "parse_error", "raw": llm_output[:200]})

    success = final_answer is not None
    log("AGENT_END", {
        "query":            user_query,
        "steps_used":       step + 1,
        "success":          success,
        "total_latency_ms": total_latency,
        "total_tokens":     total_tokens,
        "answer":           final_answer or "",
        "provider":         p.name,
    })

    return {
        "answer":     final_answer or "Đã đạt giới hạn bước — không tìm được câu trả lời.",
        "steps":      step + 1,
        "trace":      transcript,
        "latency_ms": total_latency,
        "tokens":     total_tokens,
        "provider":   p.name,
        "step_log":   step_log,
        "success":    success,
    }


# =============================================================================
# DEMO — chạy trực tiếp
# =============================================================================

# 5 Test Cases có mục đích:
#
# [CHATBOT THẮNG]  TC-01: Kiến thức khí hậu học  → không cần tool (agent tốn thêm steps)
# [CHATBOT THẮNG]  TC-02: Mùa du lịch tốt nhất   → dữ liệu tĩnh, chatbot là đủ
# [AGENT THẮNG]   TC-03: So sánh thực tế 2 TP    → multi-step: lấy 2 TP → tính chênh lệch
# [AGENT THẮNG]   TC-04: Dự báo 2 điểm + tư vấn → multi-step: step 3 phụ thuộc step 1+2
# [EDGE CASE]     TC-05: Thiếu địa điểm cụ thể   → tool fail, test graceful degradation
TEST_CASES = [
    "Hà Nội có bao nhiêu mùa trong năm? Đặc điểm từng mùa là gì?",
    "Tháng mấy là thời điểm đẹp nhất để du lịch Đà Lạt và tại sao?",
    "So sánh nhiệt độ hiện tại của Hà Nội và Hồ Chí Minh. Chênh lệch bao nhiêu độ?",
    "Tôi muốn đi Đà Nẵng hoặc Nha Trang cuối tuần này. Dự báo 3 ngày tới ở cả 2 nơi thế nào? Gợi ý tôi nên chọn đâu.",
    "Cho tôi biết thời tiết hôm nay.",
]

LABELS = [
    "CHATBOT THẮNG",
    "CHATBOT THẮNG",
    "AGENT THẮNG",
    "AGENT THẮNG",
    "EDGE CASE",
]

if __name__ == "__main__":
    from logger import _get_log_path
    print("=" * 65)
    print("  Agent Thời Tiết Việt Nam — ReAct + Weather Tool")
    print(f"  Provider : {PROVIDER.upper()}  |  Model: {MODEL}")
    print(f"  Max iter : {MAX_ITERATIONS}")
    print(f"  Log      : {_get_log_path()}")
    print("=" * 65)
    print("  Objective 2 : ReAct Loop (Thought → Action → Observation)")
    print("  Objective 3 : Provider Switching — thử --provider gemini")
    print("  TC-01,02: Chatbot thắng  — câu hỏi kiến thức tĩnh")
    print("  TC-03,04: Agent thắng    — multi-step, real-time grounding")
    print("  TC-05:    Edge case      — input mơ hồ")
    print("=" * 65)

    for i, query in enumerate(TEST_CASES, 1):
        label = LABELS[i - 1]
        print(f"\n[TC-{i:02d}] [{label}]")
        print(f"  Query: {query}")
        print("-" * 65)
        try:
            result = run_agent(query)
            print(f"  Answer   : {result['answer'][:350]}")
            print(f"  Steps    : {result['steps']} | Latency: {result['latency_ms']} ms | Tokens: {result['tokens']}")
            print(f"  Success  : {'✅' if result['success'] else '❌'}")
        except Exception as e:
            print(f"  Error    : {e}")
