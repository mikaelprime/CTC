import logging
from html import escape

import httpx

from app.core import clock
from app.core.config import settings
from app.core.pricing import REGISTRATION_LABELS, TUITION_LABELS

logger = logging.getLogger(__name__)

MAILJET_API_URL = "https://api.mailjet.com/v3.1/send"


class EmailService:
    # Render (y varios hosts gratuitos) bloquean las conexiones SMTP
    # salientes en el plan free para evitar abuso de spam: un socket crudo a
    # smtp.gmail.com:587 falla con "Network is unreachable" sin importar que
    # las credenciales sean correctas. Mailjet expone una API HTTP normal
    # (POST sobre HTTPS/443), que ningún host bloquea, así que el envío pasa
    # por ahí en vez de por smtplib.
    API_KEY = (settings.MAILJET_API_KEY or "").strip()
    API_SECRET = (settings.MAILJET_API_SECRET or "").strip()
    SENDER_EMAIL = settings.EMAIL_FROM_ADDRESS
    SENDER_NAME = settings.EMAIL_FROM_NAME

    @staticmethod
    def recipients(student) -> list[str]:
        """Correo del estudiante y, si tiene, el de su responsable (PDF:
        datos del responsable). Sin repetir la misma dirección."""
        found = []
        for email in (student.email, student.responsible_email):
            if email and email.lower() not in {e.lower() for e in found}:
                found.append(email)
        return found

    @staticmethod
    def send_receipt(receipt, next_payment_date=None):
        """Comprobante (ticket) por correo (PDF, mejora recomendada)."""
        try:
            EmailService._send_receipt(receipt, next_payment_date)
        except Exception:
            logger.exception("No se pudo preparar el comprobante %s", getattr(receipt, "id", "?"))

    @staticmethod
    def _send_receipt(receipt, next_payment_date):
        enrollment = receipt.enrollment
        student = enrollment.student
        to = EmailService.recipients(student)
        if not to:
            logger.info("Estudiante #%s sin correo; no se envía el comprobante %s.", student.id, receipt.number)
            return
        lines = ""
        for payment in sorted(receipt.payments, key=lambda p: p.due_date):
            concept = (
                REGISTRATION_LABELS.get(enrollment.registration_type, "Matrícula")
                if payment.kind == "MATRICULA"
                else f"Colegiatura (vence {payment.due_date:%d/%m/%Y})"
            )
            lines += (
                f'<tr><td>{escape(concept)}</td>'
                f'<td style="text-align:right;font-weight:bold">${float(payment.amount):,.2f}</td></tr>'
            )
            if payment.surcharge and float(payment.surcharge) > 0:
                lines += (
                    '<tr><td>Recargo por mora</td>'
                    f'<td style="text-align:right;font-weight:bold">${float(payment.surcharge):,.2f}</td></tr>'
                )
        next_text = f"{next_payment_date:%d/%m/%Y}" if next_payment_date else "Colegiaturas completas"
        html = f"""
        <!doctype html>
        <html><body style="margin:0;background:#eef5f4;font-family:Arial;color:#183039">
          <div style="max-width:640px;margin:32px auto;background:#fff;border-radius:18px;overflow:hidden">
            <div style="padding:30px 34px;background:#123b43;color:#fff">
              <div style="font-size:12px;letter-spacing:2px;color:#76e0d1;font-weight:bold">CTC EL SALVADOR</div>
              <h1 style="margin:12px 0 6px">Pago recibido</h1>
              <p style="margin:0;color:#c7e4e1">Comprobante {receipt.number}</p>
            </div>
            <div style="padding:30px 34px">
              <p style="font-size:16px">Hola <strong>{escape(student.full_name)}</strong>,</p>
              <div style="padding:20px;background:#f2fbfa;border-left:5px solid #13a895;border-radius:8px">
                <div style="font-size:12px;color:#668087;text-transform:uppercase">Total pagado</div>
                <div style="font-size:30px;font-weight:bold;color:#123b43;margin-top:7px">${float(receipt.total):,.2f}</div>
                <div style="font-size:13px;color:#5d7379">{escape(enrollment.diploma.name)}</div>
              </div>
              <table style="width:100%;border-collapse:separate;border-spacing:0 10px;font-size:14px;margin-top:18px">
                {lines}
                <tr><td>Método de pago</td><td style="text-align:right;font-weight:bold">{escape(receipt.payment_type)}</td></tr>
                <tr><td>Efectivo recibido</td><td style="text-align:right;font-weight:bold">${float(receipt.cash_received):,.2f}</td></tr>
                <tr><td>Cambio</td><td style="text-align:right;font-weight:bold">${float(receipt.change):,.2f}</td></tr>
                <tr><td>Próximo pago</td><td style="text-align:right;font-weight:bold;color:#0b8f7e">{next_text}</td></tr>
              </table>
              <p style="color:#70858b;font-size:12px">Las colegiaturas se programan cada 28 días desde el inicio de clases.</p>
            </div>
            <div style="padding:18px 34px;background:#f5f8f8;color:#84979b;font-size:11px">Comprobante generado automáticamente por CTC Campus.</div>
          </div>
        </body></html>
        """
        EmailService._send_email(to, f"Comprobante de pago CTC {receipt.number}", html, True)

    @staticmethod
    def send_due_reminder(enrollment, due_date, amount):
        try:
            EmailService._send_due_reminder(enrollment, due_date, amount)
        except Exception:
            logger.exception(
                "No se pudo preparar el recordatorio de pago para la inscripción #%s",
                getattr(enrollment, "id", "?"),
            )

    @staticmethod
    def _send_due_reminder(enrollment, due_date, amount):
        student = enrollment.student
        to = EmailService.recipients(student)
        if not to:
            logger.info(
                "Estudiante #%s sin correo registrado; no se envía recordatorio de pago.",
                student.id,
            )
            return
        days_left = (due_date - clock.today()).days
        html = f"""
        <!doctype html>
        <html><body style="margin:0;background:#eef5f4;font-family:Arial;color:#183039">
          <div style="max-width:640px;margin:32px auto;background:#fff;border-radius:18px;overflow:hidden">
            <div style="padding:30px 34px;background:#123b43;color:#fff">
              <div style="font-size:12px;letter-spacing:2px;color:#76e0d1;font-weight:bold">CTC EL SALVADOR</div>
              <h1 style="margin:12px 0 6px">Tu colegiatura está por vencer</h1>
              <p style="margin:0;color:#c7e4e1">Faltan {days_left} día(s) para tu próximo pago.</p>
            </div>
            <div style="padding:30px 34px">
              <p style="font-size:16px">Hola <strong>{escape(student.full_name)}</strong>,</p>
              <div style="padding:20px;background:#fff8ec;border-left:5px solid #f59e0b;border-radius:8px">
                <div style="font-size:12px;color:#8a6d1f;text-transform:uppercase">Monto a pagar</div>
                <div style="font-size:30px;font-weight:bold;color:#123b43;margin-top:7px">${float(amount):,.2f}</div>
                <div style="font-size:13px;color:#5d7379">{escape(enrollment.diploma.name)}</div>
              </div>
              <table style="width:100%;border-collapse:separate;border-spacing:0 10px;font-size:14px;margin-top:18px">
                <tr><td>Fecha de vencimiento</td><td style="text-align:right;font-weight:bold;color:#b45309">{due_date:%d/%m/%Y}</td></tr>
              </table>
              <p style="color:#70858b;font-size:12px">Pasado el vencimiento se aplica un recargo por mora. Si ya realizaste el pago, ignora este mensaje.</p>
            </div>
            <div style="padding:18px 34px;background:#f5f8f8;color:#84979b;font-size:11px">Recordatorio generado automáticamente por CTC Campus.</div>
          </div>
        </body></html>
        """
        EmailService._send_email(to, f"Recordatorio de pago CTC #{enrollment.id}", html, True)

    @staticmethod
    def send_enrollment_confirmation(enrollment, monthly_amount, receipt=None):
        try:
            EmailService._send_enrollment_confirmation(enrollment, monthly_amount, receipt)
        except Exception:
            logger.exception(
                "No se pudo preparar la confirmación de inscripción #%s", getattr(enrollment, "id", "?")
            )

    @staticmethod
    def _send_enrollment_confirmation(enrollment, monthly_amount, receipt=None):
        student = enrollment.student
        to = EmailService.recipients(student)
        if not to:
            logger.info(
                "Estudiante #%s sin correo registrado; no se envía confirmación de la inscripción #%s.",
                student.id, enrollment.id,
            )
            return
        # PDF: el primer pago de colegiatura es el mismo día de inicio de
        # clases (antes se anunciaba inicio + 28 días, que es el segundo).
        first_payment = enrollment.start_date
        payment_rows = ""
        if receipt is not None:
            payment_rows += (
                f'<tr><td>Comprobante</td><td style="text-align:right;font-weight:bold">{receipt.number}</td></tr>'
                f'<tr><td>Monto de matrícula</td><td style="text-align:right;font-weight:bold">${float(receipt.total):,.2f}</td></tr>'
                f'<tr><td>Efectivo recibido</td><td style="text-align:right;font-weight:bold">${float(receipt.cash_received):,.2f}</td></tr>'
                f'<tr><td>Cambio</td><td style="text-align:right;font-weight:bold">${float(receipt.change):,.2f}</td></tr>'
            )
        html = f"""
        <!doctype html>
        <html><body style="margin:0;background:#eef5f4;font-family:Arial;color:#183039">
          <div style="max-width:640px;margin:32px auto;background:#fff;border-radius:18px;overflow:hidden">
            <div style="padding:30px 34px;background:#123b43;color:#fff">
              <div style="font-size:12px;letter-spacing:2px;color:#76e0d1;font-weight:bold">CTC EL SALVADOR</div>
              <h1 style="margin:12px 0 6px">Inscripción confirmada</h1>
              <p style="margin:0;color:#c7e4e1">Tu lugar en el programa ha sido registrado.</p>
            </div>
            <div style="padding:30px 34px">
              <p style="font-size:16px">Hola <strong>{escape(student.full_name)}</strong>,</p>
              <div style="padding:20px;background:#f2fbfa;border-left:5px solid #13a895;border-radius:8px">
                <div style="font-size:12px;color:#668087;text-transform:uppercase">Programa académico</div>
                <div style="font-size:21px;font-weight:bold;color:#123b43;margin-top:7px">{escape(enrollment.diploma.name)}</div>
              </div>
              <table style="width:100%;border-collapse:separate;border-spacing:0 10px;font-size:14px;margin-top:18px">
                <tr><td>Fecha de inscripción</td><td style="text-align:right;font-weight:bold">{enrollment.enrollment_date:%d/%m/%Y}</td></tr>
                <tr><td>Inicio de clases</td><td style="text-align:right;font-weight:bold">{enrollment.start_date:%d/%m/%Y}</td></tr>
                <tr><td>Horario</td><td style="text-align:right;font-weight:bold">{escape(enrollment.schedule.name)}</td></tr>
                <tr><td>Finalización estimada</td><td style="text-align:right;font-weight:bold">{enrollment.end_date:%d/%m/%Y}</td></tr>
                <tr><td>Matrícula</td><td style="text-align:right;font-weight:bold">{REGISTRATION_LABELS.get(enrollment.registration_type, enrollment.registration_type)}</td></tr>
                <tr><td>Plan de colegiatura</td><td style="text-align:right;font-weight:bold">{TUITION_LABELS.get(enrollment.tuition_plan, enrollment.tuition_plan)} (${float(monthly_amount):,.2f} cada 28 días)</td></tr>
                {payment_rows}
                <tr><td>Primer pago de colegiatura</td><td style="text-align:right;font-weight:bold;color:#0b8f7e">{first_payment:%d/%m/%Y}</td></tr>
              </table>
              <p style="color:#70858b;font-size:12px">Las colegiaturas se programan cada 28 días.</p>
            </div>
            <div style="padding:18px 34px;background:#f5f8f8;color:#84979b;font-size:11px">Comprobante generado automáticamente por CTC Campus.</div>
          </div>
        </body></html>
        """
        EmailService._send_email(to, f"Confirmación de inscripción CTC #{enrollment.id}", html, True)

    @staticmethod
    def _send_email(to_emails, subject, content, is_html=False):
        to_email = ", ".join(to_emails)
        if not EmailService.API_KEY or not EmailService.API_SECRET or not EmailService.SENDER_EMAIL:
            logger.warning(
                "Mailjet no configurado (falta MAILJET_API_KEY/MAILJET_API_SECRET/EMAIL_FROM_ADDRESS); "
                "correo a %s no enviado.",
                to_email,
            )
            return
        payload = {
            "Messages": [
                {
                    "From": {"Email": EmailService.SENDER_EMAIL, "Name": EmailService.SENDER_NAME},
                    "To": [{"Email": email} for email in to_emails],
                    "Subject": subject,
                    ("HTMLPart" if is_html else "TextPart"): content,
                }
            ]
        }
        try:
            response = httpx.post(
                MAILJET_API_URL,
                json=payload,
                auth=(EmailService.API_KEY, EmailService.API_SECRET),
                timeout=15,
            )
            response.raise_for_status()
            # Mailjet responde HTTP 200 incluso si un mensaje individual del
            # batch falló (remitente sin verificar, destinatario inválido,
            # etc.); el resultado real está en Messages[0].Status.
            result = response.json()
            message_status = (result.get("Messages") or [{}])[0].get("Status")
            if message_status != "success":
                logger.error("Mailjet no pudo enviar el correo a %s: %s", to_email, result)
                return
            logger.info("Correo '%s' enviado a %s", subject, to_email)
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Mailjet rechazó el correo a %s (HTTP %s): %s",
                to_email, exc.response.status_code, exc.response.text,
            )
        except Exception:
            logger.exception("No se pudo enviar el correo a %s", to_email)
