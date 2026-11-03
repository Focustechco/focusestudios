from datetime import datetime, date
import pytz
from app.core.timezone import (
    to_utc,
    to_fortaleza,
    combine_date_slot,
    format_fortaleza,
    FORTALEZA_TZ,
    UTC_TZ
)


def test_timezone_conversion_fortaleza_utc():
    # 08:00 em America/Fortaleza (UTC-3) deve ser exatamente 11:00 UTC
    target_date = date(2026, 11, 3)
    utc_dt = combine_date_slot(target_date, "08:00")

    assert utc_dt.tzinfo == UTC_TZ
    assert utc_dt.hour == 11
    assert utc_dt.minute == 0

    # Conversão reversa
    fortaleza_dt = to_fortaleza(utc_dt)
    assert fortaleza_dt.tzinfo.zone == "America/Fortaleza"
    assert fortaleza_dt.hour == 8
    assert fortaleza_dt.minute == 0


def test_format_fortaleza():
    utc_dt = datetime(2026, 11, 3, 14, 30, tzinfo=UTC_TZ)
    # 14:30 UTC -> 11:30 em Fortaleza
    formatted = format_fortaleza(utc_dt, "%H:%M")
    assert formatted == "11:30"
