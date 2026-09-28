# Matriz de trazabilidad — Propuesta del proyecto

Cada requisito de *"Propuesta - Proyecto Software.pdf"* con la pantalla que lo
cumple, el endpoint del backend y la prueba automática que lo demuestra.
Las pruebas citadas están en `backend/tests/` (salvo las marcadas como
`desktop/tests/`).

## Requisitos de la pantalla del cajero

| # | Requisito (PDF) | Pantalla (escritorio) | Endpoint | Prueba |
| --- | --- | --- | --- | --- |
| 1 | Registro de matrícula de estudiantes (diplomados) con los datos de la página 2 | Inscripciones → **Nueva matrícula** (formulario único: estudiante nuevo o registrado, responsable, servicio, horario, fechas, observaciones) | `POST /enrollments/` (acepta `student` o `student_id`) | `test_propuesta_pdf.py::test_1_matricula_en_un_solo_formulario_con_todos_los_datos_del_pdf`, `test_1_matricula_es_atomica_si_falla_el_cobro_no_queda_el_estudiante` |
| 1 | Edad calculada | Nueva matrícula / Estudiantes (se calcula sola) | `GET /students/{id}` (edad calculada al consultar) | `test_otra_edad_siempre_actualizada_desde_la_fecha_de_nacimiento` |
| 1 | Catálogo de diplomados y horarios del PDF | Diplomados / Horarios (precargados por `seed_data.py`) | `GET /diplomas/`, `GET /schedules/` | `test_1_diplomados_y_horarios_oficiales_del_pdf_estan_cargados` |
| 2 | Cobro de colegiatura cada 28 días desde la fecha de inicio de clases | Caja y cobros → **Cobrar colegiatura** | `POST /payments/collect`, `GET /payments/next/{id}` | `test_2_ejemplo_literal_del_pdf_inicio_01_08_2026`, `test_2_primer_cobro_el_dia_de_inicio_y_siguiente_28_dias_despues` |
| 2 | Fecha de matrícula y fecha de inicio del diplomado | Nueva matrícula (dos fechas separadas) | `POST /enrollments/` (`enrollment_date`, `start_date`) | `test_payments.py`, `test_enrollments.py::test_registration_payment_does_not_shift_first_tuition_due_date` |
| 3 | Matrícula $20, Promo 50% $10, Gratis $0; Grupal $25, Privado $55, On-line $70 | Nueva matrícula (precios visibles); Configuración → Tarifario | `GET/PUT /config/` | `test_3_tarifas_del_pdf_por_defecto`, `test_3_matricula_gratis_no_genera_cobro_ni_pide_caja`, `test_3_las_tarifas_se_pueden_actualizar_sin_reprogramar` |
| 4 | Campo "Efectivo:" y cálculo automático del "Cambio:" | Nueva matrícula y Cobrar colegiatura (cambio en vivo; no deja confirmar si falta efectivo) | `POST /payments/collect`, `POST /enrollments/` | `test_4_efectivo_y_cambio_calculado_por_el_sistema`, `test_4_con_tarjeta_no_hay_efectivo_ni_cambio` |
| 5 | Cierre de caja **diario**: reporte que suma los pagos para contrastarlo con el dinero físico | Caja y cobros → **Cerrar caja (arqueo)** (billetes y monedas) → reporte imprimible; **Cierre del día** | `POST /cashier/register/close`, `GET /cashier/registers/{id}/report`, `GET /cashier/daily` | `test_5_reporte_de_cierre_diario_con_detalle_por_concepto_y_arqueo_por_denominacion`, `test_5_descuadre_exige_justificacion_y_queda_en_bitacora`, `test_5_cierre_diario_general_y_mensual_por_dia` |
| 5 | Cierre de caja **mensual** | Caja y cobros → **Cierre mensual**; Cajeros y cierres → Ver cierre mensual | `GET /cashier/monthly` | `test_5_cierre_diario_general_y_mensual_por_dia`, `desktop/tests/test_cash_reports.py` |
| 6 | Notificar al estudiante 7 días antes del vencimiento | Automático (correo al estudiante y a su responsable); botón **Avisar por WhatsApp** | Hilo horario del backend, inicio de sesión y `POST /api/cron/reminders` | `test_6_aviso_7_dias_antes_llega_al_estudiante_y_al_responsable`, `test_reminders.py` |
| 6 | Estado "Pendiente" si pasan 28 días sin un nuevo cobro | Inscripciones (columna Estado y cuotas vencidas) | Se recalcula en cada consulta | `test_6_estado_pendiente_al_pasar_28_dias_sin_cobro`, `test_payment_cycle.py` |
| 6 | Mostrar al cajero o administrador los pagos próximos | Caja y cobros → panel **Cobros próximos y atrasados** (siempre visible, doble clic para cobrar); Dashboard | `GET /reports/upcoming-payments` | `test_6_lista_de_cobros_proximos_con_whatsapp_y_monto_adeudado` |

