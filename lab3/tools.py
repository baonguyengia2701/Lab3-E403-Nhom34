"""
tools.py — Tất cả tool definitions cho Lab 3.

Gồm 7 tools:
  - calculator     : Tính toán biểu thức toán học an toàn
  - datetime       : Truy vấn ngày giờ thực tế
  - unit_converter : Chuyển đổi đơn vị (độ dài, khối lượng, thời gian, tiền tệ, nhiệt độ)
  - weather        : Thời tiết thực tế các thành phố Việt Nam (từ wttr.in)
  - statistics     : Tính thống kê cơ bản trên dãy số (mean, min, max, sum, median)
  - percentage     : Tính phần trăm nhanh (x% of y, tăng/giảm %, so sánh %)
  - vietnam_info   : Tra cứu thông tin địa lý / khí hậu các tỉnh thành Việt Nam
"""

import ast
import operator
import re
from datetime import datetime, date
from typing import Union
from weather_tool import WEATHER_TOOL

# =============================================================================
# TOOL 1: CALCULATOR
# =============================================================================

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}


def _safe_eval(node) -> Union[int, float]:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise ValueError(f"Operator {op_type.__name__} is not allowed.")
        return _ALLOWED_OPERATORS[op_type](_safe_eval(node.left), _safe_eval(node.right))
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise ValueError(f"Operator {op_type.__name__} is not allowed.")
        return _ALLOWED_OPERATORS[op_type](_safe_eval(node.operand))
    else:
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def calculate(expression: str) -> str:
    """
    Tính toán biểu thức toán học an toàn (dùng AST, không eval tùy ý).
    Ví dụ: calculate("18/100 * 1500000") → "270000"
    """
    expression = expression.strip().strip("'\"")
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return str(round(result, 6))
    except ZeroDivisionError:
        return "Error: Division by zero."
    except Exception as e:
        return f"Error evaluating '{expression}': {e}"


CALCULATOR_TOOL = {
    "name": "calculator",
    "description": (
        "Tính toán biểu thức toán học. Hỗ trợ: +, -, *, /, **, %, //. "
        "Input: biểu thức toán học dạng chuỗi. Ví dụ: '18/100 * 1500000'."
    ),
    "func": calculate,
}


# =============================================================================
# TOOL 2: DATETIME
# =============================================================================

def query_datetime(command: str) -> str:
    """
    Truy vấn ngày giờ thực tế từ hệ thống.
    Lệnh hỗ trợ:
      - 'today'                   → ngày hôm nay
      - 'now'                     → ngày và giờ hiện tại
      - 'weekday'                 → thứ trong tuần
      - 'days_until:YYYY-MM-DD'   → số ngày còn lại đến ngày đó
      - 'days_since:YYYY-MM-DD'   → số ngày đã qua kể từ ngày đó
    """
    command = command.strip().strip("'\"").lower()
    today = date.today()
    now = datetime.now()

    if command == "today":
        return f"Today's date is {today.strftime('%A, %B %d, %Y')}."
    if command == "now":
        return f"Current date and time: {now.strftime('%A, %B %d, %Y at %H:%M:%S')}."
    if command == "weekday":
        return f"Today is {today.strftime('%A')}."

    if command.startswith("days_until:"):
        target_str = command.split("days_until:", 1)[1].strip()
        try:
            target = date.fromisoformat(target_str)
        except ValueError:
            return f"Error: Invalid date format '{target_str}'. Use YYYY-MM-DD."
        delta = (target - today).days
        if delta < 0:
            return f"The date {target_str} has already passed ({abs(delta)} days ago)."
        return f"There are {delta} days remaining until {target_str}."

    if command.startswith("days_since:"):
        target_str = command.split("days_since:", 1)[1].strip()
        try:
            target = date.fromisoformat(target_str)
        except ValueError:
            return f"Error: Invalid date format '{target_str}'. Use YYYY-MM-DD."
        delta = (today - target).days
        if delta < 0:
            return f"The date {target_str} is in the future ({abs(delta)} days from now)."
        return f"{delta} days have passed since {target_str}."

    return (
        f"Unknown command '{command}'. "
        "Supported: 'today', 'now', 'weekday', 'days_until:YYYY-MM-DD', 'days_since:YYYY-MM-DD'."
    )


