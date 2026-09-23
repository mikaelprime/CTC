import hmac
import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

# Sin esto, el logging de Python queda sin configurar: el "handler de
# último recurso" que usa por defecto solo emite WARNING y ERROR, así que
# cualquier logger.info() de la app (confirmaciones de envío de correo,
# estudiantes sin email, etc.) se descarta en silencio y nunca aparece en
# los logs de Render, aunque el código sí se haya ejecutado. force=True
# asegura que esta configuración se aplique aunque algo (uvicorn, otro
# import) ya le haya puesto un handler al logger raíz antes.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    force=True,
)
from app.database.base import Base
from app.database.database import SessionLocal, engine
from app.core.validation_errors import humanize
from app.models.role import Role
from app.models.user import User
from app.models.cash_register import CashRegister
from app.routes.auth import router as auth_router
from app.routes import auth
from app.routes import student
from app.routes import schedule
from app.routes import diploma
from app.routes import payment
from app.routes.enrollment import router as enrollment_router
from app.routes import cashier
from app.routes import config
from app.routes import users
from app.routes import reports

# Base.metadata.create_all(bind=engine)

logger = logging.getLogger(__name__)

# Cada cuánto revisa el backend, por su cuenta, los vencimientos próximos
# (aviso 7 días antes y estado PENDIENTE). Antes solo pasaba al iniciar
# sesión: si nadie entraba en varios días, nadie recibía su recordatorio.
_REMINDER_INTERVAL_SECONDS = int(os.getenv("REMINDER_INTERVAL_SECONDS", "3600"))


def run_due_reminders() -> int:
    from app.services.payment_service import PaymentService

    db = SessionLocal()
    try:
        return PaymentService.send_due_reminders(db)
    finally:
        db.close()


def _reminder_loop(stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            sent = run_due_reminders()
            if sent:
                logger.info("Recordatorios de pago enviados: %s", sent)
        except Exception:
            logger.exception("Falló la revisión periódica de recordatorios de pago")
        stop.wait(_REMINDER_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # En las pruebas se desactiva (REMINDER_SCHEDULER=off) para que no corra
    # en paralelo con ellas.
    stop = threading.Event()
    if os.getenv("REMINDER_SCHEDULER", "on").lower() != "off":
        threading.Thread(target=_reminder_loop, args=(stop,), daemon=True, name="reminders").start()
    yield
    stop.set()


app = FastAPI(
    title="CTC Management System",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(student.router)
app.include_router(diploma.router)
app.include_router(schedule.router)
app.include_router(enrollment_router)
app.include_router(payment.router)
app.include_router(cashier.router)
app.include_router(config.router)
app.include_router(users.router)
app.include_router(reports.router)


@app.exception_handler(IntegrityError)
def handle_integrity_error(request: Request, exc: IntegrityError):
    """Red de seguridad: si algún endpoint deja pasar un borrado/creación que
    viola una restricción de la base de datos (por ejemplo, borrar un
    registro que todavía tiene datos dependientes) sin validarlo antes, esto
    evita que la persona vea un "Internal Server Error" sin explicación."""
    return JSONResponse(
        status_code=409,
        content={"detail": "La operación no se pudo completar porque hay datos relacionados que dependen de este registro."},
    )


@app.exception_handler(RequestValidationError)
def handle_validation_error(request: Request, exc: RequestValidationError):
    """Errores de validación en español y en una sola cadena legible (el
    formato por defecto es una lista en inglés que el escritorio mostraba
    tal cual)."""
    return JSONResponse(status_code=422, content={"detail": humanize(exc.errors())})


@app.post("/api/cron/reminders")
def cron_reminders(x_cron_secret: str = Header(default="")):
    """Para un cron externo gratuito (p. ej. cron-job.org, una vez al día):
    el plan gratuito de Render duerme el servicio sin tráfico y el hilo de
    recordatorios no corre mientras duerme. Esta llamada lo despierta y
    procesa los avisos. Requiere CRON_SECRET configurado en el servidor."""
    expected = os.getenv("CRON_SECRET", "")
    if not expected or not hmac.compare_digest(x_cron_secret, expected):
        raise HTTPException(status_code=403, detail="No autorizado")
    return {"reminders_sent": run_due_reminders()}


@app.get("/")
def root():
    return {
        "message": "Bienvenido al CTC Management System"
    }

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "CTC Management System",
        "version": "1.0.0"
    }