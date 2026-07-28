from app.database.session import SessionLocal
from app.models.role import Role
from app.models.user import User
from app.auth.security import hash_password

db = SessionLocal()

# -------------------------
# CREAR ROLES
# -------------------------

roles = {
    "Administrador",
    "Gerente",
    "Cajero"
}

for role_name in roles:

    role = db.query(Role).filter(
        Role.name == role_name
    ).first()

    if not role:
        db.add(Role(name=role_name))

    db.commit()

# -------------------------
# CREAR ADMINISTRADOR
# -------------------------

admin = db.query(User).filter(
    User.email == "admin@ctc.edu.sv"
).first()

if not admin:

    admin_role = db.query(Role).filter(
        Role.name == "Administrador"
    ).first()

    admin = User(
        full_name="Administrador General",
        email="admin@ctc.edu.sv",
        password=hash_password("123456"),
        birth_date="2000-01-01",
        role_id=admin_role.id,
        is_active=True
    )

    db.add(admin)
    db.commit()

print("Seed ejecutado correctamente.")