DATETIME_TOOL = {
    "name": "datetime",
    "description": (
        "Truy vấn ngày giờ thực tế. "
        "Lệnh: 'today', 'now', 'weekday', 'days_until:YYYY-MM-DD', 'days_since:YYYY-MM-DD'. "
        "Ví dụ: datetime(days_until:2027-01-01)"
    ),
    "func": query_datetime,
}


# =============================================================================
# TOOL 3: UNIT CONVERTER
# =============================================================================

_LENGTH_TO_METERS = {
    "km": 1000.0, "kilometer": 1000.0, "kilometers": 1000.0,
    "m": 1.0, "meter": 1.0, "meters": 1.0,
    "cm": 0.01, "centimeter": 0.01, "centimeters": 0.01,
    "mm": 0.001, "millimeter": 0.001, "millimeters": 0.001,
    "mile": 1609.344, "miles": 1609.344, "mi": 1609.344,
    "yard": 0.9144, "yards": 0.9144, "yd": 0.9144,
    "foot": 0.3048, "feet": 0.3048, "ft": 0.3048,
    "inch": 0.0254, "inches": 0.0254,
}
_MASS_TO_KG = {
    "kg": 1.0, "kilogram": 1.0, "kilograms": 1.0,
    "g": 0.001, "gram": 0.001, "grams": 0.001,
    "lb": 0.453592, "lbs": 0.453592, "pound": 0.453592, "pounds": 0.453592,
    "oz": 0.0283495, "ounce": 0.0283495, "ounces": 0.0283495,
    "tonne": 1000.0, "ton": 1000.0, "tons": 1000.0,
}
_TIME_TO_SECONDS = {
    "second": 1.0, "seconds": 1.0, "sec": 1.0, "s": 1.0,
    "minute": 60.0, "minutes": 60.0, "min": 60.0,
    "hour": 3600.0, "hours": 3600.0, "hr": 3600.0,
    "day": 86400.0, "days": 86400.0,
    "week": 604800.0, "weeks": 604800.0,
    "year": 31536000.0, "years": 31536000.0,
}
_CURRENCY_TO_USD = {
    "usd": 1.0, "dollar": 1.0, "dollars": 1.0,
    "vnd": 1 / 25400.0, "dong": 1 / 25400.0,
    "eur": 1.08, "euro": 1.08, "euros": 1.08,
    "gbp": 1.27, "jpy": 1 / 150.0, "yen": 1 / 150.0,
    "cny": 1 / 7.24, "yuan": 1 / 7.24,
    "krw": 1 / 1350.0, "won": 1 / 1350.0,
    "thb": 1 / 35.0, "baht": 1 / 35.0,
    "sgd": 0.74, "aud": 0.65,
}
_CATEGORY_TABLES = [_LENGTH_TO_METERS, _MASS_TO_KG, _TIME_TO_SECONDS, _CURRENCY_TO_USD]


def _find_category(unit: str):
    key = unit.lower().strip()
    for table in _CATEGORY_TABLES:
        if key in table:
            return table
    return None


def _convert_temperature(value: float, from_unit: str, to_unit: str):
    f, t = from_unit.lower().strip(), to_unit.lower().strip()
    temp_units = {"celsius", "c", "fahrenheit", "f", "kelvin", "k"}
    if f not in temp_units or t not in temp_units:
        return None
    celsius = value if f in ("celsius", "c") else (value - 32) * 5 / 9 if f in ("fahrenheit", "f") else value - 273.15
    if t in ("celsius", "c"):
        return celsius
    elif t in ("fahrenheit", "f"):
        return celsius * 9 / 5 + 32
    return celsius + 273.15


