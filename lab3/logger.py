"""
logger.py — Structured JSON logger cho Lab 3.

Ghi mỗi event thành 1 dòng JSON vào logs/YYYY-MM-DD.log.
Format tương thích với analyze_logs.py ở thư mục gốc.
"""

import json
import os
from datetime import datetime, timezone


def _get_log_path() -> str:
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    filename = datetime.now().strftime("%Y-%m-%d") + ".log"
    return os.path.join(log_dir, filename)


def log(event: str, data: dict) -> None:
    """
    Ghi một event JSON vào file log.

    Args:
        event: Tên event (vd: 'CHATBOT_RESPONSE', 'AGENT_STEP', ...).
        data:  Dict chứa thông tin của event.
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "data": data,
    }
    line = json.dumps(record, ensure_ascii=False)
    with open(_get_log_path(), "a", encoding="utf-8") as f:
        f.write(line + "\n")
