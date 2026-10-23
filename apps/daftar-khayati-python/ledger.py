"""Small, testable data layer for the native Daftar Khayati Android app."""
from __future__ import annotations
from datetime import date
from typing import Any

def default_state() -> dict[str, Any]:
    templates = [
        ("shirt", "پیراهن", "👔", "تکمیلی"),
        ("pants", "شلوار", "👖", "تکمیلی"),
        ("coat", "مانتو", "🧥", "تکمیلی"),
        ("dress", "لباس و پیراهن", "👗", "تکمیلی"),
        ("skirt", "دامن", "👗", "تکمیلی"),
        ("zipper", "زیپ", "🧵", "زنجیره‌ای"),
        ("button", "دکمه", "🔘", "زنجیره‌ای"),
        ("seam", "دوخت درز", "🪡", "زنجیره‌ای"),
    ]
    cards = [
        {"id": key, "name": name, "emoji": emoji, "type": work_type,
         "price": 0, "button_count": 0, "button_cost": 0, "description": ""}
        for key, name, emoji, work_type in templates
    ]
    return {"cards": cards, "entries": [], "receipts": [],
            "settings": {"name": "", "work_mode": "هر دو", "last_card_id": "shirt"},
            "schema_version": 1}

def to_number(value: Any, default: int = 0) -> int:
    try:
        return max(0, int(float(str(value or "0").replace(",", "").strip())))
    except (TypeError, ValueError, OverflowError):
        return default

def make_entry(*, card: dict[str, Any], qty: Any, price: Any, entry_date: str,
               color: str = "", size: str = "", note: str = "",
               button_cost: Any = 0, charge_buttons: bool = True,
               external_cost: Any = 0) -> dict[str, Any]:
    quantity, wage = to_number(qty), to_number(price)
    if quantity < 1:
        raise ValueError("تعداد باید حداقل یک باشد.")
    if wage < 1:
        raise ValueError("دستمزد هر عدد باید بیشتر از صفر باشد.")
    try:
        date.fromisoformat(entry_date)
    except (TypeError, ValueError):
        raise ValueError("تاریخ را به شکل سال-ماه-روز وارد کن.") from None
    raw_button_cost = to_number(button_cost)
    buttons = raw_button_cost if charge_buttons else 0
    outside = to_number(external_cost)
    gross = quantity * wage
    return {
        "id": f"{entry_date}-{card['id']}-{quantity}-{gross}-{raw_button_cost}",
        "date": entry_date, "card_id": card["id"], "card_name": card["name"],
        "emoji": card.get("emoji", "🧵"), "type": card.get("type", "تکمیلی"),
        "qty": quantity, "price": wage, "gross": gross,
        "button_cost": buttons, "external_cost": outside,
        "net": gross - buttons - outside, "color": color.strip(),
        "size": size.strip(), "note": note.strip(),
    }

def summarize(entries: list[dict[str, Any]], receipts: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "qty": sum(to_number(x.get("qty")) for x in entries),
        "gross": sum(to_number(x.get("gross", to_number(x.get("qty")) * to_number(x.get("price")))) for x in entries),
        "buttons": sum(to_number(x.get("button_cost")) for x in entries),
        "external": sum(to_number(x.get("external_cost")) for x in entries),
        "net": sum(int(x.get("net", 0)) for x in entries),
        "received": sum(to_number(x.get("amount")) for x in receipts),
    }

def today_iso() -> str:
    return date.today().isoformat()