def convert_units(query: str) -> str:
    """
    Chuyển đổi đơn vị. Format: '<số> <đơn vị> to <đơn vị>'.
    Ví dụ: '100 km to miles', '37 celsius to fahrenheit', '1000000 vnd to usd'.
    """
    query = query.strip().lower()
    match = re.match(r"^([\d,._]+)\s+([a-z_]+)\s+to\s+([a-z_]+)$", query, re.IGNORECASE)
    if not match:
        return "Format sai. Dùng: '<số> <đơn vị> to <đơn vị>'. Ví dụ: '100 km to miles'."
    raw_value, from_unit, to_unit = match.group(1), match.group(2), match.group(3)
    try:
        value = float(raw_value.replace(",", ""))
    except ValueError:
        return f"Số không hợp lệ: '{raw_value}'."

    temp_result = _convert_temperature(value, from_unit, to_unit)
    if temp_result is not None:
        return f"{value} {from_unit} = {round(temp_result, 4)} {to_unit}"

    from_table = _find_category(from_unit)
    to_table = _find_category(to_unit)
    if from_table is None:
        return f"Đơn vị '{from_unit}' không được hỗ trợ."
    if to_table is None:
        return f"Đơn vị '{to_unit}' không được hỗ trợ."
    if from_table is not to_table:
        return f"Không thể chuyển '{from_unit}' sang '{to_unit}': khác loại đơn vị."

    result = value * from_table[from_unit.lower().strip()] / to_table[to_unit.lower().strip()]
    result_str = str(int(result)) if isinstance(result, float) and result.is_integer() else str(round(result, 6))
    return f"{value} {from_unit} = {result_str} {to_unit}"


UNIT_CONVERTER_TOOL = {
    "name": "unit_converter",
    "description": (
        "Chuyển đổi đơn vị: độ dài (km, miles, m, ft…), khối lượng (kg, lb, g…), "
        "thời gian (seconds, minutes, hours, days…), tiền tệ (VND, USD, EUR…), "
        "nhiệt độ (celsius, fahrenheit, kelvin). "
        "Format: '<số> <đơn vị> to <đơn vị>'. Ví dụ: '100 km to miles'."
    ),
    "func": convert_units,
}


# =============================================================================
# TOOL 5: STATISTICS
# =============================================================================

