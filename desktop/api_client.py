"""HTTP client for the CTC FastAPI backend (runs in Docker, exposed on localhost:8000).

Unlike the old Streamlit frontend, this app has no per-request session object,
so the JWT is held on a module-level singleton for the lifetime of the process.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

import requests


def _load_api_url() -> str:
    configured = os.environ.get("API_BASE_URL")
    if configured:
        return configured.strip().rstrip("/")

    config_path = Path(__file__).with_name("config.json")
    if config_path.exists():
        try:
            value = json.loads(config_path.read_text(encoding="utf-8")).get("api_base_url")
            if value:
                return str(value).strip().rstrip("/")
        except (OSError, json.JSONDecodeError):
            pass

    return "https://ctc-backend-j3id.onrender.com"


API_BASE_URL = _load_api_url()
_TIMEOUT = 20
# El backend gratuito de Render se "duerme" tras un rato sin tráfico y puede
# tardar hasta un minuto en despertar en la primera petición.
_LOGIN_TIMEOUT = 60


class ApiError(Exception):
    """Raised for any failed request to the backend (HTTP or network error)."""


class ApiClient:
    def __init__(self):
        self.token: Optional[str] = None
        self.user_email: Optional[str] = None
        self.user_role: Optional[str] = None
        self.user_id: Optional[int] = None

    def is_authenticated(self) -> bool:
        return bool(self.token)

    def ping(self, timeout: int = _LOGIN_TIMEOUT) -> bool:
        """Verifica que el backend responda. Usado por la pantalla de carga
        para saber si hay que esperar a que Render despierte el servicio."""
        try:
            resp = requests.get(f"{API_BASE_URL}/api/health", timeout=timeout)
            return resp.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def logout(self) -> None:
        self.token = None
        self.user_email = None
        self.user_role = None
        self.user_id = None

    def login(self, email: str, password: str) -> None:
        try:
            resp = requests.post(
                f"{API_BASE_URL}/auth/login",
                json={"email": email, "password": password},
                timeout=_LOGIN_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            raise ApiError(f"No se pudo contactar al backend ({API_BASE_URL}): {exc}") from exc

        if resp.status_code != 200:
            raise ApiError(self._detail(resp) or "Correo o contraseña incorrectos.")

        data = resp.json()
        self.token = data["access_token"]
        self.user_email = data.get("email", email)
        self.user_role = data.get("role")
        self.user_id = data.get("user_id")

    @staticmethod
    def _detail(resp: requests.Response) -> Optional[str]:
        try:
            detail = resp.json().get("detail")
        except ValueError:
            return resp.text or None
        # Un backend sin el manejador de validación en español devuelve una
        # lista de errores; se muestra como líneas legibles, no como repr().
        if isinstance(detail, list):
            return "\n".join(
                f"{item.get('loc', ['', ''])[-1]}: {item.get('msg', '')}" if isinstance(item, dict) else str(item)
                for item in detail
            )
        return detail

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, method: str, path: str, **kwargs: Any):
        try:
            resp = requests.request(
                method, f"{API_BASE_URL}{path}", headers=self._headers(), timeout=_TIMEOUT, **kwargs
            )
        except requests.exceptions.RequestException as exc:
            raise ApiError(f"No se pudo contactar al backend ({API_BASE_URL}): {exc}") from exc

        if resp.status_code == 401:
            self.logout()
            raise ApiError("Tu sesión expiró. Vuelve a iniciar sesión.")

        if resp.status_code >= 400:
            raise ApiError(self._detail(resp) or f"Error {resp.status_code} en {path}")

        return resp.json() if resp.content else None

    def get(self, path: str):
        return self._request("GET", path)

    def post(self, path: str, json: Optional[dict] = None):
        return self._request("POST", path, json=json)

    def put(self, path: str, json: Optional[dict] = None):
        return self._request("PUT", path, json=json)

    def delete(self, path: str):
        return self._request("DELETE", path)


api = ApiClient()
