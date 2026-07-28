from fastapi import FastAPI
from app.database.base import Base
from app.database.database import engine
from app.models.role import Role
from app.models.user import User
from app.routes.auth import router as auth_router
from app.routes import auth
from app.routes import student
from app.routes import schedule
from app.routes import diploma

# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CTC Management System",
    version="1.0.0"
)

app.include_router(schedule.router)
app.include_router(auth_router)
app.include_router(auth.router)
app.include_router(student.router)
app.include_router(diploma.router)

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