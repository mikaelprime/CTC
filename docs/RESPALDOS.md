# Respaldos, servidor despierto y panel web

Tres complementos que funcionan aparte de la aplicación.

## 1. Respaldo automático de la base de datos

`.github/workflows/backup.yml` copia cada noche (2:00 a. m. de El Salvador) la
base de Supabase con `pg_dump`, la **cifra con AES-256** y la guarda 30 días
en GitHub (*Actions → Respaldo de la base de datos → la corrida → Artifacts*).

Va cifrada porque el repositorio es público: cualquier usuario de GitHub puede
descargar los artefactos, y la base tiene DUI, teléfonos y correos. Sin la
contraseña el archivo no se puede abrir.

### Configuración (una sola vez)

En GitHub: *Settings → Secrets and variables → Actions → New repository secret*.

| Secreto | Valor |
|---|---|
| `BACKUP_DATABASE_URL` | La cadena de conexión de Supabase (la misma `DATABASE_URL` de Render) |
| `BACKUP_PASSPHRASE` | Una contraseña larga que elijas. **Guárdala aparte**: sin ella no se puede restaurar |

Para probarlo sin esperar a la noche: *Actions → Respaldo de la base de datos
→ Run workflow*.

### Restaurar un respaldo

Requiere [PostgreSQL 17](https://www.postgresql.org/download/) (trae
`pg_restore`) y `gpg` (viene con Git para Windows).

```bash
# 1. Descifrar (pide la contraseña BACKUP_PASSPHRASE)
gpg --output ctc.dump --decrypt ctc_2026-09-28_0200.dump.gpg

# 2. Restaurar sobre la base (REEMPLAZA las tablas actuales por las del respaldo)
pg_restore --clean --if-exists --no-owner --no-privileges --dbname "CADENA_DE_CONEXION" ctc.dump
```

Para revisar el contenido sin tocar ninguna base:
`pg_restore --list ctc.dump`.

## 2. Mantener el backend despierto y avisos diarios

`.github/workflows/keep-alive.yml`:

- Visita `/api/health` **cada 10 minutos**: el plan gratuito de Render duerme
  el servicio tras 15 minutos sin tráfico, y la primera petición tardaba hasta
  un minuto (el login parecía colgado).
- Una vez al día (8:00 a. m. de El Salvador) llama a `/api/cron/reminders` para
  enviar los avisos de vencimiento aunque nadie inicie sesión.

### Configuración (una sola vez)

1. En Render: *ctc-backend → Environment* → copia el valor de `CRON_SECRET`.
2. En GitHub: crea el secreto `CRON_SECRET` con ese mismo valor.
3. Pruébalo: *Actions → Mantener backend despierto y avisos diarios → Run workflow*.
   Deben salir en verde los pasos "ping" y "reminders".

Notas:

- GitHub puede retrasar unos minutos las tareas programadas.
- GitHub desactiva las tareas programadas si el repositorio pasa **60 días sin
  cambios**; se reactivan desde la pestaña *Actions*.
- Render gratuito da 750 horas al mes; un solo servicio encendido todo el mes
  usa unas 744, así que alcanza.

## 3. Panel web de consulta

Página de **solo lectura** para ver desde el celular o cualquier navegador:

**https://ctc-backend-j3id.onrender.com/panel**

Muestra lo cobrado en el día (total, efectivo y comprobantes), los estudiantes
atrasados y los que vencen en 7 días (con botón de WhatsApp), lo cobrado por
concepto, las cajas del día con sobrante o faltante, los cobros por día del mes
y, para el administrador, la actividad reciente de la bitácora. Se actualiza
sola cada minuto.

- Se entra con el mismo usuario y contraseña de la app de escritorio, con los
  mismos permisos: el cajero ve solo lo suyo y el administrador ve todo.
- No permite cobrar ni modificar nada: eso se hace en la app de escritorio.
- La sesión dura mientras la pestaña esté abierta.
- La sirve el mismo backend (`backend/app/panel/index.html`), así que no
  necesita otro hosting.
