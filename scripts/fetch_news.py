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
        ("El Día Deportes", "https://www.eldia.com/deportes/.rss"),
        ("0221 Deportes", "https://www.0221.com.ar/rss/pages/deportes.xml"),
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
        ("Infobae Tecno", "https://www.infobae.com/arc/outboundfeeds/rss/category/tecno/?outputType=xml"),  # sin confirmar, revisar si no trae nada
        ("Infobae Ciencia", "https://www.infobae.com/arc/outboundfeeds/rss/category/ciencia/?outputType=xml"),  # sin confirmar, revisar si no trae nada
        ("Agencia CyTA", "https://www.agenciacyta.org.ar/feed/"),  # sin confirmar, revisar si no trae nada
        ("Agencia CTyS", "https://www.ctys.com.ar/feed/"),  # sin confirmar, revisar si no trae nada
    ],
    "autos": [
        ("Parabrisas", "https://parabrisas.perfil.com/feed"),  # sin confirmar, revisar si no trae nada
        ("TN Autos", "https://tn.com.ar/arc/outboundfeeds/rss/category/autos/?outputType=xml"),  # sin confirmar, revisar si no trae nada
        ("Autocosmos", "https://noticias.autocosmos.com.ar/feed/"),  # sin confirmar, revisar si no trae nada
    ],
    "turismo": [
        ("Viajando Destinos", "https://argentina.viajando.travel/rss/destinos.xml"),
        ("Viajando Últimas Noticias", "https://argentina.viajando.travel/rss/ultimas-noticias.xml"),
        ("Viajando Escapadas", "https://argentina.viajando.travel/rss/escapadas.xml"),
        ("Viajando Sol y Playa", "https://argentina.viajando.travel/rss/sol-playa.xml"),
    ],
    "vida_sana": [
        ("Infobae Salud", "https://www.infobae.com/arc/outboundfeeds/rss/category/salud/?outputType=xml"),  # sin confirmar, revisar si no trae nada
    ],
    "local": [
        ("0221", "https://www.0221.com.ar/rss/pages/la-plata.xml"),
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

# Palabras que indican que una noticia es policial/de inseguridad. Se usan
# para filtrar la categoría "local", que trae feeds generales (no solo de
# un tema) y por eso puede traer alguna nota de este tipo mezclada.
PALABRAS_POLICIALES = [
    "polic", "robo", "robó", "robaron", "asalto", "asaltaron", "asesinato",
    "asesinaron", "homicidio", "crimen", "detuvieron", "detenido", "preso",
    "condena", "condenaron", "juicio", "fiscal", "femicidio", "balacera",
    "tiroteo", "secuestro", "narco", "droga", "cárcel", "delito", "hurto",
    "arma de fuego", "puñalada", "apuñal",
]


def es_noticia_policial(titulo: str) -> bool:
    titulo_lower = titulo.lower()
    return any(palabra in titulo_lower for palabra in PALABRAS_POLICIALES)



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
    # Cielosports (deportes de La Plata) tiene más peso a propósito: la mayoría
    # de los primeros lectores del sitio son de La Plata, así que Gimnasia y
    # Estudiantes se ven más seguido que en un medio genérico.
    FUENTES_CON_MAS_PESO = {"El Día Deportes": 12, "0221 Deportes": 12}

    items = []
    for nombre_fuente, url in fuentes:
        try:
            feed = feedparser.parse(url, request_headers=REQUEST_HEADERS)
        except Exception as exc:  # noqa: BLE001 - queremos seguir con las otras fuentes
            print(f"  ! No se pudo leer {nombre_fuente} ({url}): {exc}")
            continue

        limite = FUENTES_CON_MAS_PESO.get(nombre_fuente, 6)
        cantidad_antes = len(items)
        for entry in feed.entries[:limite]:
            titulo = limpiar_texto(entry.get("title", ""))
            if not titulo:
                continue
            if nombre_categoria == "local" and es_noticia_policial(titulo):
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

    # Diversificar: alternar fuentes en vez de mostrar 5 seguidas del mismo medio.
    # Las fuentes en FUENTES_CON_MAS_PESO aparecen más veces en la rotación,
    # así que terminan ocupando más lugares en el resultado final.
    items_por_fuente = {}
    for item in items:
        items_por_fuente.setdefault(item["fuente"], []).append(item)

    orden_rotacion = []
    for fuente in items_por_fuente.keys():
        peso = 3 if fuente in FUENTES_CON_MAS_PESO else 1
        orden_rotacion.extend([fuente] * peso)

    resultado = []
    i = 0
    intentos_maximos = ITEMS_PER_CATEGORY * 20  # por las dudas, para no colgarse
    while len(resultado) < ITEMS_PER_CATEGORY and any(items_por_fuente.values()) and i < intentos_maximos:
        fuente = orden_rotacion[i % len(orden_rotacion)]
        if items_por_fuente[fuente]:
            resultado.append(items_por_fuente[fuente].pop(0))
        i += 1

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
