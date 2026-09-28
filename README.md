# CTC Campus

Sistema de gestión académica y cobranza para **CTC El Salvador**. Permite registrar
estudiantes, administrar diplomados, controlar inscripciones y operar la cobranza de
colegiaturas cada 28 días desde una aplicación de escritorio.

## Funcionalidades

Cumple cada punto de la propuesta del proyecto; la matriz
[docs/TRAZABILIDAD.md](docs/TRAZABILIDAD.md) liga cada requisito con su
pantalla, su endpoint y su prueba automática.

- **Registro de matrícula en un solo formulario** (datos del estudiante, del
  responsable, diplomado, horario, fecha de matrícula, fecha de inicio de
  clases y observaciones), guardado en una sola transacción.
- **Cobro de colegiatura cada 28 días** desde la fecha de inicio de clases, con
  número fijo de cuotas por diplomado (6 meses = 7 cuotas).
- **Tarifario** (Matrícula $20, Promo 50% $10, Gratis $0; Grupal $25,
  Privado $55, On-line $70) editable por el administrador.
- **Efectivo y cambio** calculados al instante; también tarjeta y transferencia.
- **Caja diaria** con fondo inicial, **arqueo por denominación**, justificación
  obligatoria ante descuadres y **reportes de cierre** diario, por caja y mensual
  (imprimibles y exportables a Excel/PDF).
- **Alertas**: correo al estudiante y a su responsable 7 días antes del
  vencimiento, estado **PENDIENTE** al pasar los 28 días, lista de **cobros
  próximos y atrasados** siempre visible y aviso por **WhatsApp**.
- **Comprobantes** con número correlativo (`R-000001`): ticket de 80 mm impreso,
  PDF, correo y WhatsApp; reimpresión en cualquier momento.
- **Recargo por mora** de $3.00 (configurable) con opción de aplicarlo o no.
- **Estado de cuenta** por estudiante (cuotas pagadas y vencidas, saldo vencido
  y saldo por pagar).
- **Bitácora** de auditoría: cobros, anulaciones, cierres, cambios de
  configuración y de usuarios.
- Roles **Administrador** y **Cajero** aplicados en la API, contraseñas
  temporales que deben cambiarse y bloqueo por intentos fallidos.
- Hora oficial de El Salvador en todas las fechas de negocio.

Documentación: [manual de usuario](docs/MANUAL_USUARIO.md) ·
[manual técnico](docs/MANUAL_TECNICO.md) (arquitectura, modelo de datos,
reglas de negocio, API, seguridad y despliegue).

## Arquitectura

- `backend/`: API FastAPI, reglas de negocio, autenticación y migraciones Alembic.
- `desktop/`: aplicación nativa PySide6 para Windows.
- PostgreSQL: persistencia principal ejecutada mediante Docker Compose.
- JWT: autenticación de sesiones y autorización por rol.

## Inicio rápido

Requisitos: Docker Desktop, Python 3.12+ y un entorno virtual para el desktop.

```powershell
docker compose up -d
& .venv\Scripts\python.exe desktop\main.py
```

El backend queda disponible en `http://localhost:8000` y su documentación en
`http://localhost:8000/docs`.

## Crear y compartir el EXE

El cliente Windows se empaqueta con PyInstaller, una herramienta gratuita:

```powershell
& .venv\Scripts\python.exe -m pip install pyinstaller pywin32-ctypes
& .\desktop\build_exe.ps1
```

El script crea `dist\CTC-Campus.zip`. Para compartirlo, configura `config.json`
con la URL pública del backend antes de distribuirlo. El EXE es el cliente; la
base de datos y la API deben estar publicadas por separado para que varias
computadoras compartan los mismos datos.

## Publicar gratis en la nube

La configuración incluida usa Supabase para PostgreSQL y Render para FastAPI.
Ambos servicios tienen planes gratuitos con límites y el servicio web puede
dormirse después de un período sin tráfico.

1. Crea una cuenta en Supabase y crea un proyecto PostgreSQL.
2. En `Connect` copia la cadena de conexión compatible con IPv4/pooler.
3. No ejecutes scripts manuales en la base: Alembic aplica las migraciones al iniciar.
4. Sube este repositorio a GitHub sin subir `.env` ni contraseñas.
5. En Render selecciona `New > Blueprint` y conecta el repositorio. Render leerá
	`render.yaml` y creará `ctc-backend`.
6. Configura en Render las variables privadas `DATABASE_URL`, `SECRET_KEY`,
	`MAILJET_API_KEY`, `MAILJET_API_SECRET` y `EMAIL_FROM_ADDRESS`.
7. Prueba `https://TU-SERVICIO.onrender.com/api/health`.
8. Edita `dist\CTC-Campus-release\config.json`:

	```json
	{"api_base_url": "https://TU-SERVICIO.onrender.com"}
	```