## Mejoras recomendadas

| Mejora (PDF) | Cómo se cumple | Endpoint | Prueba |
| --- | --- | --- | --- |
| Imprimir y/o enviar el ticket al correo | Ticket de 80 mm (impresora o PDF), por correo al estudiante y responsable, y por WhatsApp; número correlativo `R-000001`; **reimpresión** desde la lista de pagos | `GET /receipts/{id}`, `GET /payments/{id}/ticket` | `test_mejora_ticket_con_numero_correlativo_y_reimpresion`, `desktop/tests/test_cash_reports.py::test_ticket_rows_and_whatsapp` |
| Recargo de $3.00 al pasar los 28 días, con opción de aplicarlo | Casilla "Aplicar recargo por mora" en el cobro; monto configurable | `POST /payments/collect` (`apply_late_fee`) | `test_mejora_recargo_opcional_de_3_dolares`, `test_payments.py` |

## "Otras" mejoras (justificación de cada una)

| Mejora | Por qué aporta | Prueba |
| --- | --- | --- |
| Número fijo de cuotas por diplomado y estado **FINALIZADA** | Sin tope se podía cobrar un diplomado para siempre | `test_2_el_diplomado_tiene_un_numero_fijo_de_cuotas` |
| Todo cobro exige **caja abierta** (también el administrador) y cada pago queda enlazado a su caja | Ningún dinero queda fuera de un arqueo; una caja abierta de un día para otro ya no mezcla cobros | `test_5_todo_cobro_exige_caja_abierta_tambien_para_el_administrador`, `test_5_una_caja_solo_suma_sus_propios_cobros` |
| Un pago cobrado **no se edita ni se borra**: se anula el comprobante completo con motivo | Integridad contable; el ticket impreso siempre coincide con lo registrado | `test_advance_payment_is_one_receipt_with_28_day_cycle_and_voids_as_a_whole`, `test_otra_solo_quedan_endpoints_de_cobro_seguros` |
| **Bitácora** de auditoría | Saber quién cobró, anuló, cerró caja o cambió precios | `test_otra_bitacora_registra_cobros_y_anulaciones` |
| **Estado de cuenta** por estudiante (cuotas, saldo vencido y saldo pendiente) | Se entrega al estudiante/responsable | `test_history_and_edit.py::test_student_history_lists_payments_and_totals`, `desktop/tests/test_report_export.py` |
| Hora oficial de **El Salvador** (UTC-6) | El servidor corre en UTC: después de las 6 p. m. fechaba los cobros al día siguiente | `test_otra_fecha_y_hora_oficial_de_el_salvador` |
| **Contraseña temporal** obligatoria de cambiar y **bloqueo** por intentos fallidos persistente | Seguridad de las cuentas de cajero | `test_otra_contrasena_temporal_obliga_a_cambiarla`, `test_otra_bloqueo_por_intentos_fallidos_sobrevive_a_un_reinicio` |
| No se registra dos veces al mismo estudiante | Evita duplicados en reportes | `test_1_no_se_registra_dos_veces_al_mismo_estudiante` |
| Diplomado u horario inactivo no recibe inscripciones | Permite retirar un programa sin borrar su historial | `test_otra_diplomado_inactivo_no_recibe_inscripciones` |

## Lo que se eliminó por no aportar

| Elemento | Motivo |
| --- | --- |
| Precios por diplomado (`registration_fee`, `monthly_fee`) | El sistema nunca los usaba para cobrar: el tarifario es institucional. Mostraban precios falsos ($50/$40) |
| DUI del estudiante | La propuesta solo pide el DUI del responsable y el formulario nunca lo pedía |
| Alta manual de pagos, "pago adelantado" separado, editar y borrar pagos | Permitían alterar dinero ya cobrado; el cobro normal ya admite varias cuotas |
| Registro de estudiantes separado de la matrícula | Duplicaba el flujo; ahora se hace en el formulario único |
| `/reports/cashier-monthly` | Duplicaba `/cashier/monthly` |
