import re
from datetime import date

PHONE_PATTERN = re.compile(r"^\+7 \d{3} \d{3} \d{2}-\d{2}$")


def is_valid_phone(phone: str) -> bool:
    return bool(PHONE_PATTERN.match(phone.strip()))


def format_date_ru(d: date) -> str:
    months = (
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    )
    weekdays = (
        "понедельник",
        "вторник",
        "среда",
        "четверг",
        "пятница",
        "суббота",
        "воскресенье",
    )
    return f"{d.day} {months[d.month - 1]} {d.year} ({weekdays[d.weekday()]})"
