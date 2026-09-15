#!/usr/bin/env python3
"""
Trae noticias reales desde RSS de varias fuentes (Clarín, Página 12, Ámbito)
y genera /news.json con los datos organizados por categoría, listos para
que el sitio (index.html) los muestre.

Se ejecuta automáticamente vía GitHub Actions (ver .github/workflows/update-news.yml),
pero también se puede correr a mano con: python scripts/fetch_news.py
"""

import json
import re
import sys
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

import feedparser

# ---------------------------------------------------------------------------
# Fuentes por categoría. Cada categoría junta varias fuentes para que el
# sitio sea plural (no depender de un solo medio).
# ---------------------------------------------------------------------------
FEEDS = {
    "politica": [
        ("Ámbito", "https://www.ambito.com/rss/pages/politica.xml"),
        ("Página 12", "https://www.pagina12.com.ar/rss/portada"),
        ("Clarín", "https://www.clarin.com/rss/politica/"),
        ("Ámbito Mundo", "https://www.ambito.com/rss/pages/mundo.xml"),
        ("C5N", "https://www.c5n.com/rss/pages/politica.xml"),
        ("Infobae", "https://www.infobae.com/arc/outboundfeeds/rss/category/politica/?outputType=xml"),  # sin confirmar, revisar si no trae nada
        ("Tiempo Argentino", "https://www.tiempoar.com.ar/politica/feed/"),  # sin confirmar, revisar si no trae nada
    ],
    "economia": [
        ("Ámbito", "https://www.ambito.com/rss/pages/economia.xml"),
        ("Clarín", "https://www.clarin.com/rss/economia/"),
        ("C5N", "https://www.c5n.com/rss/pages/economia.xml"),
        ("Infobae", "https://www.infobae.com/arc/outboundfeeds/rss/category/economia/?outputType=xml"),  # sin confirmar, revisar si no trae nada
        ("Tiempo Argentino", "https://www.tiempoar.com.ar/economia/feed/"),  # sin confirmar, revisar si no trae nada
    ],
    "deportes": [
        ("Ámbito", "https://www.ambito.com/rss/pages/deportes.xml"),
        ("Clarín", "https://www.clarin.com/rss/deportes/"),
        ("C5N", "https://www.c5n.com/rss/pages/deportes.xml"),
        ("Infobae", "https://www.infobae.com/arc/outboundfeeds/rss/category/deportes/?outputType=xml"),  # sin confirmar, revisar si no trae nada
        ("Olé", "https://www.ole.com.ar/rss/futbol-primera/"),  # sin confirmar, revisar si no trae nada
    ],
    "policiales_actualidad": [
        ("Clarín", "https://www.clarin.com/rss/policiales/"),  # sin confirmar, revisar si no trae nada
        ("C5N", "https://www.c5n.com/rss/pages/sociedad.xml"),
        ("Infobae", "https://www.infobae.com/arc/outboundfeeds/rss/category/sociedad/policiales/?outputType=xml"),  # sin confirmar, revisar si no trae nada
    ],
    "internacional": [
        ("Ámbito", "https://www.ambito.com/rss/pages/mundo.xml"),
        ("C5N", "https://www.c5n.com/rss/pages/mundo.xml"),
        ("Clarín", "https://www.clarin.com/rss/mundo/"),  # sin confirmar, revisar si no trae nada
        ("Infobae", "https://www.infobae.com/arc/outboundfeeds/rss/category/america/?outputType=xml"),  # sin confirmar, revisar si no trae nada
    ],
    "espectaculos": [
        ("Ámbito", "https://www.ambito.com/rss/pages/espectaculos.xml"),
        ("C5N", "https://www.c5n.com/rss/pages/ratingcero.xml"),
        ("Clarín", "https://www.clarin.com/rss/espectaculos/"),  # sin confirmar, revisar si no trae nada
        ("Infobae", "https://www.infobae.com/arc/outboundfeeds/rss/category/teleshow/?outputType=xml"),  # sin confirmar, revisar si no trae nada
    ],
    "tecnologia": [
        ("Ámbito", "https://www.ambito.com/rss/pages/tecnologia.xml"),
        ("C5N", "https://www.c5n.com/rss/pages/tecnologia.xml"),
        ("Clarín", "https://www.clarin.com/rss/tecnologia/"),  # sin confirmar, revisar si no trae nada
        ("Infobae", "https://www.infobae.com/arc/outboundfeeds/rss/category/tecno/?outputType=xml"),  # sin confirmar, revisar si no trae nada
    ],
    "autos": [
        ("C5N", "https://www.c5n.com/rss/pages/autos.xml"),
        ("Parabrisas", "https://parabrisas.perfil.com/feed"),  # sin confirmar, revisar si no trae nada
    ],
    "turismo": [
        ("Clarín", "https://www.clarin.com/rss/viajes/"),  # sin confirmar, revisar si no trae nada
        ("Infobae", "https://www.infobae.com/arc/outboundfeeds/rss/category/viajes/?outputType=xml"),  # sin confirmar, revisar si no trae nada
    ],
    "local": [
        ("0221", "https://www.0221.com.ar/rss/pages/la-plata.xml"),
        ("0221 Policiales", "https://www.0221.com.ar/rss/pages/policiales.xml"),
        ("0221 Universidad", "https://www.0221.com.ar/rss/pages/universidad.xml"),
        ("0221 ¿Qué Hago?", "https://www.0221.com.ar/rss/pages/que-hago.xml"),
        ("El Día", "https://www.eldia.com/.rss"),
    ],
}

