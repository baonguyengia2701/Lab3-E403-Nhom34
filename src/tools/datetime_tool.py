from datetime import datetime, date, timedelta


def query_datetime(command: str) -> str:
    """
    Answer date/time queries.

    Supported commands:
        - "today"              → returns today's date
        - "now"                → returns current date and time
        - "days_until:YYYY-MM-DD" → days remaining until the given date
        - "days_since:YYYY-MM-DD" → days elapsed since the given date
        - "weekday"            → returns today's day of the week

    Args:
        command: A string command as described above.

    Returns:
        A human-readable string with the answer.
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
        "Answers date and time queries. "
        "Supported commands: 'today' (current date), 'now' (date and time), "
        "'weekday' (day of week), 'days_until:YYYY-MM-DD' (countdown), "
        "'days_since:YYYY-MM-DD' (elapsed days). "
        "Example: datetime(days_until:2027-01-01)"
    ),
    "func": query_datetime,
}
