import logging
from datetime import timedelta

import httpx

from app.core.config import settings

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
    def send_payment_confirmation(payment, next_payment_date=None, months_paid=1):
        try:
            EmailService._send_payment_confirmation(payment, next_payment_date, months_paid)
        except Exception:
            logger.exception(
                "No se pudo preparar el comprobante de pago #%s", getattr(payment, "id", "?")
            )

    @staticmethod
    def _send_payment_confirmation(payment, next_payment_date, months_paid):
        student = payment.enrollment.student
        if not student.email:
            logger.info(
                "Estudiante #%s sin correo registrado; no se envía comprobante de pago #%s.",
                student.id, payment.id,
            )
            return
        next_date = next_payment_date or (payment.due_date + timedelta(days=28))
        html = f"""
        <!doctype html>
        <html><body style="margin:0;background:#eef5f4;font-family:Arial;color:#183039">
          <div style="max-width:640px;margin:32px auto;background:#fff;border-radius:18px;overflow:hidden">
            <div style="padding:30px 34px;background:#123b43;color:#fff">
              <div style="font-size:12px;letter-spacing:2px;color:#76e0d1;font-weight:bold">CTC EL SALVADOR</div>
              <h1 style="margin:12px 0 6px">Pago recibido</h1>
              <p style="margin:0;color:#c7e4e1">Tu comprobante de pago está listo.</p>
            </div>
            <div style="padding:30px 34px">
              <p style="font-size:16px">Hola <strong>{student.full_name}</strong>,</p>
              <div style="padding:20px;background:#f2fbfa;border-left:5px solid #13a895;border-radius:8px">
                <div style="font-size:12px;color:#668087;text-transform:uppercase">Total pagado</div>
                <div style="font-size:30px;font-weight:bold;color:#123b43;margin-top:7px">${float(payment.total):,.2f}</div>
                <div style="font-size:13px;color:#5d7379">{months_paid} mes(es) cubierto(s)</div>
              </div>
              <table style="width:100%;border-collapse:separate;border-spacing:0 10px;font-size:14px;margin-top:18px">
                <tr><td>Fecha de pago</td><td style="text-align:right;font-weight:bold">{payment.payment_date}</td></tr>
                <tr><td>Vencimiento cubierto</td><td style="text-align:right;font-weight:bold">{payment.due_date}</td></tr>
                <tr><td>Próximo pago</td><td style="text-align:right;font-weight:bold;color:#0b8f7e">{next_date}</td></tr>
              </table>
              <p style="color:#70858b;font-size:12px">Las colegiaturas se programan cada 28 días.</p>
            </div>
            <div style="padding:18px 34px;background:#f5f8f8;color:#84979b;font-size:11px">Comprobante generado automáticamente por CTC Campus.</div>
          </div>
        </body></html>
        """
        EmailService._send_email(student.email, f"Comprobante de pago CTC #{payment.id}", html, True)

    @staticmethod
    def send_enrollment_confirmation(enrollment):
        try:
            EmailService._send_enrollment_confirmation(enrollment)
        except Exception:
            logger.exception(
                "No se pudo preparar la confirmación de inscripción #%s", getattr(enrollment, "id", "?")
            )

    @staticmethod
    def _send_enrollment_confirmation(enrollment):
        student = enrollment.student
        if not student.email:
            logger.info(
                "Estudiante #%s sin correo registrado; no se envía confirmación de la inscripción #%s.",
                student.id, enrollment.id,
            )
            return
        next_payment = enrollment.start_date + timedelta(days=28)
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
              <p style="font-size:16px">Hola <strong>{student.full_name}</strong>,</p>
              <div style="padding:20px;background:#f2fbfa;border-left:5px solid #13a895;border-radius:8px">
                <div style="font-size:12px;color:#668087;text-transform:uppercase">Programa académico</div>
                <div style="font-size:21px;font-weight:bold;color:#123b43;margin-top:7px">{enrollment.diploma.name}</div>
              </div>
              <table style="width:100%;border-collapse:separate;border-spacing:0 10px;font-size:14px;margin-top:18px">
                <tr><td>Fecha de inscripción</td><td style="text-align:right;font-weight:bold">{enrollment.enrollment_date}</td></tr>
                <tr><td>Inicio de clases</td><td style="text-align:right;font-weight:bold">{enrollment.start_date}</td></tr>
                <tr><td>Finalización estimada</td><td style="text-align:right;font-weight:bold">{enrollment.end_date}</td></tr>
                <tr><td>Próximo pago</td><td style="text-align:right;font-weight:bold;color:#0b8f7e">{next_payment}</td></tr>
              </table>
              <p style="color:#70858b;font-size:12px">Las colegiaturas se programan cada 28 días.</p>
            </div>
            <div style="padding:18px 34px;background:#f5f8f8;color:#84979b;font-size:11px">Comprobante generado automáticamente por CTC Campus.</div>
          </div>
        </body></html>
        """
        EmailService._send_email(student.email, f"Confirmación de inscripción CTC #{enrollment.id}", html, True)

    @staticmethod
    def _send_email(to_email, subject, content, is_html=False):
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
                    "To": [{"Email": to_email}],
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
