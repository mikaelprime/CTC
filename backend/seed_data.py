import sys
import os
from datetime import date, time

# Permitir que reconozca los módulos dentro de backend/app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.database import SessionLocal, engine
from app.database.base import Base
from app.models.diploma import Diploma
from app.models.schedule import Schedule
from app.models.student import Student
from app.models.enrollment import Enrollment
from app.models.role import Role
from app.models.user import User
from app.auth.security import hash_password

def populate_initial_data():
    # Crea las tablas si aún no existen localmente
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    print("Iniciando carga de datos requeridos por CTC El Salvador...")

    # 1. Cargar Diplomados Oficiales
    diplomas_data = [
        {"name": "Secretariado en Informática", "duration_months": 6, "registration_fee": 20.00, "monthly_fee": 25.00},
        {"name": "Operador en Sistemas Informáticos", "duration_months": 6, "registration_fee": 20.00, "monthly_fee": 25.00},
        {"name": "Marketing Digital", "duration_months": 4, "registration_fee": 20.00, "monthly_fee": 25.00},
        {"name": "Soporte Técnico", "duration_months": 5, "registration_fee": 20.00, "monthly_fee": 25.00},
    ]

    for dip in diplomas_data:
        exists = db.query(Diploma).filter(Diploma.name == dip["name"]).first()
        if not exists:
            db.add(Diploma(**dip))

    # 2. Cargar Horarios de Fin de Semana (Sábado / Domingo)
    schedules_data = [
        {"name": "Sábado Mañana", "start_time": time(8, 0), "end_time": time(12, 0), "active": True},
        {"name": "Sábado Tarde", "start_time": time(13, 0), "end_time": time(17, 0), "active": True},
        {"name": "Domingo Mañana", "start_time": time(8, 0), "end_time": time(12, 0), "active": True},
    ]

    for sch in schedules_data:
        exists = db.query(Schedule).filter(Schedule.name == sch["name"]).first()
        if not exists:
            db.add(Schedule(**sch))

    db.commit()

    # Roles y cuentas iniciales para que el sistema pueda iniciar sesión.
    admin_role = db.query(Role).filter(Role.name.ilike("admin%")) .first()
    if admin_role is None:
        admin_role = Role(name="ADMIN")
        db.add(admin_role)
    cashier_role = db.query(Role).filter(Role.name.ilike("cajero%")) .first()
    if cashier_role is None:
        cashier_role = Role(name="CAJERO")
        db.add(cashier_role)
    db.commit()

    if db.query(User).filter(User.email == "admin@ctc.edu.sv").first() is None:
        db.add(User(
            full_name="Administrador CTC",
            email="admin@ctc.edu.sv",
            password=hash_password("123456"),
            birth_date=date(1990, 1, 1),
            role_id=admin_role.id,
        ))
    if db.query(User).filter(User.email == "cajero@ctc.edu.sv").first() is None:
        db.add(User(
            full_name="Cajero CTC",
            email="cajero@ctc.edu.sv",
            password=hash_password("123456"),
            birth_date=date(1995, 1, 1),
            role_id=cashier_role.id,
        ))
    db.commit()
    db.close()
    print("¡Base de datos cargada con éxito localmente!")

if __name__ == "__main__":
    populate_initial_data()