# Se traen más noticias que las que se muestran de una: el sitio va rotando
# entre este pool más grande (mezclando nacionales e internacionales),
# como ya hacen el clima y la cotización.
ITEMS_PER_CATEGORY = 12
REQUEST_HEADERS = {
    # Algunos sitios bloquean pedidos sin User-Agent de navegador.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

IMG_TAG_RE = re.compile(r'<img[^>]+src="([^"]+)"', re.IGNORECASE)


def limpiar_texto(texto: str) -> str:
    """Saca tags HTML y espacios de más de un título/resumen de RSS."""
    if not texto:
        return ""
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = unescape(texto)
    return " ".join(texto.split())


def extraer_imagen(entry) -> str:
    """Busca una imagen en distintos formatos posibles del RSS."""
    # 1) media:content / media:thumbnail (formato usado por Ámbito, Clarín)
    for key in ("media_content", "media_thumbnail"):
        media = entry.get(key)
        if media:
            url = media[0].get("url")
            if url:
                return url

    # 2) enclosure (algunos feeds de Página 12)
    for link in entry.get("links", []):
        if link.get("type", "").startswith("image"):
            return link.get("href", "")

    # 3) imagen embebida dentro del resumen/summary en HTML
    resumen_html = entry.get("summary", "") or entry.get("description", "")
    match = IMG_TAG_RE.search(resumen_html)
    if match:
        return match.group(1)

    return ""


def traer_categoria(nombre_categoria: str, fuentes: list) -> list:
    items = []
    for nombre_fuente, url in fuentes:
        try:
            feed = feedparser.parse(url, request_headers=REQUEST_HEADERS)
        except Exception as exc:  # noqa: BLE001 - queremos seguir con las otras fuentes
            print(f"  ! No se pudo leer {nombre_fuente} ({url}): {exc}")
            continue

        cantidad_antes = len(items)
        for entry in feed.entries[:6]:
            titulo = limpiar_texto(entry.get("title", ""))
            if not titulo:
                continue
            items.append(
                {
                    "titulo": titulo,
                    "link": entry.get("link", ""),
                    "imagen": extraer_imagen(entry),
                    "fuente": nombre_fuente,
                    "fecha": entry.get("published", "") or entry.get("updated", ""),
                }
            )
        print(f"  · {nombre_fuente}: {len(items) - cantidad_antes} noticias (entries en el feed: {len(feed.entries)})")

    # Diversificar: alternar fuentes en vez de mostrar 5 seguidas del mismo medio
    items_por_fuente = {}
    for item in items:
        items_por_fuente.setdefault(item["fuente"], []).append(item)

    resultado = []
    while len(resultado) < ITEMS_PER_CATEGORY and any(items_por_fuente.values()):
        for fuente in list(items_por_fuente.keys()):
            if items_por_fuente[fuente]:
                resultado.append(items_por_fuente[fuente].pop(0))
                if len(resultado) >= ITEMS_PER_CATEGORY:
                    break

    return resultado


def main():
    print("Buscando noticias...")
    data = {
        "actualizado": datetime.now(timezone.utc).isoformat(),
        "categorias": {},
    }

    for categoria, fuentes in FEEDS.items():
        print(f"- {categoria}")
        data["categorias"][categoria] = traer_categoria(categoria, fuentes)

    salida = Path(__file__).resolve().parent.parent / "news.json"
    salida.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Listo: {salida} ({sum(len(v) for v in data['categorias'].values())} noticias)")


if __name__ == "__main__":
    main()
