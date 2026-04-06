"""
weather_tool.py — Công cụ tra cứu thời tiết thực tế cho các tỉnh thành Việt Nam.

Dùng wttr.in API (miễn phí, không cần API key).

Lệnh hỗ trợ:
  weather(<tên tỉnh/thành>)           → thời tiết hiện tại
  weather(forecast:<tên tỉnh/thành>)  → dự báo 3 ngày tới
  weather(compare:<tỉnh1>|<tỉnh2>)    → so sánh thời tiết 2 địa điểm

Ví dụ:
  weather(Hanoi)
  weather(forecast:Da Nang)
  weather(compare:Hanoi|Ho Chi Minh)
"""

import requests
from typing import Optional

# ---------------------------------------------------------------------------
# Bản đồ tên tiếng Việt → tên tiếng Anh cho API
# ---------------------------------------------------------------------------

_LOCATION_MAP: dict[str, str] = {
    # Miền Bắc
    "hà nội": "Hanoi",
    "hanoi": "Hanoi",
    "ha noi": "Hanoi",
    "hải phòng": "Hai Phong",
    "hai phong": "Hai Phong",
    "haiphong": "Hai Phong",
    "quảng ninh": "Ha Long",
    "quang ninh": "Ha Long",
    "hạ long": "Ha Long",
    "ha long": "Ha Long",
    "nam định": "Nam Dinh",
    "nam dinh": "Nam Dinh",
    "thái nguyên": "Thai Nguyen",
    "thai nguyen": "Thai Nguyen",
    "lào cai": "Lao Cai",
    "lao cai": "Lao Cai",
    "sapa": "Sa Pa",
    "sa pa": "Sa Pa",
    "điện biên": "Dien Bien Phu",
    "dien bien": "Dien Bien Phu",
    # Miền Trung
    "đà nẵng": "Da Nang",
    "da nang": "Da Nang",
    "danang": "Da Nang",
    "huế": "Hue",
    "hue": "Hue",
    "quảng bình": "Dong Hoi",
    "quang binh": "Dong Hoi",
    "quảng nam": "Tam Ky",
    "quang nam": "Tam Ky",
    "nha trang": "Nha Trang",
    "khánh hòa": "Nha Trang",
    "khanh hoa": "Nha Trang",
    "quy nhơn": "Quy Nhon",
    "quy nhon": "Quy Nhon",
    "bình định": "Quy Nhon",
    "binh dinh": "Quy Nhon",
    "đà lạt": "Da Lat",
    "da lat": "Da Lat",
    "dalat": "Da Lat",
    "lâm đồng": "Da Lat",
    "lam dong": "Da Lat",
    "phan thiết": "Phan Thiet",
    "phan thiet": "Phan Thiet",
    # Miền Nam
    "hồ chí minh": "Ho Chi Minh City",
    "ho chi minh": "Ho Chi Minh City",
    "hcmc": "Ho Chi Minh City",
    "sài gòn": "Ho Chi Minh City",
    "saigon": "Ho Chi Minh City",
    "tphcm": "Ho Chi Minh City",
    "tp hcm": "Ho Chi Minh City",
    "cần thơ": "Can Tho",
    "can tho": "Can Tho",
    "vũng tàu": "Vung Tau",
    "vung tau": "Vung Tau",
    "bình dương": "Thu Dau Mot",
    "binh duong": "Thu Dau Mot",
    "đồng nai": "Bien Hoa",
    "dong nai": "Bien Hoa",
    "long an": "Tan An",
    "tiền giang": "My Tho",
    "tien giang": "My Tho",
    "kiên giang": "Rach Gia",
    "kien giang": "Rach Gia",
    "phú quốc": "Phu Quoc",
    "phu quoc": "Phu Quoc",
    "an giang": "Long Xuyen",
    "long xuyên": "Long Xuyen",
}

_WEATHER_ICONS = {
    "sunny": "☀️", "clear": "☀️",
    "partly cloudy": "⛅", "partly": "⛅",
    "cloudy": "☁️", "overcast": "☁️",
    "mist": "🌫️", "fog": "🌫️", "haze": "🌫️",
    "rain": "🌧️", "drizzle": "🌦️", "shower": "🌦️",
    "thunder": "⛈️", "storm": "⛈️",
    "snow": "❄️", "blizzard": "🌨️",
    "sleet": "🌨️", "ice": "🧊",
}


def _get_weather_icon(desc: str) -> str:
    d = desc.lower()
    for key, icon in _WEATHER_ICONS.items():
        if key in d:
            return icon
    return "🌡️"


def _normalize_location(loc: str) -> str:
    """Chuyển tên tiếng Việt/viết tắt sang tên API."""
    return _LOCATION_MAP.get(loc.lower().strip(), loc.strip())


