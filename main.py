"""
Lab 3 — Main entry point.
Runs the same test cases through both the SimpleChatbot and the ReActAgent,
then prints a side-by-side comparison table.
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()

# ── Provider selection ────────────────────────────────────────────────────────
PROVIDER = os.getenv("DEFAULT_PROVIDER", "openai").lower()
MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")

def build_provider():
    if PROVIDER == "openai":
        from src.core.openai_provider import OpenAIProvider
        api_key = os.getenv("OPENAI_API_KEY")
        return OpenAIProvider(model_name=MODEL, api_key=api_key)
    elif PROVIDER == "google":
        from src.core.gemini_provider import GeminiProvider
        api_key = os.getenv("GEMINI_API_KEY")
        return GeminiProvider(model_name=os.getenv("DEFAULT_MODEL", "gemini-1.5-flash"), api_key=api_key)
    else:
        raise ValueError(
            f"Unknown provider '{PROVIDER}'. Set DEFAULT_PROVIDER=openai or google in .env"
        )

# ── Test cases ────────────────────────────────────────────────────────────────
TEST_CASES = [
    {
        "id": "TC-01",
        "label": "Simple Q&A",
        "query": "What is the capital of Vietnam?",
        "expected_type": "factual",
    },
    {
        "id": "TC-02",
        "label": "Math calculation",
        "query": "Calculate 18% VAT on 1,500,000 VND.",
        "expected_type": "tool-use",
    },
    {
        "id": "TC-03",
        "label": "Date query",
        "query": "What is today's date?",
        "expected_type": "tool-use",
    },
    {
        "id": "TC-04",
        "label": "Multi-step reasoning",
        "query": "What is today's date and how many days are left until January 1, 2027?",
        "expected_type": "multi-step",
    },
    {
        "id": "TC-05",
        "label": "Compound math + date",
        "query": (
            "If I save 500,000 VND per day starting today, "
            "how much will I have saved by January 1, 2027?"
        ),
        "expected_type": "multi-step",
    },
]


def run_comparison():
    print("=" * 70)
    print("  Lab 3 - Chatbot vs ReAct Agent Comparison")
    print(f"  Provider: {PROVIDER.upper()} | Model: {MODEL}")
    print("=" * 70)

    llm = build_provider()

    from src.agent.chatbot import SimpleChatbot
    from src.agent.agent import ReActAgent
    from src.tools import ALL_TOOLS

    chatbot = SimpleChatbot(llm=llm)
    agent = ReActAgent(llm=llm, tools=ALL_TOOLS, max_steps=6)

    results = []

    for tc in TEST_CASES:
        print(f"\n{'-'*70}")
        print(f"[{tc['id']}] {tc['label']} ({tc['expected_type']})")
        print(f"Query: {tc['query']}")
        print("-" * 70)

        # --- Chatbot ---
        t0 = time.time()
        chatbot_answer = chatbot.chat(tc["query"])
        chatbot_time = round((time.time() - t0) * 1000)

        # --- Agent ---
        t0 = time.time()
        agent_answer = agent.run(tc["query"])
        agent_time = round((time.time() - t0) * 1000)

        print(f"\n  [CHATBOT]  ({chatbot_time}ms)")
        print(f"  {chatbot_answer[:300]}")

        print(f"\n  [AGENT]    ({agent_time}ms)")
        print(f"  {agent_answer[:300]}")

        results.append({
            "id": tc["id"],
            "label": tc["label"],
            "type": tc["expected_type"],
            "chatbot_ms": chatbot_time,
            "agent_ms": agent_time,
            "chatbot_answer": chatbot_answer,
            "agent_answer": agent_answer,
        })

    # ── Summary table ─────────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("  SUMMARY")
    print(f"  {'ID':<8} {'Type':<15} {'Chatbot (ms)':<15} {'Agent (ms)':<12}")
    print(f"  {'-'*50}")
    for r in results:
        print(f"  {r['id']:<8} {r['type']:<15} {r['chatbot_ms']:<15} {r['agent_ms']:<12}")

    avg_chatbot = sum(r["chatbot_ms"] for r in results) / len(results)
    avg_agent = sum(r["agent_ms"] for r in results) / len(results)
    print(f"\n  Average latency - Chatbot: {avg_chatbot:.0f}ms | Agent: {avg_agent:.0f}ms")
    print("=" * 70)


if __name__ == "__main__":
    run_comparison()
