# CTC Campus — App de Escritorio

Interfaz nativa (PySide6/Qt) para el sistema CTC. El backend (FastAPI) y la base de
datos siguen corriendo en Docker; esta app corre directamente en Windows y consume
la API vía HTTP.

## Requisitos

1. Backend + Postgres arriba:
   ```
   docker compose up -d
   ```
2. Dependencias de escritorio (en el host, no en Docker — una GUI no puede mostrarse
   dentro de un contenedor):
   ```
   pip install -r desktop/requirements.txt
   ```

## Ejecutar

```
python desktop/main.py
```

Inicia sesión con un usuario existente (el seed crea `admin@ctc.edu.sv` / `123456`,
ver `backend/seed_data.py`).

Por defecto la app apunta a `http://localhost:8000`. Para usar otra URL:

```
set API_BASE_URL=http://mi-servidor:8000
python desktop/main.py
```

## Crear la aplicación Windows

Instala PyInstaller en el entorno virtual y ejecuta el script de compilación:

```powershell
& .venv\Scripts\python.exe -m pip install pyinstaller
& .\desktop\build_exe.ps1
```

El resultado queda en `dist\CTC-Campus-release` y `dist\CTC-Campus.zip`. Antes de
compartirlo, edita `config.json` junto al ejecutable y cambia `api_base_url` por la
URL pública del backend. El ejecutable no contiene la base de datos ni credenciales
SMTP.

## Módulos

Todos los módulos leen y escriben datos reales: estudiantes, inscripciones, pagos,
horarios, diplomas, cajeros y configuración. La interfaz también permite buscar
registros, alternar tema claro/oscuro y usar pantalla completa.
