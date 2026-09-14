# Nexo — Información que conecta

Sitio de noticias que se actualiza solo, usando GitHub Actions + GitHub Pages.

## Cómo está armado

- `index.html` — la portada del sitio.
- `news.json` — las noticias actuales. Lo genera automáticamente `scripts/fetch_news.py`, no se edita a mano.
- `scripts/fetch_news.py` — trae noticias reales desde los RSS de Ámbito, Página 12 y Clarín, y las guarda en `news.json`.
- `.github/workflows/update-news.yml` — la tarea programada que corre el script cada 30 minutos.

## Primeros pasos para publicarlo

1. **Subir estos archivos a un repositorio nuevo en GitHub.**
   - Creá un repositorio (por ejemplo `nexo`).
   - Subí toda esta carpeta tal cual (mantiene la estructura de subcarpetas `.github/` y `scripts/`).

2. **Activar GitHub Pages.**
   - En el repositorio: `Settings` → `Pages`.
   - En "Source", elegí la rama `main` (o `master`) y la carpeta `/ (root)`.
   - Guardá. GitHub te da una URL tipo `https://tu-usuario.github.io/nexo/`.

3. **Probar que la actualización automática funciona.**
   - En el repositorio: pestaña `Actions`.
   - Vas a ver el workflow "Actualizar noticias". Hacé clic en él y despues en "Run workflow" para probarlo a mano la primera vez (no hace falta esperar los 30 minutos).
   - Si corre bien, va a aparecer un commit nuevo actualizando `news.json`.

4. **Ver el sitio.**
   - Entrá a la URL de GitHub Pages del paso 2. Las noticias reales deberían aparecer ahí (puede tardar 1-2 minutos en propagarse la primera vez).

## Notas

- Si alguna fuente cambia su URL de RSS o deja de responder, el script sigue funcionando con las demás fuentes (no se cae todo por una sola que falle).
- Para agregar otra fuente de noticias, sumala en el diccionario `FEEDS` dentro de `scripts/fetch_news.py`.
- **C5N y El Destape**: las URLs que están puestas son una suposición (no encontré su RSS oficial confirmado). Corré la Action una vez a mano y fijate en los logs si esas dos fuentes trajeron resultados; si no, buscá el link real de su RSS o sacalas del diccionario.
- El clima, la cotización y el video destacado en el header/franja inferior siguen siendo datos de ejemplo (no vienen de una fuente real todavía) — eso lo conectamos en un paso aparte.
