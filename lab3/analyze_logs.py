"""
analyze_logs.py — Failure Analysis cho Lab 3.

Objective 4: Failure Analysis
  Đọc structured logs trong lab3/logs/ để xác định tại sao agent fails:
    - Hallucinations (chatbot trả lời real-time query không có data)
    - Parsing errors  (AGENT_PARSE_ERROR)
    - LLM errors      (AGENT_LLM_ERROR)
    - Infinite loops  (AGENT_LOOP_DETECTED)

Cách chạy:
    cd lab3
    python analyze_logs.py
    python analyze_logs.py --date 2026-04-06   # log của ngày cụ thể
    python analyze_logs.py --all               # tất cả log files
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# =============================================================================
# LOAD LOGS
# =============================================================================

LOG_DIR = Path(__file__).parent / "logs"


def load_log_file(path: Path) -> list:
    """Đọc 1 file .log, trả về list các JSON records."""
    records = []
    try:
        with open(path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"  [WARN] Line {lineno} in {path.name}: invalid JSON — skipped")
    except FileNotFoundError:
        print(f"  [WARN] File not found: {path}")
    return records


def load_logs(date_str: str = None, all_files: bool = False) -> list:
    """
    Tải logs từ thư mục lab3/logs/.

    Args:
        date_str:  'YYYY-MM-DD' — chỉ load file của ngày đó.
        all_files: True — load tất cả .log files.

    Returns:
        List tất cả records (dict).
    """
    if not LOG_DIR.exists():
        return []

    log_files = sorted(LOG_DIR.glob("*.log"))
    if not log_files:
        return []

    if date_str:
        target = LOG_DIR / f"{date_str}.log"
        log_files = [target] if target.exists() else []
    elif not all_files:
        log_files = [log_files[-1]]  # mặc định: file mới nhất

    records = []
    for f in log_files:
        batch = load_log_file(f)
        records.extend(batch)
        print(f"  Loaded {len(batch):4d} records  ←  {f.name}")
    return records


# =============================================================================
# ANALYSIS
# =============================================================================

def count_events(records: list) -> dict:
    counts = defaultdict(int)
    for r in records:
        counts[r.get("event", "UNKNOWN")] += 1
    return dict(counts)


def chatbot_stats(records: list) -> dict:
    starts    = [r for r in records if r["event"] == "CHATBOT_START"]
    responses = [r for r in records if r["event"] == "CHATBOT_RESPONSE"]
    errors    = [r for r in records if r["event"] == "CHATBOT_ERROR"]

    total    = len(starts)
    success  = len(responses)
    failed   = len(errors)
    sr       = round(success / total * 100, 1) if total else 0

    latencies = [r["data"].get("latency_ms", 0) for r in responses]
    tokens    = [r["data"].get("total_tokens", 0) for r in responses]

    providers = defaultdict(int)
    for r in responses:
        providers[r["data"].get("provider", "unknown")] += 1

    return {
        "total":    total,
        "success":  success,
        "failed":   failed,
        "success_rate": sr,
        "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
        "avg_tokens":     round(sum(tokens)    / len(tokens))    if tokens    else 0,
        "providers": dict(providers),
    }


def agent_stats(records: list) -> dict:
    starts       = [r for r in records if r["event"] == "AGENT_START"]
    ends         = [r for r in records if r["event"] == "AGENT_END"]
    parse_errors = [r for r in records if r["event"] == "AGENT_PARSE_ERROR"]
    llm_errors   = [r for r in records if r["event"] == "AGENT_LLM_ERROR"]
    loops        = [r for r in records if r["event"] == "AGENT_LOOP_DETECTED"]
    actions      = [r for r in records if r["event"] == "AGENT_ACTION"]

    total   = len(starts)
    ended   = len(ends)
    success = sum(1 for r in ends if r["data"].get("success", False))
    sr      = round(success / ended * 100, 1) if ended else 0

    steps_list    = [r["data"].get("steps_used", 0) for r in ends]
    latencies     = [r["data"].get("total_latency_ms", 0) for r in ends]
    tokens_list   = [r["data"].get("total_tokens", 0) for r in ends]

    # Tool usage breakdown
    tool_counts = defaultdict(int)
    for r in actions:
        tool_counts[r["data"].get("tool", "unknown")] += 1

    providers = defaultdict(int)
    for r in ends:
        providers[r["data"].get("provider", "unknown")] += 1

    return {
        "total":        total,
        "success":      success,
        "failed":       ended - success,
        "success_rate": sr,
        "parse_errors": len(parse_errors),
        "llm_errors":   len(llm_errors),
        "loop_detected": len(loops),
        "avg_steps":    round(sum(steps_list) / len(steps_list), 1) if steps_list else 0,
        "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
        "avg_tokens":   round(sum(tokens_list) / len(tokens_list)) if tokens_list else 0,
        "tool_usage":   dict(tool_counts),
        "providers":    dict(providers),
    }


def failure_cases(records: list) -> list:
    """
    Lấy danh sách các trường hợp thất bại cụ thể:
    - Agent parse errors
    - Agent LLM errors
    - Agent loop detections
    - Chatbot errors
    """
    failures = []

    for r in records:
        event = r.get("event", "")
        data  = r.get("data", {})
        ts    = r.get("timestamp", "")[:19].replace("T", " ")

        if event == "AGENT_PARSE_ERROR":
            failures.append({
                "time":  ts,
                "type":  "🔴 Parse Error",
                "where": "Agent",
                "step":  data.get("step", "?"),
                "detail": data.get("raw_output", "")[:120],
            })
        elif event == "AGENT_LLM_ERROR":
            failures.append({
                "time":  ts,
                "type":  "🔴 LLM Error",
                "where": "Agent",
                "step":  data.get("step", "?"),
                "detail": data.get("error", "")[:120],
            })
        elif event == "AGENT_LOOP_DETECTED":
            failures.append({
                "time":  ts,
                "type":  "🟡 Infinite Loop",
                "where": "Agent",
                "step":  data.get("step", "?"),
                "detail": f"Repeated: {data.get('repeated_action', '')}",
            })
        elif event == "CHATBOT_ERROR":
            failures.append({
                "time":  ts,
                "type":  "🔴 Chatbot Error",
                "where": "Chatbot",
                "step":  "-",
                "detail": data.get("error", "")[:120],
            })

    return failures


def hallucination_candidates(records: list) -> list:
    """
    Tìm các câu trả lời chatbot có dấu hiệu hallucination:
    - Chatbot trả lời query về "thời tiết hiện tại" / "nhiệt độ lúc này"
      nhưng không có real-time data (không gọi tool).
    """
    real_time_keywords = [
        "lúc này", "hôm nay", "hiện tại", "ngay lúc", "bây giờ",
        "hôm nay có mưa", "nhiệt độ hôm nay", "thời tiết hôm nay",
    ]
    candidates = []
    for r in records:
        if r.get("event") != "CHATBOT_RESPONSE":
            continue
        query = r["data"].get("query", "").lower()
        if any(kw in query for kw in real_time_keywords):
            answer = r["data"].get("answer", "")
            ts     = r.get("timestamp", "")[:19].replace("T", " ")
            candidates.append({
                "time":   ts,
                "query":  r["data"].get("query", "")[:80],
                "answer": answer[:120],
                "note":   "Chatbot answered real-time query without tool — potential hallucination",
            })
    return candidates


# =============================================================================
# PRINT REPORT
# =============================================================================

SEP  = "=" * 68
SEP2 = "-" * 68


def print_report(records: list) -> None:
    if not records:
        print("\n  ⚠️  Không có log records. Hãy chạy chatbot.py và agent.py trước.")
        return

    print(f"\n{SEP}")
    print("  Lab 3 — Failure Analysis Report")
    print(f"  Total records: {len(records)}")
    print(SEP)

    # ── Event counts ──────────────────────────────────────────────────────────
    print("\n📋 EVENT COUNTS")
    print(SEP2)
    counts = count_events(records)
    for ev, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        bar = "█" * min(cnt, 40)
        print(f"  {ev:<30} {cnt:4d}  {bar}")

    # ── Chatbot stats ─────────────────────────────────────────────────────────
    print("\n🔵 CHATBOT STATS  (Objective 1 — Baseline)")
    print(SEP2)
    cs = chatbot_stats(records)
    if cs["total"] == 0:
        print("  Chưa có dữ liệu chatbot.")
    else:
        print(f"  Tổng queries     : {cs['total']}")
        print(f"  Thành công       : {cs['success']}  ({cs['success_rate']}%)")
        print(f"  Lỗi API          : {cs['failed']}")
        print(f"  Latency trung bình: {cs['avg_latency_ms']} ms")
        print(f"  Tokens trung bình : {cs['avg_tokens']}")
        if cs["providers"]:
            print(f"  Providers        : {cs['providers']}")

    # ── Agent stats ───────────────────────────────────────────────────────────
    print("\n🟢 AGENT STATS  (Objective 2 — ReAct Loop)")
    print(SEP2)
    ag = agent_stats(records)
    if ag["total"] == 0:
        print("  Chưa có dữ liệu agent.")
    else:
        print(f"  Tổng queries      : {ag['total']}")
        print(f"  Thành công        : {ag['success']}  ({ag['success_rate']}%)")
        print(f"  Thất bại          : {ag['failed']}")
        print(f"  Parse errors      : {ag['parse_errors']}  ← LLM không theo format")
        print(f"  LLM errors        : {ag['llm_errors']}   ← API call thất bại")
        print(f"  Infinite loops    : {ag['loop_detected']}   ← Loop guard kích hoạt")
        print(f"  Steps trung bình  : {ag['avg_steps']}")
        print(f"  Latency trung bình: {ag['avg_latency_ms']} ms")
        print(f"  Tokens trung bình : {ag['avg_tokens']}")
        if ag["tool_usage"]:
            print(f"  Tool usage        : {ag['tool_usage']}")
        if ag["providers"]:
            print(f"  Providers         : {ag['providers']}")

    # ── So sánh ───────────────────────────────────────────────────────────────
    print("\n📊 SO SÁNH  CHATBOT  vs  AGENT")
    print(SEP2)
    cs_lat = cs['avg_latency_ms']
    ag_lat = ag['avg_latency_ms']
    cs_tok = cs['avg_tokens']
    ag_tok = ag['avg_tokens']
    print(f"  {'Chỉ số':<25} {'Chatbot':>12} {'Agent':>12}  {'Nhận xét'}")
    print(f"  {'-'*24} {'-'*12} {'-'*12}  {'-'*20}")
    print(f"  {'Success rate':<25} {str(cs['success_rate'])+'%':>12} {str(ag['success_rate'])+'%':>12}")
    print(f"  {'Avg latency (ms)':<25} {cs_lat:>12} {ag_lat:>12}  {'Agent chậm hơn' if ag_lat > cs_lat else 'Agent nhanh hơn'}")
    print(f"  {'Avg tokens':<25} {cs_tok:>12} {ag_tok:>12}  {'Agent tốn hơn' if ag_tok > cs_tok else 'Chatbot tốn hơn'}")
    print(f"  {'LLM calls (avg)':<25} {'1':>12} {str(ag['avg_steps']) if ag['total'] else '?':>12}  Agent multi-step")
    print(f"  {'Has real-time data':<25} {'❌ No':>12} {'✅ Yes':>12}  Agent wins on accuracy")

    # ── Failure cases ─────────────────────────────────────────────────────────
    failures = failure_cases(records)
    print(f"\n🔴 FAILURE CASES  ({len(failures)} total)")
    print(SEP2)
    if not failures:
        print("  ✅ Không có failure cases trong log này.")
    else:
        for f in failures[:15]:  # show tối đa 15
            print(f"  [{f['time']}] {f['type']}  Step {f['step']}")
            print(f"    → {f['detail']}")

    # ── Hallucination candidates ──────────────────────────────────────────────
    hallucinations = hallucination_candidates(records)
    print(f"\n⚠️  HALLUCINATION CANDIDATES  ({len(hallucinations)} real-time queries answered by chatbot)")
    print(SEP2)
    if not hallucinations:
        print("  Không tìm thấy. (Chưa có log chatbot trả lời real-time queries)")
    else:
        for h in hallucinations[:10]:
            print(f"  [{h['time']}] Query: {h['query']}")
            print(f"    Answer: {h['answer']}")
            print(f"    ⚠️  {h['note']}")
            print()

    print(f"\n{SEP}")
    print("  Tip: Chạy agent.py --provider gemini để so sánh provider switching")
    print(f"{SEP}\n")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print(f"\n{'='*68}")
    print("  Lab 3 — Failure Analysis  (Objective 4)")
    print(f"{'='*68}")
    print(f"  Log directory: {LOG_DIR}")

    date_arg = None
    all_flag = False
    for arg in sys.argv[1:]:
        if arg == "--all":
            all_flag = True
        elif arg.startswith("--date"):
            parts = arg.split("=")
            if len(parts) == 2:
                date_arg = parts[1]
            elif len(sys.argv) > sys.argv.index(arg) + 1:
                date_arg = sys.argv[sys.argv.index(arg) + 1]

    if not LOG_DIR.exists() or not list(LOG_DIR.glob("*.log")):
        print("\n  ⚠️  Thư mục logs/ trống. Hãy chạy trước:")
        print("     python chatbot.py")
        print("     python agent.py")
        print("  Sau đó chạy lại: python analyze_logs.py")
    else:
        print()
        records = load_logs(date_str=date_arg, all_files=all_flag)
        print_report(records)
