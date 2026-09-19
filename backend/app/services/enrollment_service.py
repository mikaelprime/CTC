from datetime import date, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.enrollment import Enrollment
# Asegúrate de importar tu modelo y esquema de Enrollment
# from app.models.enrollment import Enrollment 
# from app.schemas.enrollment import EnrollmentCreate

class EnrollmentService:

    # --- MÉTODOS CRUD QUE FALTABAN ---

    @staticmethod
    def get_all(db: Session) -> List[Any]:
        return db.query(Enrollment).all()

    @staticmethod
    def create(db: Session, enrollment: Any) -> Any:
        # Ajusta según los campos de tu esquema/modelo
        db_enrollment = Enrollment(**enrollment.dict())
        db.add(db_enrollment)
        db.commit()
        db.refresh(db_enrollment)
        return db_enrollment

    @staticmethod
    def get_by_id(db: Session, enrollment_id: int) -> Any:
        return db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()

    @staticmethod
    def delete(db: Session, enrollment_id: int) -> Any:
        db_enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
        if db_enrollment:
            db.delete(db_enrollment)
            db.commit()
        return db_enrollment

    # --- TUS MÉTODOS EXISTENTES DE CÁLCULO ---

    @staticmethod
    def calculate_next_payment_date(start_date: date) -> date:
        """
        Calcula la fecha exacta del próximo pago a 28 días
        a partir de la Fecha de Inicio de Clases.
        """
        return start_date + timedelta(days=28)

    @staticmethod
    def check_payment_status(last_payment_date: date, current_date: date = None) -> Dict[str, Any]:
        """
        Determina el estado del pago.
        """
        if current_date is None:
            current_date = date.today()

        due_date = last_payment_date + timedelta(days=28)
        days_remaining = (due_date - current_date).days

        if days_remaining < 0:
            return {
                "status": "Pendiente",
                "days_overdue": abs(days_remaining),
                "apply_late_fee": True,
                "late_fee_amount": 3.00,
                "message": "Pago vencido. Se requiere aplicar recargo de $3.00."
            }
        elif days_remaining <= 7:
            return {
                "status": "Próximo a Vencer",
                "days_remaining": days_remaining,
                "apply_late_fee": False,
                "late_fee_amount": 0.0,
                "message": f"Alerta: El pago vence en {days_remaining} días. Notificar al alumno."
            }
        else:
            return {
                "status": "Al día",
                "days_remaining": days_remaining,
                "apply_late_fee": False,
                "late_fee_amount": 0.0,
                "message": "Pago al día."
            }