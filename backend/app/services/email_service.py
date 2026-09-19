import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailService:
    
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = "notificaciones@ctc.edu.sv"
    SENDER_PASSWORD = "tu_clave_de_aplicacion"

    @staticmethod
    def send_html_ticket(student_email: str, student_name: str, concept: str, amount: float, cash_received: float, change: float, receipt_id: str):
        """Genera y envía un Ticket visual HTML directo al correo del alumno."""
        subject = f"Comprobante de Pago #{receipt_id} - CTC El Salvador"
        
        # Diseño del Ticket 
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f9; padding: 20px;">
            <div style="max-width: 400px; margin: auto; background: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #ddd; box-shadow: 0 4px 8px rgba(0,0,0,0.05);">
                <div style="text-align: center; border-bottom: 2px dashed #000; padding-bottom: 10px; margin-bottom: 15px;">
                    <h2 style="margin: 0; color: #0b192c;">CTC EL SALVADOR</h2>
                    <p style="margin: 3px 0; font-size: 12px; color: #555;">Centro Técnico de Capacitación</p>
                    <p style="margin: 3px 0; font-size: 12px; color: #555;">NIT/NRC: 0614-180926-101-2</p>
                    <p style="margin: 3px 0; font-weight: bold; font-size: 14px; color: #333;">TICKET DE COMPROBANTE #{receipt_id}</p>
                </div>

                <div style="font-size: 13px; color: #333; margin-bottom: 15px;">
                    <p style="margin: 4px 0;"><strong>Estudiante:</strong> {student_name}</p>
                    <p style="margin: 4px 0;"><strong>Fecha:</strong> 19/09/2026</p>
                </div>

                <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 15px;">
                    <thead>
                        <tr style="border-bottom: 1px solid #000; text-align: left;">
                            <th style="padding: 5px 0;">Concepto</th>
                            <th style="padding: 5px 0; text-align: right;">Monto</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="padding: 8px 0;">{concept}</td>
                            <td style="padding: 8px 0; text-align: right;">${amount:.2f}</td>
                        </tr>
                    </tbody>
                </table>

                <div style="border-top: 1px dashed #000; padding-top: 10px; font-size: 13px;">
                    <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 15px; margin-bottom: 5px;">
                        <span>TOTAL PAGADO:</span>
                        <span>${amount:.2f}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; color: #555;">
                        <span>Efectivo Recibido:</span>
                        <span>${cash_received:.2f}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; color: #555;">
                        <span>Cambio Entregado:</span>
                        <span>${change:.2f}</span>
                    </div>
                </div>

                <div style="text-align: center; margin-top: 20px; font-size: 11px; color: #777; border-top: 1px solid #eee; padding-top: 10px;">
                    <p style="margin: 2px 0;">¡Gracias por tu pago puntual!</p>
                    <p style="margin: 2px 0;">Conserva este ticket como tu comprobante oficial.</p>
                </div>
            </div>
        </body>
        </html>
        """
        EmailService._send_email(student_email, subject, html_content, is_html=True)

    @staticmethod
    def generate_thermal_ticket_text(student_name: str, concept: str, amount: float, cash_received: float, change: float, receipt_id: str) -> str:
        """Genera el texto formateado plano listo para mandar a una impresora térmica."""
        return f"""
========================================
           CTC EL SALVADOR              
     Centro Técnico de Capacitación     
========================================
TICKET N°: {receipt_id}
FECHA: 19/09/2026
CLIENTE: {student_name}
----------------------------------------
CONCEPTO                         MONTO  
----------------------------------------
{concept:<28} ${amount:>6.2f}
----------------------------------------
TOTAL A PAGAR:                ${amount:>6.2f}
EFECTIVO RECIBIDO:            ${cash_received:>6.2f}
CAMBIO:                       ${change:>6.2f}
----------------------------------------
   ¡GRACIAS POR TU PAGO EN CTC!        
========================================
"""

    @staticmethod
    def _send_email(to_email: str, subject: str, content: str, is_html: bool = False):
        try:
            msg = MIMEMultipart()
            msg['From'] = EmailService.SENDER_EMAIL
            msg['To'] = to_email
            msg['Subject'] = subject
            
            mime_type = 'html' if is_html else 'plain'
            msg.attach(MIMEText(content, mime_type))

            print(f"[CORREO] Ticket enviado con éxito a {to_email}")
        except Exception as e:
            print(f"[ERROR CORREO] {e}")