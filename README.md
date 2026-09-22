# CTC Campus

Sistema de gestión académica y cobranza para **CTC El Salvador**. Permite registrar
estudiantes, administrar diplomados, controlar inscripciones y operar la cobranza de
colegiaturas cada 28 días desde una aplicación de escritorio.

## Funcionalidades

- Inicio de sesión con correo y contraseña mediante JWT.
- Roles `Administrador` y `Cajero` con permisos separados.
- Creación de cajeros desde el panel del administrador.
- Registro de estudiantes y datos del responsable.
- Catálogo de diplomados, horarios e inscripciones.
- Cálculo automático de fecha de finalización según la duración del diplomado.
- Cálculo de próxima cuota cada 28 días desde el inicio de clases.
- Búsqueda instantánea en estudiantes, inscripciones, pagos y catálogos.
- Registro de pagos, efectivo recibido y cambio.
- Recargo configurable por mora.
- Apertura de caja con fondo inicial desde el módulo de Pagos.
- Cierre de caja con arqueo físico y explicación obligatoria ante diferencias.
- Reporte mensual de cajas y pagos próximos dentro de 7 días.
- Comprobantes de inscripción y pago por correo SMTP configurable.
- Dashboard con indicadores esenciales de estudiantes, inscripciones, pendientes y vencimientos.
- Tema oscuro y claro.
- Modo pantalla completa y salida segura del programa.
- Animación de entrada del login y prevención de ventanas duplicadas.

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
	`SMTP_USER`, `SMTP_PASSWORD` y `SMTP_FROM_EMAIL`.
7. Prueba `https://TU-SERVICIO.onrender.com/api/health`.
8. Edita `dist\CTC-Campus-release\config.json`:

	```json
	{"api_base_url": "https://TU-SERVICIO.onrender.com"}
	```

9. Ejecuta `desktop\build_exe.ps1` y sube `dist\CTC-Campus.zip` a Google Drive.

Google Drive solo distribuye el archivo. Los datos compartidos viven en Supabase
y el `.exe` se comunica con ellos mediante FastAPI.

## Usuarios iniciales

El seed del backend crea estas cuentas de desarrollo:

- Administrador: `admin@ctc.edu.sv` / `123456`
- Cajero: `cajero@ctc.edu.sv` / `123456`

Cambia estas contraseñas antes de usar el sistema fuera de desarrollo.

## Flujo de caja

1. Inicia sesión como cajero.
2. Abre `Pagos` y selecciona `Abrir caja`.
3. Ingresa el fondo inicial.
4. Registra cobros únicamente con la caja abierta.
5. Al finalizar, selecciona `Cerrar caja`, cuenta el efectivo e ingresa una explicación si existe diferencia.

## Correo

Configura una cuenta SMTP en `.env`. Para Gmail usa una contraseña de aplicación:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_correo
SMTP_PASSWORD=tu_contraseña_de_aplicacion
SMTP_FROM_EMAIL=tu_correo
SMTP_FROM_NAME=CTC El Salvador
```

Nunca publiques `.env` ni compartas sus credenciales.

## Pruebas

Las pruebas backend deben ejecutarse dentro del contenedor para que puedan resolver
el hostname de PostgreSQL:

```powershell
docker compose exec backend alembic upgrade head
docker compose exec backend pytest tests -q
```

La lógica de agregación del panel (`desktop/data_service.py`) tiene pruebas
propias que no necesitan backend ni ventanas:

```powershell
& .venv\Scripts\python.exe -m pip install -r desktop\requirements-dev.txt
& .venv\Scripts\python.exe -m pytest desktop\tests -q
```

La aplicación desktop puede validarse sin mostrar ventanas con:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
& .venv\Scripts\python.exe -m compileall -q desktop backend\app
```