9. Ejecuta `desktop\build_exe.ps1` y sube `dist\CTC-Campus.zip` a Google Drive.

Google Drive solo distribuye el archivo. Los datos compartidos viven en Supabase
y el `.exe` se comunica con ellos mediante FastAPI.

## Usuarios iniciales

El seed del backend crea estas cuentas con contraseña **temporal**; el sistema
obliga a cambiarla en el primer inicio de sesión:

- Administrador: `admin@ctc.edu.sv` / `123456`
- Cajero: `cajero@ctc.edu.sv` / `123456`

## Flujo de caja

1. Inicia sesión y abre `Caja y cobros → Abrir caja` con el fondo inicial.
2. Matricula en `Inscripciones → Nueva matrícula` y cobra colegiaturas con
   `Cobrar colegiatura` (o doble clic en la lista de cobros próximos). Sin caja
   abierta no se puede cobrar.
3. Al terminar el turno, `Cerrar caja (arqueo)`: cuenta billetes y monedas, y
   justifica cualquier diferencia. Se muestra el reporte de cierre.

## Permisos

La API hace cumplir los roles (no solo el menú del escritorio):

- **Solo administrador:** catálogos (diplomados y horarios), editar, anular o
  borrar inscripciones, anular comprobantes, borrar estudiantes, tarifario y
  configuración, cajeros (crear, activar/desactivar, restablecer contraseña),
  todas las cajas y cierres, y la bitácora.
- **Cajero:** matricular, editar estudiantes, cobrar, abrir/cerrar su caja y
  ver sus propios cierres.
- **Todos:** cambiar su propia contraseña. El administrador también puede
  cobrar, con su propia caja.

Un pago cobrado nunca se edita ni se borra: se **anula** el comprobante
completo con motivo, queda en el historial y deja de sumar en caja y reportes.

## Correo

El envío de comprobantes usa la API HTTP de [Mailjet](https://www.mailjet.com/)
(no SMTP): los hosts gratuitos como Render bloquean las conexiones SMTP
salientes para evitar spam, así que un socket a `smtp.gmail.com:587` falla
con "Network is unreachable" sin importar las credenciales. La API de Mailjet
corre sobre HTTPS/443, que no se bloquea.

1. Crea una cuenta gratuita en [Mailjet](https://www.mailjet.com/) (200
   correos/día gratis, sin necesitar un dominio propio).
2. En `Account Settings > Sender addresses and domains > Add a sender
   address` verifica el correo desde el que vas a enviar (puede ser tu
   correo personal); Mailjet te manda un enlace de confirmación.
3. En `Account Settings > API Key Management` copia tu `API Key` y `Secret
   Key`.
4. Configura en `.env`:

	```env
	MAILJET_API_KEY=tu_api_key
	MAILJET_API_SECRET=tu_secret_key
	EMAIL_FROM_ADDRESS=el_correo_que_verificaste
	EMAIL_FROM_NAME=CTC El Salvador
	```

Nunca publiques `.env` ni compartas sus credenciales.

### Recordatorios de pago (7 días antes)

El backend revisa los vencimientos cada hora por su cuenta y, además, en cada
inicio de sesión. En el plan gratuito de Render el servicio se duerme sin
tráfico, así que conviene programar un cron externo gratuito (por ejemplo
[cron-job.org](https://cron-job.org)) una vez al día:

- URL: `POST https://<tu-backend>.onrender.com/api/cron/reminders`
- Encabezado: `X-Cron-Secret: <valor de CRON_SECRET>` (Render lo genera; está
  en `Environment` del servicio)

## Pruebas

Las pruebas **nunca** usan el `DATABASE_URL` del `.env` (que apunta a la base
real): `backend/tests/conftest.py` crea una base SQLite temporal en cada
corrida, o usa `TEST_DATABASE_URL` si está definida (CI la apunta a su
PostgreSQL desechable).

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests -q
```

La prueba de cobros simultáneos necesita PostgreSQL (`SELECT ... FOR UPDATE`)
y se omite con SQLite; corre en CI.

`backend/tests/test_propuesta_pdf.py` tiene una prueba por cada punto de la
propuesta del proyecto (incluido el ejemplo literal 01/08/2026 → 29/08/2026).

El escritorio (panel, reportes de cierre, estado de cuenta, tickets) tiene
pruebas propias que no necesitan backend ni ventanas:

```powershell
& .venv\Scripts\python.exe -m pip install -r desktop\requirements-dev.txt
& .venv\Scripts\python.exe -m pytest desktop\tests -q
```

La aplicación desktop puede validarse sin mostrar ventanas con:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
& .venv\Scripts\python.exe -m compileall -q desktop backend\app
```