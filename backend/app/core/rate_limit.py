"""Freno simple contra intentos de login por fuerza bruta.

No hay Redis ni infraestructura extra en este proyecto (un solo proceso de
backend), así que un contador en memoria por correo es suficiente: tras
varios intentos fallidos seguidos, bloquea ese correo un rato en vez de
dejar reintentar sin límite.
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
