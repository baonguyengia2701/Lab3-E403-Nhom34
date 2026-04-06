"""
chatbot.py — Baseline chatbot hỏi đáp thời tiết Việt Nam.

Objective 1: Baseline Chatbot
  Chỉ dùng 1 LLM call — không có tool, không có real-time data.
  Dùng để so sánh với agent.py và quan sát giới hạn khi gặp multi-step reasoning.

Cách chạy:
    python chatbot.py
    python chatbot.py --provider gemini      # dùng Gemini
    python chatbot.py --provider openai      # dùng OpenAI (mặc định)
"""

import os
import sys
import time
from dotenv import load_dotenv
from provider import build_provider
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

SYSTEM_PROMPT = """Bạn là trợ lý thông tin thời tiết và khí hậu Việt Nam.

Trả lời dựa trên kiến thức khí hậu học: đặc điểm các vùng miền, mùa trong năm,
nhiệt độ trung bình theo tháng, mùa mưa/khô từng khu vực.

Nguyên tắc:
- Trả lời ngắn gọn (2-4 câu), bằng tiếng Việt.
- Với câu hỏi về kiến thức khí hậu/mùa: trả lời tự tin và chính xác.
- Với câu hỏi về thời tiết HIỆN TẠI hoặc DỰ BÁO CỤ THỂ: hãy thừa nhận rõ
  "Tôi không có dữ liệu thực tế hôm nay" và chỉ ước tính theo mùa.
- KHÔNG bịa số liệu thực tế."""

# =============================================================================
# CHATBOT FUNCTION
# =============================================================================

def chat(user_query: str, override_provider=None) -> dict:
    """
    Gọi LLM một lần để trả lời câu hỏi thời tiết.

    Args:
        user_query:        Câu hỏi từ người dùng.
        override_provider: LLMProvider instance (dùng trong app.py để truyền từ UI).

    Returns:
        dict với 'answer', 'latency_ms', 'tokens', 'provider'.
    """
    p = override_provider or provider
    log("CHATBOT_START", {"query": user_query, "model": p.model, "provider": p.name})
    start = time.time()

    try:
        content, usage = p.chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_query},
        ])
    except Exception as e:
        log("CHATBOT_ERROR", {"query": user_query, "error": str(e), "provider": p.name})
        raise

    latency_ms = int((time.time() - start) * 1000)

    log("CHATBOT_RESPONSE", {
        "query":             user_query,
        "answer":            content,
        "model":             p.model,
        "provider":          p.name,
        "latency_ms":        latency_ms,
        "prompt_tokens":     usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "total_tokens":      usage["total_tokens"],
    })

    return {
        "answer":     content,
        "latency_ms": latency_ms,
        "tokens":     usage["total_tokens"],
        "provider":   p.name,
    }


# =============================================================================
# DEMO — chạy trực tiếp
# =============================================================================

# 5 Test Cases có mục đích:
#
# [CHATBOT THẮNG]  TC-01: Kiến thức khí hậu học  → chatbot nhanh/rẻ hơn, không cần tool
# [CHATBOT THẮNG]  TC-02: Mùa du lịch tốt nhất   → dữ liệu tĩnh, chatbot là đủ
# [AGENT THẮNG]   TC-03: So sánh thực tế 2 TP    → multi-step: bước 2 phụ thuộc bước 1
# [AGENT THẮNG]   TC-04: Dự báo 2 điểm + tư vấn → multi-step: step 3 phụ thuộc step 1+2
# [EDGE CASE]     TC-05: Input mơ hồ thiếu địa điểm → test graceful degradation
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
    "AGENT THẮNG (chatbot giới hạn)",
    "AGENT THẮNG (chatbot giới hạn)",
    "EDGE CASE",
]

if __name__ == "__main__":
    from logger import _get_log_path
    print("=" * 65)
    print("  Chatbot Thời Tiết Việt Nam — Baseline (1 LLM call, no tools)")
    print(f"  Provider : {PROVIDER.upper()}  |  Model: {MODEL}")
    print(f"  Log      : {_get_log_path()}")
    print("=" * 65)
    print("  Objective 1: Quan sát giới hạn của LLM không có tool")
    print("  TC-01,02: Chatbot thắng  — câu hỏi kiến thức tĩnh")
    print("  TC-03,04: Chatbot thua   — thiếu dữ liệu real-time")
    print("  TC-05:    Edge case      — input mơ hồ")
    print("=" * 65)

    for i, query in enumerate(TEST_CASES, 1):
        label = LABELS[i - 1]
        print(f"\n[TC-{i:02d}] [{label}]")
        print(f"  Query: {query}")
        print("-" * 65)
        try:
            result = chat(query)
            print(f"  Answer  : {result['answer'][:350]}")
            print(f"  Latency : {result['latency_ms']} ms | Tokens: {result['tokens']}")
        except Exception as e:
            print(f"  Error   : {e}")