def _fetch_weather(location: str) -> Optional[dict]:
    """Gọi wttr.in và trả về dict dữ liệu thô, hoặc None nếu lỗi."""
    url = f"https://wttr.in/{requests.utils.quote(location)}?format=j1"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _current_summary(data: dict, location: str) -> str:
    """Tóm tắt thời tiết hiện tại."""
    cur = data["current_condition"][0]
    desc = cur["weatherDesc"][0]["value"]
    icon = _get_weather_icon(desc)
    temp_c = cur["temp_C"]
    feels  = cur["FeelsLikeC"]
    humidity = cur["humidity"]
    wind_kmh = cur["windspeedKmph"]
    wind_dir = cur["winddir16Point"]
    uv = cur.get("uvIndex", "N/A")
    vis = cur["visibility"]
    pressure = cur["pressure"]

    return (
        f"{icon} Thời tiết tại {location}:\n"
        f"  • Mô tả   : {desc}\n"
        f"  • Nhiệt độ: {temp_c}°C (cảm giác như {feels}°C)\n"
        f"  • Độ ẩm   : {humidity}%\n"
        f"  • Gió     : {wind_kmh} km/h hướng {wind_dir}\n"
        f"  • UV Index: {uv}\n"
        f"  • Tầm nhìn: {vis} km\n"
        f"  • Áp suất : {pressure} hPa"
    )


def _forecast_summary(data: dict, location: str) -> str:
    """Dự báo 3 ngày tới."""
    lines = [f"📅 Dự báo thời tiết tại {location} (3 ngày):"]
    for day in data.get("weather", []):
        date = day["date"]
        max_c = day["maxtempC"]
        min_c = day["mintempC"]
        desc = day["hourly"][4]["weatherDesc"][0]["value"]  # buổi trưa
        icon = _get_weather_icon(desc)
        rain = day["hourly"][4].get("precipMM", "0")
        lines.append(
            f"  {icon} {date}: {min_c}°C – {max_c}°C, {desc}, mưa: {rain}mm"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def get_weather(query: str) -> str:
    """
    Tra cứu thời tiết thực tế cho các tỉnh thành Việt Nam.

    Args:
        query: Tên địa điểm hoặc lệnh đặc biệt.
               - "Hanoi"                   → thời tiết hiện tại Hà Nội
               - "forecast:Da Nang"        → dự báo 3 ngày Đà Nẵng
               - "compare:Hanoi|Saigon"    → so sánh 2 thành phố

    Returns:
        Chuỗi mô tả thời tiết.
    """
    query = query.strip()

    # ── Dự báo ─────────────────────────────────────────────────────────────
    if query.lower().startswith("forecast:"):
        raw_loc = query.split(":", 1)[1].strip()
        location = _normalize_location(raw_loc)
        data = _fetch_weather(location)
        if data is None:
            return f"Không lấy được dữ liệu thời tiết cho '{location}'. Kiểm tra tên địa điểm."
        return _forecast_summary(data, location)

    # ── So sánh 2 địa điểm ─────────────────────────────────────────────────
    if query.lower().startswith("compare:"):
        parts = query.split(":", 1)[1].split("|")
        if len(parts) != 2:
            return "Format so sánh sai. Dùng: compare:ThanhPho1|ThanhPho2"
        loc1 = _normalize_location(parts[0].strip())
        loc2 = _normalize_location(parts[1].strip())
        d1 = _fetch_weather(loc1)
        d2 = _fetch_weather(loc2)
        if d1 is None:
            return f"Không lấy được dữ liệu cho '{loc1}'."
        if d2 is None:
            return f"Không lấy được dữ liệu cho '{loc2}'."
        c1 = d1["current_condition"][0]
        c2 = d2["current_condition"][0]
        return (
            f"🔄 So sánh thời tiết hiện tại:\n\n"
            f"📍 {loc1}:\n"
            f"  {_get_weather_icon(c1['weatherDesc'][0]['value'])} {c1['weatherDesc'][0]['value']}, "
            f"{c1['temp_C']}°C, độ ẩm {c1['humidity']}%\n\n"
            f"📍 {loc2}:\n"
            f"  {_get_weather_icon(c2['weatherDesc'][0]['value'])} {c2['weatherDesc'][0]['value']}, "
            f"{c2['temp_C']}°C, độ ẩm {c2['humidity']}%"
        )

    # ── Thời tiết hiện tại ─────────────────────────────────────────────────
    location = _normalize_location(query)
    data = _fetch_weather(location)
    if data is None:
        return (
            f"Không lấy được dữ liệu thời tiết cho '{location}'. "
            "Hãy thử tên tiếng Anh (Hanoi, Da Nang, Ho Chi Minh City…) hoặc kiểm tra kết nối."
        )
    return _current_summary(data, location)


WEATHER_TOOL = {
    "name": "weather",
    "description": (
        "Tra cứu thời tiết thực tế (real-time) cho các tỉnh thành Việt Nam. "
        "Hỗ trợ 3 dạng: "
        "(1) Thời tiết hiện tại: weather(Hanoi) hoặc weather(Hà Nội) — "
        "(2) Dự báo 3 ngày: weather(forecast:Da Nang) — "
        "(3) So sánh 2 thành phố: weather(compare:Hanoi|Ho Chi Minh City). "
        "Địa điểm hỗ trợ: Hà Nội, Hải Phòng, Đà Nẵng, Huế, Nha Trang, Đà Lạt, "
        "Hồ Chí Minh, Cần Thơ, Vũng Tàu, Phú Quốc, Hạ Long và nhiều tỉnh khác."
    ),
    "func": get_weather,
}
