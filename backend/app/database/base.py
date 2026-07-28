from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Registra todos los roles
import app.models