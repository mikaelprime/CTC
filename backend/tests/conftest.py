"""Las pruebas NUNCA deben tocar la base real: antes usaban el DATABASE_URL
del .env (Supabase de producción) y dejaban estudiantes y pagos de prueba.

Ahora usan TEST_DATABASE_URL (CI lo apunta a su Postgres desechable) o, por
defecto, un SQLite nuevo en cada corrida. Esto tiene que ejecutarse antes de
importar la app: database.py lee DATABASE_URL al importarse, y load_dotenv
no pisa una variable que ya existe.
"""

import os
import tempfile
from pathlib import Path
from uuid import uuid4

_default_db = Path(tempfile.gettempdir()) / "ctc_pytest.db"
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_default_db.as_posix()}")
if "supabase" in TEST_DATABASE_URL or "render.com" in TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL apunta a una base real; las pruebas se niegan a correr ahí.")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
# Sin correos reales ni hilo de recordatorios corriendo en paralelo.
os.environ["MAILJET_API_KEY"] = ""
os.environ["MAILJET_API_SECRET"] = ""
os.environ["REMINDER_SCHEDULER"] = "off"
IS_SQLITE = TEST_DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    _default_db.unlink(missing_ok=True)
    import app.models  # noqa: F401  (registra todos los modelos en Base)
    import seed_data

    seed_data.populate_initial_data()  # crea las tablas y los usuarios base

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)

# DUI válidos (dígito verificador correcto) para datos de prueba.
VALID_DUI = "00016297-5"


def student_payload(**overrides) -> dict:
    """Estudiante adulto con todos los datos obligatorios válidos."""
    payload = {
        "full_name": "Estudiante Prueba",
        "birth_date": "2000-05-10",
        "address": "Colonia Escalón, San Salvador",
        "email": f"estudiante-{uuid4().hex[:8]}@ctc.edu.sv",
        "contact_phone": "7777-8888",
        "schooling": "Bachillerato",
    }
    payload.update(overrides)
    return payload
