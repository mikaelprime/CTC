"""Freno contra intentos de login por fuerza bruta (primera capa).

Contador en memoria por correo: tras varios intentos fallidos seguidos,
bloquea ese correo un rato. Cubre también correos que no existen, para que
la respuesta no revele cuáles son cuentas reales. La segunda capa es el
bloqueo guardado en la cuenta (users.locked_until, ver routes/auth.py), que
no se pierde cuando el backend se reinicia.
"""

import time

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 5 * 60  # ventana en la que cuentan los intentos fallidos
LOCKOUT_SECONDS = 5 * 60  # cuánto dura el bloqueo una vez alcanzado el máximo

_failed_attempts: dict[str, list[float]] = {}


def _prune(timestamps: list[float], now: float) -> list[float]:
    return [t for t in timestamps if now - t < WINDOW_SECONDS]


def seconds_until_retry(email: str) -> int:
    """0 si puede intentar login ya; si no, segundos que faltan para poder reintentar."""
    now = time.monotonic()
    attempts = _prune(_failed_attempts.get(email, []), now)
    _failed_attempts[email] = attempts
    if len(attempts) < MAX_ATTEMPTS:
        return 0
    elapsed_since_last_failure = now - attempts[-1]
    remaining = LOCKOUT_SECONDS - elapsed_since_last_failure
    return max(0, int(remaining))


def register_failure(email: str) -> None:
    now = time.monotonic()
    attempts = _prune(_failed_attempts.get(email, []), now)
    attempts.append(now)
    _failed_attempts[email] = attempts


def register_success(email: str) -> None:
    _failed_attempts.pop(email, None)
