# Pulso: web de tendencias tech e IA en piloto automático

Cada 6 horas, GitHub Actions:
1. Lee Hacker News y elige las historias con más puntos y comentarios que aún no se han publicado.
2. Descarga el artículo y los comentarios destacados, y Claude escribe un resumen en español (sin inventar datos; si no hay texto suficiente, se descarta).
3. Genera la web estática (portada, una página por tema, páginas de categoría, sitemap, RSS) y la publica en GitHub Pages.

## Puesta en marcha (una sola vez, ~10 minutos)
1. Crea un repositorio **público** en GitHub y sube el contenido de esta carpeta.
2. Settings → Secrets and variables → Actions → New repository secret: `ANTHROPIC_API_KEY` con tu clave de la API de Claude.
3. Settings → Pages → Source: **GitHub Actions**.
4. Pestaña Actions → "Actualizar y publicar" → Run workflow. En 2-3 minutos tendrás la web en `https://TU_USUARIO.github.io/NOMBRE_REPO/`.
5. Desde ahí se actualiza sola.

## Coste
Con el modelo Haiku y ~6 resúmenes por ejecución, del orden de céntimos al día. GitHub Pages y Actions son gratis en repos públicos.

## Ajustes útiles (variables de entorno en el workflow)
- `MAX_NEW` (6): temas nuevos por ejecución. `MIN_SCORE` (150) y `MIN_COMMENTS` (30): umbral de calidad.
- `ADSENSE_ID` (variable del repo, ej. `ca-pub-XXXX`): activa AdSense cuando tengas tráfico.
- Nombre y lema: constantes `NAME` y `TAGLINE` en `build.py`.

## Probar en local sin API
```
DATA_FILE=/tmp/demo.json OUT_DIR=/tmp/site python collect.py --demo
DATA_FILE=/tmp/demo.json OUT_DIR=/tmp/site python build.py
python -m http.server -d /tmp/site
```
