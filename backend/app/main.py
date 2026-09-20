from fastapi import FastAPI
from app.database.base import Base
from app.database.database import engine
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

app = FastAPI(
    title="CTC Management System",
    version="1.0.0"
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