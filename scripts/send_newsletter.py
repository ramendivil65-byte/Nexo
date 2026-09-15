#!/usr/bin/env python3
"""
Arma un newsletter en HTML con los titulares del día (desde news.json) y lo
manda automáticamente a la lista de suscriptores de Nexo, usando la API de
Brevo (gratis, 300 emails/día).

Se ejecuta una vez al día vía GitHub Actions (ver .github/workflows/send-newsletter.yml).
Necesita la variable de entorno BREVO_API_KEY (se configura como Secret en GitHub,
nunca queda visible en el código).
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
LISTA_SUSCRIPTORES_ID = 2  # ID de la lista "Suscriptores Nexo" en Brevo
REMITENTE_NOMBRE = "Nexo"
REMITENTE_EMAIL = "ramendivil65@gmail.com"

CATEGORIAS_A_INCLUIR = [
    ("politica", "📜 Política"),
    ("economia", "💵 Economía"),
    ("deportes", "⚽ Deportes"),
    ("policiales_actualidad", "🚨 Policiales y Actualidad"),
]

NOTICIAS_POR_CATEGORIA = 3


def armar_html(data: dict) -> str:
    fecha = datetime.now().strftime("%d/%m/%Y")
    bloques = []

    for clave, titulo_categoria in CATEGORIAS_A_INCLUIR:
        items = (data.get("categorias") or {}).get(clave) or []
        if not items:
            continue

        filas = ""
        for noticia in items[:NOTICIAS_POR_CATEGORIA]:
            titulo = noticia.get("titulo", "")
            link = noticia.get("link", "#")
            fuente = noticia.get("fuente", "")
            filas += f"""
            <tr>
              <td style="padding:10px 0; border-bottom:1px solid #E5E7EB;">
                <a href="{link}" style="color:#0B3D91; font-weight:700; text-decoration:none; font-size:15px;">{titulo}</a>
                <div style="color:#9CA3AF; font-size:12px; margin-top:4px;">{fuente}</div>
              </td>
            </tr>
            """

        bloques.append(f"""
        <tr>
          <td style="padding:20px 0 6px;">
            <div style="color:#00AEEF; font-weight:800; font-size:13px; text-transform:uppercase; letter-spacing:1px; border-bottom:2px solid #00AEEF; padding-bottom:6px;">
              {titulo_categoria}
            </div>
          </td>
        </tr>
        <tr><td><table width="100%" cellpadding="0" cellspacing="0">{filas}</table></td></tr>
        """)

    return f"""
    <html>
    <body style="margin:0; padding:0; background:#F3F4F6; font-family:Arial, sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#F3F4F6; padding:20px 0;">
        <tr>
          <td align="center">
            <table width="600" cellpadding="0" cellspacing="0" style="background:white;">
              <tr>
                <td style="background:#0B3D91; padding:20px 24px;">
                  <span style="color:white; font-weight:900; font-size:22px;">NEXO</span>
                  <span style="color:#C7D8F5; font-size:12px; margin-left:10px;">Información que conecta — {fecha}</span>
                </td>
              </tr>
              <tr>
                <td style="padding:0 24px 20px;">
                  {''.join(bloques)}
                </td>
              </tr>
              <tr>
                <td style="background:#111827; padding:16px 24px; color:#9CA3AF; font-size:11px;">
                  Recibís este correo porque te suscribiste en Nexo (ramendivil65-byte.github.io/Nexo).
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """


def main():
    if not BREVO_API_KEY:
        print("Falta la variable de entorno BREVO_API_KEY.", file=sys.stderr)
        sys.exit(1)

    news_path = Path(__file__).resolve().parent.parent / "news.json"
    with open(news_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    html = armar_html(data)
    fecha_asunto = datetime.now().strftime("%d/%m")

    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
    }

    # 1) Crear la campaña
    campana = {
        "name": f"Nexo - Resumen del día {fecha_asunto}",
        "subject": f"📰 Las noticias de hoy en Nexo ({fecha_asunto})",
        "sender": {"name": REMITENTE_NOMBRE, "email": REMITENTE_EMAIL},
        "type": "classic",
        "htmlContent": html,
        "recipients": {"listIds": [LISTA_SUSCRIPTORES_ID]},
    }

    resp = requests.post(
        "https://api.brevo.com/v3/emailCampaigns",
        headers=headers,
        json=campana,
        timeout=30,
    )
    resp.raise_for_status()
    campaign_id = resp.json()["id"]
    print(f"Campaña creada (id {campaign_id})", flush=True)

    # 2) Mandarla ya mismo
    resp2 = requests.post(
        f"https://api.brevo.com/v3/emailCampaigns/{campaign_id}/sendNow",
        headers=headers,
        timeout=30,
    )
    resp2.raise_for_status()
    print("Newsletter enviado.", flush=True)


if __name__ == "__main__":
    main()

