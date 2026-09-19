import smtplib
import ssl
from email.message import EmailMessage
from app.core.config import settings

class EmailService:

    @staticmethod
    def send_email(to_email: str, subject: str, body: str):
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = to_email
        message.set_content(body)

        context = ssl.create_default_context()

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)

    @staticmethod
    def send_payment_confirmation(payment):
        student = payment.enrollment.student
        diploma = payment.enrollment.diploma

        if not student or not student.email:
            return

        subject = "Confirmación de pago - CTC"
        body = (
            f"Hola {student.full_name},\n\n"
            f"Se ha registrado el cobro de tu cuota del diplomado "
            f"{diploma.name} correspondiente al "
            f"{payment.due_date.strftime('%d/%m/%Y')}.\n\n"
            f"Monto cobrado: ${payment.total}\n\n"
            f"Gracias por tu pago.\n"
            f"CTC"
        )

        try:
            EmailService.send_email(student.email, subject, body)
        except Exception as exc:
            print(f"No se pudo enviar el correo de pago a {student.email}: {exc}")
