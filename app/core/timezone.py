from datetime import datetime, date, time
from typing import Optional
import pytz
from app.config import settings

FORTALEZA_TZ = pytz.timezone(settings.TIMEZONE)
UTC_TZ = pytz.UTC


def get_current_time_fortaleza() -> datetime:
    """Retorna o datetime atual no fuso America/Fortaleza com tzinfo."""
    return datetime.now(FORTALEZA_TZ)


def get_current_time_utc() -> datetime:
    """Retorna o datetime atual em UTC com tzinfo."""
    return datetime.now(UTC_TZ)


def to_utc(dt: datetime) -> datetime:
    """Converte um datetime (seja ingênuo armazenado em UTC, ou com tz) para UTC timezone-aware."""
    if dt.tzinfo is None:
        dt = UTC_TZ.localize(dt)
    return dt.astimezone(UTC_TZ)


def to_fortaleza(dt: datetime) -> datetime:
    """Converte um datetime (UTC ou outro) para America/Fortaleza."""
    if dt.tzinfo is None:
        dt = UTC_TZ.localize(dt)
    return dt.astimezone(FORTALEZA_TZ)


def format_fortaleza(dt: Optional[datetime], fmt: str = "%d/%m/%Y %H:%M") -> str:
    """Formata um datetime no fuso de Fortaleza para exibição humana na interface."""
    if not dt:
        return "-"
    return to_fortaleza(dt).strftime(fmt)


def combine_date_slot(target_date: date, slot_str: str) -> datetime:
    """
    Combina uma data (date) e uma string de horário 'HH:MM' no fuso de Fortaleza,
    retornando o datetime em UTC para persistência confiável no banco.
    """
    parts = slot_str.split(":")
    hour, minute = int(parts[0]), int(parts[1])
    naive_dt = datetime.combine(target_date, time(hour=hour, minute=minute))
    fortaleza_dt = FORTALEZA_TZ.localize(naive_dt)
    return to_utc(fortaleza_dt)
