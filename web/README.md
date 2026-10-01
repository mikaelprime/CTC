# Página web de descargas

Página pública y gratuita (GitHub Pages) para descargar la aplicación y las
guías (en PDF o para leer en línea): **https://mikaelprime.github.io/CTC/**

Usa Tailwind CSS y GSAP desde CDN; no necesita compilar nada.

| Archivo | Contenido |
| --- | --- |
| `index.html` | La página |
| `descargas/*.pdf` | Guías listas para descargar |
| `guias/*.html` | Fuente de las guías (también se leen en línea) |
| `generar_pdfs.ps1` | Vuelve a crear los PDF tras editar una guía |

Las guías son versiones cortas; los manuales completos siguen en `docs/`.

## Publicar (una sola vez)

1. GitHub → *Settings → Pages → Build and deployment → Source:* **GitHub Actions**.
2. Haz push a `develop` o `main` con cambios en `web/` (o *Actions → Publicar
   página web → Run workflow*).

## Subir una versión nueva de la aplicación

El ZIP (~88 MB) no va en el repositorio: se sube como *Release* y la página
siempre enlaza a la más reciente.

1. Ejecuta `desktop\build_exe.ps1` (crea `dist\CTC-Campus.zip`).
2. GitHub → *Releases → Draft a new release*, crea una etiqueta (ej. `v1.0.0`)
   y adjunta `dist\CTC-Campus.zip` **con ese nombre exacto**.
3. Publica. El botón de la página descarga automáticamente esa versión.
