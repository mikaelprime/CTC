from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database.database import get_db
from app.services.cashier_service import CashierService
from app.services.email_service import EmailService

router = APIRouter(prefix="/payments", tags=["cashier"])

class PaymentCreate(BaseModel):
    cashier_id: int
    student_id: int
    student_email: str
    student_name: str
    concept: str # Ej: "Matrícula Regular", "Colegiatura Plan Grupal"
    amount: float
    cash_received: float # Efectivo entregado por el cliente

@router.post("/")
def process_payment(data: PaymentCreate, db: Session = Depends(get_db)):
    # 1. VERIFICACIÓN Y BLOQUEO: Valida si la caja está abierta antes de cobrar
    CashierService.verify_active_box(db, cashier_id=data.cashier_id)

    # 2. CALCULADORA DE CAMBIO
    if data.cash_received < data.amount:
        raise HTTPException(status_code=400, detail="El efectivo ingresado es menor al total a pagar.")
    
    change = round(data.cash_received - data.amount, 2)
    receipt_number = "REC-2026-001" # Generador de número de recibo

    # 3. ENVIAR TICKET EN FORMATO HTML AL CORREO DEL ESTUDIANTE
    EmailService.send_html_ticket(
        student_email=data.student_email,
        student_name=data.student_name,
        concept=data.concept,
        amount=data.amount,
        cash_received=data.cash_received,
        change=change,
        receipt_id=receipt_number
    )

    # 4. GENERAR TEXTO PARA IMPRESORA TÉRMICA (Para imprimir en caja)
    thermal_ticket_text = EmailService.generate_thermal_ticket_text(
        student_name=data.student_name,
        concept=data.concept,
        amount=data.amount,
        cash_received=data.cash_received,
        change=change,
        receipt_id=receipt_number
    )

    return {
        "status": "Pago Registrado Con Éxito",
        "receipt_id": receipt_number,
        "monto_pagado": data.amount,
        "efectivo_recibido": data.cash_received,
        "cambio_entregado": change,
        "ticket_correo_enviado": True,
        "ticket_para_impresora": thermal_ticket_text # Se envía a la impresora local
    }