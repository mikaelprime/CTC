"""Fecha y hora oficiales del sistema: las de El Salvador (UTC-6).

El servidor (Render) corre en UTC. Con date.today() / datetime.now(), después
de las 6:00 p. m. hora local el sistema ya creía que era "mañana": el cobro
quedaba con la fecha del día siguiente, la mora se aplicaba un día antes y
un cierre de caja nocturno caía en otro día. Todo el backend pide la fecha
aquí en vez de al reloj del servidor.

El Salvador no usa horario de verano desde 1988, así que un desfase fijo es
exacto y no depende de la base de datos de zonas horarias del sistema
operativo (tzdata no viene instalado en Windows).
"""

from datetime import date, datetime, time, timedelta, timezone

LOCAL_TZ = timezone(timedelta(hours=-6), "America/El_Salvador")


def now() -> datetime:
    """Fecha y hora local de El Salvador (con zona horaria)."""
    return datetime.now(LOCAL_TZ)


def today() -> date:
    """Fecha local de El Salvador."""
    return now().date()


def local_day_bounds_utc(start: date, end: date) -> tuple[datetime, datetime]:
    """Instantes UTC (sin tzinfo, como los guarda la BD) que cubren desde el
    inicio del día local `start` hasta el inicio del día local siguiente a
    `end`. Sirve para filtrar columnas DateTime guardadas en UTC por días
    de calendario de El Salvador."""
    begin = datetime.combine(start, time.min, LOCAL_TZ).astimezone(timezone.utc)
    finish = datetime.combine(end + timedelta(days=1), time.min, LOCAL_TZ).astimezone(timezone.utc)
    return begin.replace(tzinfo=None), finish.replace(tzinfo=None)


def to_local(value: datetime | None) -> datetime | None:
    """Convierte un instante de la BD (UTC, con o sin tzinfo) a hora local."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(LOCAL_TZ)
