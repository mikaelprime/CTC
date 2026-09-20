import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Configuración de URL de la Base de Datos
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./ctc_database.db"  # Cambia a tu URL de PostgreSQL de Docker si la usas
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ESTA ES LA FUNCIÓN QUE FALTABA O TENÍA OTRO NOMBRE:
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()