def calculate_statistics(query: str) -> str:
    """
    Tính thống kê cơ bản trên một dãy số.

    Cú pháp: '<lệnh>:<số1>,<số2>,...'
    Lệnh hỗ trợ:
      mean   → giá trị trung bình
      min    → giá trị nhỏ nhất
      max    → giá trị lớn nhất
      sum    → tổng
      median → giá trị trung vị
      all    → tất cả các chỉ số trên

    Ví dụ:
      statistics(mean:29,31,28,30)   → "Mean: 29.5"
      statistics(all:25,30,28,32,27) → "Mean: 28.4, Min: 25, Max: 32, Sum: 142, Median: 28"
    """
    query = query.strip().strip("'\"")
    if ":" not in query:
        return "Format sai. Dùng: '<lệnh>:<số1>,<số2>,...'. Ví dụ: 'mean:29,31,28,30'."

    cmd, _, raw_numbers = query.partition(":")
    cmd = cmd.strip().lower()

    try:
        numbers = [float(n.strip()) for n in raw_numbers.split(",") if n.strip()]
    except ValueError:
        return f"Không parse được dãy số: '{raw_numbers}'. Dùng dấu phẩy để phân tách."

    if not numbers:
        return "Dãy số trống."

    n = len(numbers)
    total = sum(numbers)
    mean_val = total / n
    min_val = min(numbers)
    max_val = max(numbers)
    sorted_nums = sorted(numbers)
    median_val = (sorted_nums[n // 2 - 1] + sorted_nums[n // 2]) / 2 if n % 2 == 0 else sorted_nums[n // 2]

    def fmt(v):
        return str(int(v)) if float(v).is_integer() else str(round(v, 2))

    if cmd == "mean":
        return f"Mean ({n} giá trị): {fmt(mean_val)}"
    if cmd == "min":
        return f"Min: {fmt(min_val)}"
    if cmd == "max":
        return f"Max: {fmt(max_val)}"
    if cmd == "sum":
        return f"Sum: {fmt(total)}"
    if cmd == "median":
        return f"Median: {fmt(median_val)}"
    if cmd in ("all", "summary", "stats"):
        return (
            f"Mean: {fmt(mean_val)}, Min: {fmt(min_val)}, Max: {fmt(max_val)}, "
            f"Sum: {fmt(total)}, Median: {fmt(median_val)} (n={n})"
        )
    return (
        f"Lệnh '{cmd}' không hỗ trợ. "
        "Dùng: mean | min | max | sum | median | all."
    )


STATISTICS_TOOL = {
    "name": "statistics",
    "description": (
        "Tính thống kê cơ bản trên dãy số: mean, min, max, sum, median. "
        "Format: '<lệnh>:<số1>,<số2>,...'. "
        "Ví dụ: 'mean:29,31,28,30' → Mean: 29.5 | 'all:25,30,28' → tất cả chỉ số."
    ),
    "func": calculate_statistics,
}


# =============================================================================
# TOOL 6: PERCENTAGE
# =============================================================================

def calculate_percentage(query: str) -> str:
    """
    Tính phần trăm nhanh.

    Cú pháp hỗ trợ:
      '<x>% of <y>'          → x% của y bằng bao nhiêu?
      'what% is <x> of <y>'  → x chiếm bao nhiêu % của y?
      'increase:<cũ>,<mới>'  → % tăng từ cũ lên mới
      'decrease:<cũ>,<mới>'  → % giảm từ cũ xuống mới
      'change:<cũ>,<mới>'    → % thay đổi (tăng hoặc giảm)

    Ví dụ:
      percentage(15% of 200)         → "15% of 200 = 30.0"
      percentage(what% is 30 of 200) → "30 là 15.0% của 200"
      percentage(increase:20,25)     → "Tăng 25.0% (từ 20 lên 25)"
      percentage(change:32,29)       → "Giảm 9.38% (từ 32 xuống 29)"
    """
    query = query.strip().strip("'\"").lower()

    # Pattern: x% of y
    m = re.match(r"^([\d.]+)%\s+of\s+([\d.]+)$", query)
    if m:
        x, y = float(m.group(1)), float(m.group(2))
        result = x / 100 * y
        return f"{x}% of {y} = {round(result, 4)}"

    # Pattern: what% is x of y
    m = re.match(r"^what%\s+is\s+([\d.]+)\s+of\s+([\d.]+)$", query)
    if m:
        x, y = float(m.group(1)), float(m.group(2))
        if y == 0:
            return "Lỗi: mẫu số bằng 0."
        pct = x / y * 100
        return f"{x} là {round(pct, 2)}% của {y}"

    # Pattern: increase/decrease/change:<old>,<new>
    m = re.match(r"^(?:increase|decrease|change):([\d.]+),([\d.]+)$", query)
    if m:
        old_val, new_val = float(m.group(1)), float(m.group(2))
        if old_val == 0:
            return "Lỗi: giá trị gốc bằng 0."
        diff = new_val - old_val
        pct = diff / old_val * 100
        direction = "Tăng" if diff >= 0 else "Giảm"
        return f"{direction} {abs(round(pct, 2))}% (từ {old_val} {'lên' if diff >= 0 else 'xuống'} {new_val})"

    return (
        "Format không hợp lệ. Ví dụ:\n"
        "  '15% of 200'           → 15% của 200\n"
        "  'what% is 30 of 200'   → 30 chiếm % bao nhiêu của 200\n"
        "  'increase:20,25'       → % tăng\n"
        "  'change:32,29'         → % thay đổi"
    )


PERCENTAGE_TOOL = {
    "name": "percentage",
    "description": (
        "Tính phần trăm nhanh. "
        "Cú pháp: '<x>% of <y>' | 'what% is <x> of <y>' | 'increase:<cũ>,<mới>' | 'change:<cũ>,<mới>'. "
        "Ví dụ: '70% of 200' → 140 | 'change:32,29' → Giảm 9.38%."
    ),
    "func": calculate_percentage,
}


# =============================================================================
# TOOL 7: VIETNAM INFO
# =============================================================================

_VIETNAM_CITIES = {
    "hà nội": {
        "region": "Miền Bắc", "province_type": "Thành phố trực thuộc TW",
        "altitude_m": 12, "area_km2": 3359,
        "climate": "Nhiệt đới gió mùa, 4 mùa rõ rệt",
        "hot_season": "Tháng 5–9 (30–38°C)", "cold_season": "Tháng 12–2 (12–18°C)",
        "rain_season": "Tháng 5–9", "dry_season": "Tháng 10–4",
        "best_visit": "Tháng 10–11 (mùa thu) hoặc tháng 3–4 (xuân ấm)",
        "note": "Thủ đô Việt Nam, đông dân nhất miền Bắc.",
    },
    "hồ chí minh": {
        "region": "Miền Nam", "province_type": "Thành phố trực thuộc TW",
        "altitude_m": 10, "area_km2": 2061,
        "climate": "Nhiệt đới gió mùa, 2 mùa (mưa/khô)",
        "hot_season": "Quanh năm (28–36°C), đỉnh tháng 3–4",
        "cold_season": "Không có mùa lạnh",
        "rain_season": "Tháng 5–11", "dry_season": "Tháng 12–4",
        "best_visit": "Tháng 12–4 (mùa khô, nắng đẹp)",
        "note": "Thành phố lớn nhất VN, trung tâm kinh tế phía Nam.",
    },
    "đà nẵng": {
        "region": "Miền Trung", "province_type": "Thành phố trực thuộc TW",
        "altitude_m": 10, "area_km2": 1285,
        "climate": "Nhiệt đới gió mùa, chịu ảnh hưởng bão miền Trung",
        "hot_season": "Tháng 5–9 (30–40°C, nắng gắt)",
        "cold_season": "Tháng 12–2 (18–22°C)",
        "rain_season": "Tháng 9–12 (mùa bão)", "dry_season": "Tháng 1–8",
        "best_visit": "Tháng 2–5 (trước mùa nóng, ít mưa)",
        "note": "Thành phố biển, cầu Rồng, Bà Nà Hills.",
    },
    "đà lạt": {
        "region": "Miền Nam (Tây Nguyên)", "province_type": "Thành phố thuộc tỉnh Lâm Đồng",
        "altitude_m": 1500, "area_km2": 394,
        "climate": "Cận ôn đới, mát quanh năm",
        "hot_season": "Không có (max ~25°C vào tháng 3–4)",
        "cold_season": "Tháng 11–2 (10–15°C, có thể dưới 10°C)",
        "rain_season": "Tháng 4–10", "dry_season": "Tháng 11–3",
        "best_visit": "Tháng 11–4 (mùa khô, hoa nở, se lạnh đẹp)",
        "note": "Cao nguyên 1500m, hoa cẩm tú cầu, hồ Xuân Hương.",
    },
    "nha trang": {
        "region": "Miền Nam (Duyên hải Nam Trung Bộ)", "province_type": "Thành phố thuộc tỉnh Khánh Hòa",
        "altitude_m": 10, "area_km2": 251,
        "climate": "Nhiệt đới gió mùa, ít bão hơn Đà Nẵng",
        "hot_season": "Tháng 6–8 (28–35°C)",
        "cold_season": "Tháng 1–2 (20–24°C, vẫn ấm)",
        "rain_season": "Tháng 9–12", "dry_season": "Tháng 1–8",
        "best_visit": "Tháng 2–6 (biển đẹp, ít mưa, nắng dịu)",
        "note": "Biển đẹp nhất miền Nam, lặn biển, đảo Hòn Tre.",
    },
    "sa pa": {
        "region": "Miền Bắc (Tây Bắc)", "province_type": "Thị xã thuộc tỉnh Lào Cai",
        "altitude_m": 1600, "area_km2": 684,
        "climate": "Cận ôn đới núi cao, sương mù thường xuyên",
        "hot_season": "Tháng 4–9 (18–25°C)",
        "cold_season": "Tháng 11–3 (0–10°C, có tuyết rơi năm dày)",
        "rain_season": "Tháng 5–8", "dry_season": "Tháng 9–4",
        "best_visit": "Tháng 9–10 (lúa chín vàng) hoặc tháng 3–4 (hoa đào nở)",
        "note": "Đỉnh Fansipan 3143m, ruộng bậc thang, trekking.",
    },
    "phú quốc": {
        "region": "Miền Nam (Đảo)", "province_type": "Thành phố thuộc tỉnh Kiên Giang",
        "altitude_m": 99, "area_km2": 589,
        "climate": "Nhiệt đới, ít bão, 2 mùa rõ rệt",
        "hot_season": "Tháng 3–4 (30–35°C)",
        "cold_season": "Không có mùa lạnh",
        "rain_season": "Tháng 6–9 (sóng to, biển động)", "dry_season": "Tháng 10–5",
        "best_visit": "Tháng 11–3 (mùa khô, biển lặng, nắng đẹp)",
        "note": "Đảo ngọc, resort 5 sao, lặn biển, hồ tiêu Phú Quốc.",
    },
    "hội an": {
        "region": "Miền Trung", "province_type": "Thành phố thuộc tỉnh Quảng Nam",
        "altitude_m": 5, "area_km2": 61,
        "climate": "Nhiệt đới ẩm, hay bị ngập lụt tháng 10–11",
        "hot_season": "Tháng 5–8 (30–38°C)",
        "cold_season": "Tháng 12–2 (18–22°C)",
        "rain_season": "Tháng 9–12", "dry_season": "Tháng 1–8",
        "best_visit": "Tháng 2–4 (mát, ít mưa, rực rỡ trước mùa hè)",
        "note": "Phố cổ UNESCO, đèn lồng, bánh mì Hội An, Cẩm Nam.",
    },
    "huế": {
        "region": "Miền Trung", "province_type": "Thành phố thuộc tỉnh Thừa Thiên Huế",
        "altitude_m": 3, "area_km2": 83,
        "climate": "Nhiệt đới, mưa nhiều nhất VN (>3000mm/năm)",
        "hot_season": "Tháng 5–8 (33–40°C, gió Lào khô nóng)",
        "cold_season": "Tháng 11–2 (15–20°C)",
        "rain_season": "Tháng 8–12 (mưa lũ nhiều)", "dry_season": "Tháng 1–7",
        "best_visit": "Tháng 1–3 (ít mưa nhất trong năm)",
        "note": "Cố đô, lăng tẩm, ẩm thực Huế, sông Hương.",
    },
    "cần thơ": {
        "region": "Miền Nam (Đồng bằng sông Cửu Long)", "province_type": "Thành phố trực thuộc TW",
        "altitude_m": 1, "area_km2": 1439,
        "climate": "Nhiệt đới, 2 mùa, ít bão",
        "hot_season": "Tháng 3–4 (32–36°C)",
        "cold_season": "Không có mùa lạnh",
        "rain_season": "Tháng 5–11", "dry_season": "Tháng 12–4",
        "best_visit": "Tháng 11–4 (mùa khô, chợ nổi Cái Răng)",
        "note": "Thủ phủ miền Tây, chợ nổi, sông nước, trái cây.",
    },
}


def get_vietnam_info(query: str) -> str:
    """
    Tra cứu thông tin địa lý, khí hậu các tỉnh thành Việt Nam.

    Cú pháp:
      '<tên thành phố>'                      → thông tin tổng quan
      '<tên thành phố> climate'              → chi tiết khí hậu
      '<tên thành phố> best_visit'           → thời điểm du lịch tốt nhất
      'list'                                 → danh sách các thành phố có sẵn

    Ví dụ:
      vietnam_info(Đà Lạt)
      vietnam_info(Sa Pa climate)
      vietnam_info(list)
    """
    query = query.strip().strip("'\"")

    if query.lower() == "list":
        cities = sorted(_VIETNAM_CITIES.keys())
        return "Các thành phố có sẵn: " + ", ".join(c.title() for c in cities)

    # Tách city và sub-command
    sub_cmd = None
    clean_q = query.lower()
    for sc in ("climate", "best_visit", "best visit", "weather", "season"):
        if clean_q.endswith(sc):
            sub_cmd = sc.replace(" ", "_")
            clean_q = clean_q[:-(len(sc))].strip()
            break

    # Alias tiếng Anh → tiếng Việt
    _ALIASES = {
        "ha noi": "hà nội", "hanoi": "hà nội",
        "ho chi minh": "hồ chí minh", "hcm": "hồ chí minh", "saigon": "hồ chí minh",
        "da nang": "đà nẵng", "danang": "đà nẵng",
        "da lat": "đà lạt", "dalat": "đà lạt",
        "nha trang": "nha trang",
        "sa pa": "sa pa", "sapa": "sa pa",
        "phu quoc": "phú quốc", "phuquoc": "phú quốc",
        "hoi an": "hội an", "hoian": "hội an",
        "hue": "huế",
        "can tho": "cần thơ", "cantho": "cần thơ",
    }
    if clean_q in _ALIASES:
        clean_q = _ALIASES[clean_q]

    # Tìm khớp tên thành phố (fuzzy: chứa tên)
    city_key = None
    for key in _VIETNAM_CITIES:
        if key in clean_q or clean_q in key:
            city_key = key
            break

    if city_key is None:
        available = ", ".join(c.title() for c in sorted(_VIETNAM_CITIES.keys()))
        return (
            f"Không tìm thấy '{query}'. "
            f"Gợi ý: {available}. "
            "Hoặc dùng 'list' để xem danh sách."
        )

    info = _VIETNAM_CITIES[city_key]

    if sub_cmd in ("climate", "weather", "season"):
        return (
            f"📍 {city_key.title()} — Khí hậu:\n"
            f"  Loại: {info['climate']}\n"
            f"  Mùa nóng : {info['hot_season']}\n"
            f"  Mùa lạnh : {info['cold_season']}\n"
            f"  Mùa mưa  : {info['rain_season']}\n"
            f"  Mùa khô  : {info['dry_season']}"
        )
    if sub_cmd in ("best_visit", "best visit"):
        return f"📍 {city_key.title()} — Thời điểm du lịch tốt nhất: {info['best_visit']}"

    # Thông tin tổng quan
    return (
        f"📍 {city_key.title()} ({info['region']})\n"
        f"  Loại       : {info['province_type']}\n"
        f"  Độ cao     : {info['altitude_m']}m   |   Diện tích: {info['area_km2']} km²\n"
        f"  Khí hậu    : {info['climate']}\n"
        f"  Mùa mưa    : {info['rain_season']}   |   Mùa khô: {info['dry_season']}\n"
        f"  Du lịch đẹp: {info['best_visit']}\n"
        f"  Ghi chú    : {info['note']}"
    )


VIETNAM_INFO_TOOL = {
    "name": "vietnam_info",
    "description": (
        "Tra cứu thông tin địa lý và khí hậu các tỉnh thành Việt Nam. "
        "Bao gồm: vùng miền, độ cao, khí hậu, mùa mưa/khô, thời điểm du lịch đẹp nhất. "
        "Ví dụ: 'Đà Lạt' | 'Sa Pa climate' | 'Nha Trang best_visit' | 'list'."
    ),
    "func": get_vietnam_info,
}


# =============================================================================
# DANH SÁCH TẤT CẢ TOOLS
# =============================================================================

TOOLS = {
    "calculator":     CALCULATOR_TOOL,
    "datetime":       DATETIME_TOOL,
    "unit_converter": UNIT_CONVERTER_TOOL,
    "weather":        WEATHER_TOOL,
    "statistics":     STATISTICS_TOOL,
    "percentage":     PERCENTAGE_TOOL,
    "vietnam_info":   VIETNAM_INFO_TOOL,
}

ALL_TOOLS = [
    WEATHER_TOOL,
    CALCULATOR_TOOL,
    STATISTICS_TOOL,
    PERCENTAGE_TOOL,
    UNIT_CONVERTER_TOOL,
    DATETIME_TOOL,
    VIETNAM_INFO_TOOL,
]
