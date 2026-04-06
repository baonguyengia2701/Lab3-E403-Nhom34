"""
app.py — Giao diện web cho Lab 3: Chatbot vs ReAct Agent.

Chạy:
    cd lab3
    streamlit run app.py
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

# Đảm bảo import từ cùng thư mục lab3/
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Lab 3 — Chatbot vs ReAct Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# CUSTOM CSS
# =============================================================================

st.markdown("""
<style>
/* Header gradient */
.main-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding: 2rem 2rem 1.5rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    color: white;
}
.main-header h1 { margin: 0; font-size: 1.8rem; }
.main-header p  { margin: 0.3rem 0 0; opacity: 0.75; font-size: 0.95rem; }

/* Answer cards */
.answer-card {
    background: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-top: 0.5rem;
    color: #cdd6f4;
    font-size: 0.95rem;
    line-height: 1.6;
}
.answer-card.chatbot { border-left: 4px solid #89b4fa; }
.answer-card.agent   { border-left: 4px solid #a6e3a1; }

/* Metric chip */
.chip {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    margin: 2px;
}
.chip-blue  { background: #1e3a5f; color: #89b4fa; }
.chip-green { background: #1e3a2f; color: #a6e3a1; }
.chip-red   { background: #3a1e1e; color: #f38ba8; }

/* Trace box */
.trace-box {
    background: #11111b;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 1rem;
    font-family: 'Courier New', monospace;
    font-size: 0.82rem;
    color: #cdd6f4;
    white-space: pre-wrap;
    max-height: 400px;
    overflow-y: auto;
    line-height: 1.5;
}

/* Tool badge */
.tool-badge {
    background: #2a273f;
    border: 1px solid #6c7086;
    border-radius: 8px;
    padding: 0.7rem 1rem;
    margin: 0.3rem 0;
    font-size: 0.85rem;
    color: #cdd6f4;
}

/* Log row colors */
.log-success { color: #a6e3a1; }
.log-error   { color: #f38ba8; }
.log-info    { color: #89b4fa; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SIDEBAR — Cấu hình
# =============================================================================

with st.sidebar:
    st.markdown("## ⚙️ Cấu hình")

    # ── Provider selector (Objective 3) ──────────────────────────────────────
    provider_choice = st.selectbox(
        "🔀 LLM Provider",
        ["openai", "gemini"],
        index=0 if os.getenv("DEFAULT_PROVIDER", "openai") == "openai" else 1,
        help="Objective 3: Provider Switching — OpenAI ↔ Gemini",
    )

    if provider_choice == "openai":
        api_key = st.text_input(
            "OpenAI API Key",
            value=os.getenv("OPENAI_API_KEY", ""),
            type="password",
            placeholder="sk-...",
        )
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        model = st.selectbox(
            "Model",
            ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"],
            index=["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"].index(
                os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
                if os.getenv("DEFAULT_MODEL", "gpt-4o-mini") in ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"]
                else "gpt-4o-mini"
            ),
        )
    else:
        gemini_key = st.text_input(
            "Gemini API Key",
            value=os.getenv("GEMINI_API_KEY", ""),
            type="password",
            placeholder="AIza...",
        )
        api_key = os.getenv("OPENAI_API_KEY", "")
        model = st.selectbox(
            "Model",
            ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
            index=0,
        )

    max_iter = st.slider("Max Iterations (Agent)", 1, 10, 6)

    st.divider()
    st.markdown("### 🛠️ Tools có sẵn")

    try:
        from tools import ALL_TOOLS
        for tool in ALL_TOOLS:
            st.markdown(
                f'<div class="tool-badge">🔧 <b>{tool["name"]}</b><br>'
                f'<span style="color:#6c7086;font-size:0.78rem">{tool["description"][:80]}…</span></div>',
                unsafe_allow_html=True,
            )
    except Exception as e:
        st.error(f"Không load được tools: {e}")

    st.divider()
    st.markdown("### 📂 Quick links")
    st.markdown("- `python chatbot.py`")
    st.markdown("- `python agent.py`")
    st.markdown("- `python analyze_logs.py`")

# =============================================================================
# HEADER
# =============================================================================

st.markdown("""
<div class="main-header">
  <h1>🌤️ Lab 3 — Chatbot vs ReAct Agent: Thời Tiết Việt Nam</h1>
  <p>So sánh SimpleChatbot (không có real-time data) với ReActAgent (tra cứu thời tiết thực tế)</p>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# TABS
# =============================================================================

tab_chat, tab_demo, tab_tools, tab_analysis, tab_logs = st.tabs([
    "💬 Chat & So sánh",
    "🧪 Demo 5 Test Cases",
    "🔧 Test Tools",
    "📊 Failure Analysis",
    "📁 Xem Logs",
])

# =============================================================================
# TAB 1 — CHAT & SO SÁNH
# =============================================================================

with tab_chat:
    st.markdown("### 🌤️ Hỏi đáp thời tiết các tỉnh thành Việt Nam")
    st.caption("Chatbot ⚠️ không có real-time data | Agent ✅ tra cứu thời tiết thực tế qua weather tool")

    # Quick-select tỉnh thành
    QUICK_CITIES = {
        "— Chọn nhanh —": "",
        # Câu hỏi nhiệt độ cụ thể — dễ so sánh Chatbot vs Agent
        "🌡️ Hà Nội — nhiệt độ": "Nhiệt độ ở Hà Nội lúc này là bao nhiêu độ C?",
        "🌡️ HCM — nhiệt độ": "Nhiệt độ ở Hồ Chí Minh lúc này là bao nhiêu độ C?",
        "🌡️ Đà Nẵng — nhiệt độ": "Nhiệt độ ở Đà Nẵng lúc này là bao nhiêu độ C?",
        # Câu hỏi mang ô — cần biết mưa/độ ẩm thực tế
        "☂️ HN — có mang ô không?": "Hôm nay Hà Nội có mưa không? Tôi có cần mang ô không?",
        "☂️ HCM — có mang ô không?": "Hôm nay Hồ Chí Minh có mưa không? Tôi có cần mang ô không?",
        "☂️ Đà Nẵng — có mang ô?": "Đà Nẵng hôm nay có mưa không? Gió có mạnh không?",
        # So sánh 2 thành phố — highlight điểm mạnh của weather tool
        "🔄 HN vs HCM nóng hơn?": "So sánh nhiệt độ Hà Nội và Hồ Chí Minh ngay lúc này, nơi nào nóng hơn bao nhiêu độ?",
        "🔄 HN vs Đà Lạt": "So sánh thời tiết Hà Nội và Đà Lạt hôm nay.",
        # Dự báo du lịch
        "🏖️ Nha Trang — đi biển?": "Cuối tuần này đi Nha Trang tắm biển, thời tiết 3 ngày tới như thế nào?",
        "🏖️ Phú Quốc — đi biển?": "Thời tiết Phú Quốc 3 ngày tới thế nào? Có nên đi không?",
        "🌿 Đà Lạt — du lịch?": "Thời tiết Đà Lạt tuần này có đẹp để du lịch không?",
        "🏔️ Sa Pa — trekking?": "Sa Pa hôm nay thế nào? Có nên đi trekking không?",
    }

    col_city, col_input = st.columns([1, 2])
    with col_city:
        selected_city = st.selectbox("Chọn nhanh thành phố", list(QUICK_CITIES.keys()), label_visibility="collapsed")
    with col_input:
        prefill = QUICK_CITIES.get(selected_city, "")
        query = st.text_input(
            "Câu hỏi thời tiết",
            value=prefill,
            placeholder="VD: Thời tiết Đà Nẵng hôm nay thế nào?",
            label_visibility="collapsed",
        )

    col_run, col_mode = st.columns([1, 3])
    with col_run:
        run_btn = st.button("▶ Chạy", type="primary", use_container_width=True)
    with col_mode:
        run_both = st.checkbox("Chạy cả Chatbot lẫn Agent", value=True)

    if run_btn and query:
        active_key = api_key if provider_choice == "openai" else gemini_key
        if not active_key:
            st.error(f"⚠️ Chưa nhập {provider_choice.upper()} API Key!")
            st.stop()

        from provider import build_provider as _build_prov
        from chatbot import chat as _cb_chat
        from agent  import run_agent as _run_agent

        _prov = _build_prov(provider_choice, model=model, api_key=active_key)

        col_left, col_right = st.columns(2)
        cb_latency, cb_tokens = 0, 0
        total_latency, llm_calls = 0, 0

        # ── CHATBOT (Objective 1) ─────────────────────────────────────
        with col_left:
            st.markdown(f"#### 🔵 SimpleChatbot  `{provider_choice}/{model}`")
            st.caption("⚠️ 1 LLM call — không có tool, không có real-time data")
            with st.spinner("Đang gọi LLM..."):
                try:
                    cb_result  = _cb_chat(query, override_provider=_prov)
                    cb_answer  = cb_result["answer"]
                    cb_latency = cb_result["latency_ms"]
                    cb_tokens  = cb_result["tokens"]
                    st.markdown(
                        f'<div class="answer-card chatbot">{cb_answer}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<span class="chip chip-blue">⏱ {cb_latency} ms</span>'
                        f'<span class="chip chip-blue">🔤 {cb_tokens} tokens</span>'
                        f'<span class="chip chip-blue">📞 1 LLM call</span>',
                        unsafe_allow_html=True,
                    )
                except Exception as e:
                    st.error(f"Chatbot lỗi: {e}")

        # ── AGENT (Objective 2+3) ─────────────────────────────────────
        with col_right:
            st.markdown(f"#### 🟢 ReAct Agent  `{provider_choice}/{model}`")
            st.caption("✅ Thought→Action→Observation loop + real-time weather tool")
            with st.spinner("Đang chạy ReAct loop..."):
                try:
                    ag_result     = _run_agent(query, override_provider=_prov)
                    agent_answer  = ag_result["answer"]
                    total_latency = ag_result["latency_ms"]
                    total_tokens  = ag_result["tokens"]
                    llm_calls     = ag_result["steps"]
                    step_log      = ag_result["step_log"]
                    transcript    = ag_result["trace"]

                    st.markdown(
                        f'<div class="answer-card agent">{agent_answer}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<span class="chip chip-green">⏱ {total_latency} ms</span>'
                        f'<span class="chip chip-green">🔤 {total_tokens} tokens</span>'
                        f'<span class="chip chip-green">📞 {llm_calls} LLM calls</span>',
                        unsafe_allow_html=True,
                    )

                    with st.expander("🔍 Xem trace chi tiết (ReAct loop)"):
                        for s in step_log:
                            if s["type"] == "action":
                                st.markdown(f"**Step {s['step']}** — `{s['tool']}({s['args']})`")
                                st.caption(f"Observation: {s['obs']}")
                            elif s["type"] == "final_answer":
                                st.success(f"**Step {s['step']}** — Final Answer ✅")
                            elif s["type"] == "parse_error":
                                st.warning(f"**Step {s['step']}** — ⚠️ Parse Error (Failure Analysis)")
                            elif s["type"] == "loop_detected":
                                st.error(f"**Step {s['step']}** — 🔄 Infinite Loop Detected")
                            elif s["type"] == "llm_error":
                                st.error(f"**Step {s['step']}** — 🔴 LLM Error: {s.get('error','')}")
                        st.markdown("**Full transcript:**")
                        st.markdown(
                            f'<div class="trace-box">{transcript}</div>',
                            unsafe_allow_html=True,
                        )
                except Exception as e:
                    st.error(f"Agent lỗi: {e}")

        # ── So sánh tổng kết ──────────────────────────────────────────
        if cb_latency and total_latency:
            st.divider()
            st.markdown("#### 📊 So sánh nhanh")
            c1, c2, c3 = st.columns(3)
            c1.metric("Chatbot latency", f"{cb_latency} ms")
            c2.metric("Agent latency", f"{total_latency} ms",
                      delta=f"+{total_latency - cb_latency} ms", delta_color="inverse")
            c3.metric("LLM calls", f"Chatbot: 1 | Agent: {llm_calls}")

# =============================================================================
# TAB 2 — DEMO 5 TEST CASES
# =============================================================================

with tab_demo:
    st.markdown("### 🧪 Demo 5 Test Cases Có Mục Đích")
    st.markdown("""
| Nhóm | Test Cases | Mục đích |
|------|-----------|----------|
| 🔵 **Chatbot thắng** | TC-01, TC-02 | Query đơn giản, kiến thức tĩnh — chứng minh chatbot nhanh hơn, rẻ hơn |
| 🟢 **Agent thắng** | TC-03, TC-04 | Multi-step, bước sau phụ thuộc bước trước — chứng minh agent tạo giá trị nhờ grounding |
| 🔴 **Edge case** | TC-05 | Input mơ hồ / tool fail — test error handling và graceful degradation |
""")

    TEST_CASES = [
        {
            "id": "TC-01",
            "tag": "🔵 CHATBOT THẮNG",
            "label": "Kiến thức khí hậu học",
            "query": "Hà Nội có bao nhiêu mùa trong năm? Đặc điểm từng mùa là gì?",
            "why": "Câu hỏi kiến thức tĩnh — Chatbot trả lời tốt, nhanh hơn, rẻ hơn. Agent tốn thêm 1-2 LLM call mà kết quả tương đương.",
        },
        {
            "id": "TC-02",
            "tag": "🔵 CHATBOT THẮNG",
            "label": "Mùa du lịch tốt nhất",
            "query": "Tháng mấy là thời điểm đẹp nhất để du lịch Đà Lạt và tại sao?",
            "why": "Dữ liệu mùa vụ không thay đổi theo ngày — Chatbot đủ chính xác. Agent gọi weather tool không cần thiết.",
        },
        {
            "id": "TC-03",
            "tag": "🟢 AGENT THẮNG",
            "label": "So sánh thực tế 2 thành phố",
            "query": "So sánh nhiệt độ hiện tại của Hà Nội và Hồ Chí Minh. Chênh lệch bao nhiêu độ?",
            "why": "Multi-step: Step 1 lấy thời tiết HN, Step 2 lấy thời tiết HCM, Step 3 tính chênh lệch. Bước sau phụ thuộc bước trước — Chatbot bịa số, Agent dùng dữ liệu thực.",
        },
        {
            "id": "TC-04",
            "tag": "🟢 AGENT THẮNG",
            "label": "Dự báo 2 điểm + tư vấn",
            "query": "Tôi muốn đi Đà Nẵng hoặc Nha Trang cuối tuần này. Dự báo 3 ngày tới ở cả 2 nơi thế nào? Gợi ý tôi nên chọn đâu.",
            "why": "Multi-step: Step 1 dự báo Đà Nẵng, Step 2 dự báo Nha Trang, Step 3 tư vấn dựa trên kết quả Step 1+2. Chatbot không có dự báo thực tế.",
        },
        {
            "id": "TC-05",
            "tag": "🔴 EDGE CASE",
            "label": "Input mơ hồ — thiếu địa điểm",
            "query": "Cho tôi biết thời tiết hôm nay.",
            "why": "Input thiếu địa điểm cụ thể → Tool fail hoặc không biết cần gọi tool nào. Test graceful degradation: cả 2 phải hỏi lại hoặc từ chối lịch sự.",
        },
    ]

    if st.button("▶ Run All Test Cases", type="primary"):
        active_key = api_key if provider_choice == "openai" else gemini_key
        if not active_key:
            st.error(f"⚠️ Chưa nhập {provider_choice.upper()} API Key!")
            st.stop()

        from provider import build_provider as _build_prov
        from chatbot import chat as _cb_chat
        from agent  import run_agent as _run_agent

        _prov   = _build_prov(provider_choice, model=model, api_key=active_key)
        results = []
        progress = st.progress(0, text="Đang chạy...")

        for idx, tc in enumerate(TEST_CASES):
            progress.progress(idx / len(TEST_CASES), text=f"Chạy {tc['id']}...")

            # Chatbot (Objective 1)
            try:
                cb_result = _cb_chat(tc["query"], override_provider=_prov)
                cb_ans = cb_result["answer"]
                cb_ms  = cb_result["latency_ms"]
                cb_tok = cb_result["tokens"]
            except Exception as e:
                cb_ans, cb_ms, cb_tok = str(e), 0, 0

            # Agent (Objective 2+3)
            try:
                ag_result = _run_agent(tc["query"], override_provider=_prov)
                ag_ans   = ag_result["answer"]
                ag_ms    = ag_result["latency_ms"]
                ag_tok   = ag_result["tokens"]
                ag_steps = ag_result["steps"]
            except Exception as e:
                ag_ans, ag_ms, ag_tok, ag_steps = str(e), 0, 0, 0

            results.append({**tc, "cb_ans": cb_ans, "cb_ms": cb_ms, "cb_tok": cb_tok,
                             "ag_ans": ag_ans, "ag_ms": ag_ms, "ag_tok": ag_tok, "ag_steps": ag_steps})

        progress.progress(1.0, text="✅ Hoàn thành!")
        st.session_state["demo_results"] = results

    if "demo_results" in st.session_state:
        st.divider()
        for r in st.session_state["demo_results"]:
            tag = r.get("tag", "")
            with st.expander(f"**{r['id']}** {tag} — {r['label']}", expanded=True):
                st.caption(f"❓ Query: _{r['query']}_")
                st.info(f"🔬 **Tại sao test case này?** {r.get('why', '')}", icon="💡")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("🔵 **SimpleChatbot** _(1 LLM call, no tools)_")
                    st.markdown(f'<div class="answer-card chatbot">{r["cb_ans"]}</div>', unsafe_allow_html=True)
                    st.caption(f"⏱ {r['cb_ms']} ms | 🔤 {r['cb_tok']} tokens | 📞 1 LLM call")
                with c2:
                    st.markdown("🟢 **ReAct Agent** _(Thought → Action → Observation loop)_")
                    st.markdown(f'<div class="answer-card agent">{r["ag_ans"]}</div>', unsafe_allow_html=True)
                    st.caption(f"⏱ {r['ag_ms']} ms | 🔤 {r['ag_tok']} tokens | 🔁 {r['ag_steps']} steps")

        st.divider()
        st.markdown("#### 📊 Summary Table")
        import pandas as pd
        df = pd.DataFrame([{
            "ID": r["id"], "Type": r["label"],
            "Chatbot (ms)": r["cb_ms"], "Agent (ms)": r["ag_ms"],
            "Chatbot tokens": r["cb_tok"], "Agent tokens": r["ag_tok"],
            "Agent steps": r["ag_steps"],
        } for r in st.session_state["demo_results"]])
        st.dataframe(df, use_container_width=True, hide_index=True)

# =============================================================================
# TAB 3 — TEST TOOLS
# =============================================================================

with tab_tools:
    st.markdown("### 🔧 Test từng tool trực tiếp")

    try:
        from tools import ALL_TOOLS

        for tool in ALL_TOOLS:
            with st.expander(f"🔧 **{tool['name']}**", expanded=True):
                st.caption(tool["description"])
                col_in, col_btn = st.columns([4, 1])
                with col_in:
                    tool_input = st.text_input(
                        "Input",
                        key=f"tool_input_{tool['name']}",
                        placeholder={
                            "weather":        "Hanoi  |  forecast:Da Nang  |  compare:Hanoi|Ho Chi Minh City",
                            "calculator":     "18/100 * 1500000  |  (273 + 37) * 2",
                            "statistics":     "all:29,31,28,30,32  |  mean:25,30,28  |  median:10,20,30",
                            "percentage":     "15% of 200  |  what% is 30 of 200  |  change:32,29",
                            "unit_converter": "100 km to miles  |  37 celsius to fahrenheit  |  1000000 vnd to usd",
                            "datetime":       "today  |  now  |  days_until:2027-01-01",
                            "vietnam_info":   "Da Lat  |  Sa Pa climate  |  Phu Quoc best_visit  |  list",
                        }.get(tool["name"], ""),
                        label_visibility="collapsed",
                    )
                with col_btn:
                    if st.button("Run", key=f"tool_run_{tool['name']}"):
                        if tool_input:
                            result = tool["func"](tool_input)
                            st.success(f"✅ **Result**: {result}")
                        else:
                            st.warning("Nhập input trước.")
    except Exception as e:
        st.error(f"Lỗi load tools: {e}")

# =============================================================================
# TAB 4 — FAILURE ANALYSIS  (Objective 4)
# =============================================================================

with tab_analysis:
    st.markdown("### 📊 Failure Analysis  _(Objective 4)_")
    st.caption("Phân tích logs để tìm hallucinations, parsing errors, LLM errors và infinite loops.")

    from pathlib import Path as _P
    _log_dir = _P(__file__).parent / "logs"
    _log_files = sorted(_log_dir.glob("*.log"), reverse=True) if _log_dir.exists() else []

    if not _log_files:
        st.info("Chưa có log nào. Chạy Demo hoặc Chat tab trước để tạo log, rồi quay lại đây.")
    else:
        _col_sel, _col_all = st.columns([3, 1])
        with _col_sel:
            _sel_log = st.selectbox("Chọn file log để phân tích", [f.name for f in _log_files], key="analysis_log")
        with _col_all:
            _all_logs = st.checkbox("Tất cả logs", key="analysis_all")

        # Load records
        import json as _json
        def _load_records(path):
            recs = []
            with open(path, encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line:
                        try: recs.append(_json.loads(_line))
                        except: pass
            return recs

        if _all_logs:
            _records = []
            for _lf in _log_files:
                _records.extend(_load_records(_lf))
        else:
            _records = _load_records(_log_dir / _sel_log)

        if not _records:
            st.warning("File log trống.")
        else:
            # ── Metrics overview ─────────────────────────────────────────
            _starts_cb = sum(1 for r in _records if r["event"] == "CHATBOT_START")
            _ok_cb     = sum(1 for r in _records if r["event"] == "CHATBOT_RESPONSE")
            _starts_ag = sum(1 for r in _records if r["event"] == "AGENT_START")
            _ends_ag   = [r for r in _records if r["event"] == "AGENT_END"]
            _ok_ag     = sum(1 for r in _ends_ag if r["data"].get("success"))
            _parse_err = sum(1 for r in _records if r["event"] == "AGENT_PARSE_ERROR")
            _llm_err   = sum(1 for r in _records if r["event"] == "AGENT_LLM_ERROR")
            _loops     = sum(1 for r in _records if r["event"] == "AGENT_LOOP_DETECTED")

            st.markdown("#### Overview")
            _c1, _c2, _c3, _c4, _c5, _c6 = st.columns(6)
            _c1.metric("Chatbot calls",   _starts_cb)
            _c2.metric("Chatbot success", _ok_cb,
                       delta=f"{round(_ok_cb/_starts_cb*100) if _starts_cb else 0}%")
            _c3.metric("Agent calls",     _starts_ag)
            _c4.metric("Agent success",   _ok_ag,
                       delta=f"{round(_ok_ag/len(_ends_ag)*100) if _ends_ag else 0}%")
            _c5.metric("Parse errors",    _parse_err, delta_color="inverse")
            _c6.metric("LLM errors",      _llm_err,   delta_color="inverse")

            # ── Provider comparison ───────────────────────────────────────
            from collections import defaultdict as _dd
            _prov_counts = _dd(int)
            for _r in _records:
                _p = _r.get("data", {}).get("provider")
                if _p: _prov_counts[_p] += 1
            if _prov_counts:
                st.markdown("#### Provider Usage  _(Objective 3)_")
                import pandas as _pd
                _prov_df = _pd.DataFrame(
                    [{"Provider": k, "Calls": v} for k, v in sorted(_prov_counts.items())]
                )
                st.dataframe(_prov_df, use_container_width=True, hide_index=True)

            # ── Failure details ───────────────────────────────────────────
            st.markdown("#### Failure Details")
            _fail_tab1, _fail_tab2, _fail_tab3 = st.tabs([
                f"🔴 Parse Errors ({_parse_err})",
                f"🔴 LLM Errors ({_llm_err})",
                f"🔄 Loops ({_loops})",
            ])
            with _fail_tab1:
                _pe = [r for r in _records if r["event"] == "AGENT_PARSE_ERROR"]
                if not _pe:
                    st.success("Không có parse errors!")
                for _r in _pe:
                    _ts = _r.get("timestamp","")[:19].replace("T"," ")
                    st.warning(f"[{_ts}] Step {_r['data'].get('step','?')} — LLM không theo format Action:tool(args)")
                    st.code(_r["data"].get("raw_output","")[:300], language="text")

            with _fail_tab2:
                _le = [r for r in _records if r["event"] == "AGENT_LLM_ERROR"]
                if not _le:
                    st.success("Không có LLM errors!")
                for _r in _le:
                    _ts = _r.get("timestamp","")[:19].replace("T"," ")
                    st.error(f"[{_ts}] Step {_r['data'].get('step','?')} — {_r['data'].get('error','')}")

            with _fail_tab3:
                _lp = [r for r in _records if r["event"] == "AGENT_LOOP_DETECTED"]
                if not _lp:
                    st.success("Không có infinite loops!")
                for _r in _lp:
                    _ts = _r.get("timestamp","")[:19].replace("T"," ")
                    st.warning(f"[{_ts}] Step {_r['data'].get('step','?')} — Repeated: `{_r['data'].get('repeated_action','')}`")

            # ── Hallucination candidates ──────────────────────────────────
            st.markdown("#### ⚠️ Hallucination Candidates")
            st.caption("Chatbot trả lời câu hỏi thời tiết HIỆN TẠI mà không có tool — dữ liệu có thể bịa.")
            _rt_kw = ["lúc này","hôm nay","hiện tại","ngay lúc","bây giờ"]
            _hals = [r for r in _records
                     if r["event"] == "CHATBOT_RESPONSE"
                     and any(kw in r["data"].get("query","").lower() for kw in _rt_kw)]
            if not _hals:
                st.info("Không tìm thấy. (Chưa có chatbot trả lời real-time queries)")
            for _r in _hals:
                _ts = _r.get("timestamp","")[:19].replace("T"," ")
                with st.expander(f"[{_ts}] {_r['data'].get('query','')[:60]}", expanded=False):
                    st.markdown(f"**Query:** {_r['data'].get('query','')}")
                    st.markdown(f"**Chatbot answer:** {_r['data'].get('answer','')[:300]}")
                    st.error("⚠️ Không có real-time data — câu trả lời này có thể không chính xác")

            # ── Latency & token comparison ────────────────────────────────
            _cb_lats = [r["data"].get("latency_ms",0) for r in _records if r["event"]=="CHATBOT_RESPONSE"]
            _ag_lats = [r["data"].get("total_latency_ms",0) for r in _ends_ag]
            _cb_toks = [r["data"].get("total_tokens",0) for r in _records if r["event"]=="CHATBOT_RESPONSE"]
            _ag_toks = [r["data"].get("total_tokens",0) for r in _ends_ag]
            if _cb_lats or _ag_lats:
                st.markdown("#### 📈 Latency & Token Comparison")
                import pandas as _pd
                _comp_df = _pd.DataFrame([
                    {"Metric": "Avg Latency (ms)", "Chatbot": round(sum(_cb_lats)/len(_cb_lats)) if _cb_lats else 0,
                     "Agent": round(sum(_ag_lats)/len(_ag_lats)) if _ag_lats else 0},
                    {"Metric": "Avg Tokens",       "Chatbot": round(sum(_cb_toks)/len(_cb_toks)) if _cb_toks else 0,
                     "Agent": round(sum(_ag_toks)/len(_ag_toks)) if _ag_toks else 0},
                    {"Metric": "LLM Calls (avg)",  "Chatbot": 1,
                     "Agent": round(sum(r["data"].get("steps_used",1) for r in _ends_ag)/len(_ends_ag),1) if _ends_ag else 0},
                ])
                st.dataframe(_comp_df, use_container_width=True, hide_index=True)


# =============================================================================
# TAB 5 — LOGS
# =============================================================================

with tab_logs:
    st.markdown("### 📊 Log Viewer")

    log_dir = Path(__file__).parent / "logs"
    log_files = sorted(log_dir.glob("*.log"), reverse=True) if log_dir.exists() else []

    if not log_files:
        st.info("Chưa có log nào. Chạy thử từ tab Chat hoặc Demo để tạo log.")
    else:
        selected_log = st.selectbox(
            "Chọn file log",
            [f.name for f in log_files],
            index=0,
        )

        log_path = log_dir / selected_log
        events = []
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("{"):
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        pass

        if not events:
            st.warning("File log trống hoặc không có JSON event nào.")
        else:
            # Metrics summary
            agent_ends = [e for e in events if e["event"] == "AGENT_END"]
            llm_metrics = [e for e in events if e["event"] in ("AGENT_LLM_OUTPUT", "CHATBOT_RESPONSE")]
            chatbot_responses = [e for e in events if e["event"] == "CHATBOT_RESPONSE"]

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Tổng events", len(events))
            col2.metric("Agent runs", len(agent_ends))
            success_count = sum(1 for e in agent_ends if e["data"].get("success"))
            col3.metric("Agent thành công", success_count)
            col4.metric("Chatbot responses", len(chatbot_responses))

            st.divider()

            # Filter
            event_types = sorted({e["event"] for e in events})
            selected_types = st.multiselect(
                "Lọc theo event type",
                event_types,
                default=event_types,
            )

            filtered = [e for e in events if e["event"] in selected_types]
            st.caption(f"Hiển thị {len(filtered)} / {len(events)} events")

            # Display events
            for e in reversed(filtered[-100:]):
                ts = e.get("timestamp", "")[:19].replace("T", " ")
                ev = e.get("event", "")
                data = e.get("data", {})

                # Color by type
                if "ERROR" in ev or "FAIL" in ev:
                    icon, color = "🔴", "#f38ba8"
                elif "FINAL_ANSWER" in ev or "RESPONSE" in ev:
                    icon, color = "🟢", "#a6e3a1"
                elif "ACTION" in ev:
                    icon, color = "🟡", "#f9e2af"
                elif "START" in ev:
                    icon, color = "🔵", "#89b4fa"
                else:
                    icon, color = "⚪", "#6c7086"

                with st.expander(
                    f"{icon} `{ev}` — {ts}",
                    expanded=False,
                ):
                    st.json(data)

        # Refresh button
        if st.button("🔄 Refresh"):
            st.rerun()
