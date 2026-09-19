from datetime import date, timedelta
from typing import Dict, Any

class EnrollmentService:

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
        Determina el estado del pago:
        - Próximo a vencer (si faltan 7 días o menos)
        - Vencido / Pendiente (si supera los 28 días)
        - Aplica recargo de $3.00 si está superado los 28 días.
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
                "late_fee_amount": 3.00, # Recargo de $3.00 por mora
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