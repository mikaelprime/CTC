import logging
import smtplib
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    SMTP_SERVER = settings.SMTP_HOST
    SMTP_PORT = settings.SMTP_PORT
    SMTP_USER = settings.SMTP_USER
    SENDER_EMAIL = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    # Las contraseñas de aplicación de Gmail se muestran con espacios
    # ("xxxx xxxx xxxx xxxx") para que se lean mejor; si alguien las copia tal
    # cual a la variable de entorno, .strip() evita que ese detalle de
    # presentación rompa el login SMTP.
    SENDER_PASSWORD = (settings.SMTP_PASSWORD or "").strip()

    @staticmethod
    def send_payment_confirmation(payment, next_payment_date=None, months_paid=1):
        student = payment.enrollment.student
        if not student.email:
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
        student = enrollment.student
        if not student.email:
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
        # Credenciales de autenticación SMTP: pueden ser una cuenta distinta
        # a la que aparece como remitente (SMTP_FROM_EMAIL), así que se
        # inicia sesión con SMTP_USER, no con SENDER_EMAIL.
        login_user = EmailService.SMTP_USER or EmailService.SENDER_EMAIL
        if not login_user or not EmailService.SENDER_PASSWORD:
            logger.warning(
                "SMTP no configurado (faltan SMTP_USER/SMTP_PASSWORD); correo a %s no enviado.",
                to_email,
            )
            return
        try:
            message = MIMEMultipart()
            message["From"] = EmailService.SENDER_EMAIL
            message["To"] = to_email
            message["Subject"] = subject
            message.attach(MIMEText(content, "html" if is_html else "plain"))
            with smtplib.SMTP(EmailService.SMTP_SERVER, EmailService.SMTP_PORT, timeout=15) as smtp:
                smtp.starttls()
                smtp.login(login_user, EmailService.SENDER_PASSWORD)
                smtp.send_message(message)
            logger.info("Correo '%s' enviado a %s", subject, to_email)
        except smtplib.SMTPAuthenticationError:
            logger.exception(
                "Autenticación SMTP rechazada para %s. Revisa SMTP_USER/SMTP_PASSWORD "
                "(para Gmail debe ser una contraseña de aplicación, no la del correo).",
                login_user,
            )
        except Exception:
            logger.exception("No se pudo enviar el correo a %s", to_email)
