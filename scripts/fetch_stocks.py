#!/usr/bin/env python3
"""
Trae cotizaciones reales de acciones vía Twelve Data (gratis, con API key) y
arma el top 5 que más sube y el top 5 que más baja, tanto para acciones
argentinas (ADRs que cotizan en Nueva York) como para el Dow Jones.

Se ejecuta cada cierto tiempo vía GitHub Actions y genera /stocks.json,
que el sitio lee para mostrar los gráficos de barras.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

API_KEY = os.environ.get("TWELVE_DATA_API_KEY")

# ADRs argentinos que cotizan en Nueva York (no hay una API gratis confiable
# para las acciones directamente en pesos de la Bolsa de Buenos Aires).
ACCIONES_ARGENTINAS = [
    "YPF", "GGAL", "PAM", "BMA", "TX", "BBAR", "SUPV", "CRESY", "TEO", "LOMA",
]

# Una selección amplia de componentes del Dow Jones, para elegir el top 5
# de subas y bajas entre ellos (no son solo 5 fijas).
ACCIONES_DOW_JONES = [
    "AAPL", "MSFT", "JPM", "KO", "NVDA", "CAT", "HD", "MCD", "V", "DIS",
    "GS", "IBM", "CVX", "WMT", "PG", "UNH", "AXP", "HON", "AMGN", "CSCO",
]

REQUEST_TIMEOUT = 20


def traer_cotizaciones(simbolos: list) -> list:
    """Pide varias acciones juntas en un solo pedido a la API."""
    symbols_str = ",".join(simbolos)
    url = f"https://api.twelvedata.com/quote?symbol={symbols_str}&apikey={API_KEY}"

    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        print(f"  ! Error pidiendo cotizaciones: {exc}", file=sys.stderr)
        return []

    # Si pedís un solo símbolo, la API devuelve un objeto directo en vez de
    # una lista con uno adentro. Si pedís varios, devuelve {simbolo: {...}}.
    resultados = []
    if isinstance(data, dict) and "symbol" in data:
        data = {simbolos[0]: data}

    if not isinstance(data, dict):
        print(f"  ! Respuesta inesperada: {data}", file=sys.stderr)
        return []

    for simbolo, info in data.items():
        if not isinstance(info, dict) or "percent_change" not in info:
            print(f"  ! {simbolo} sin percent_change, respuesta: {info}", file=sys.stderr)
            continue
        try:
            resultados.append(
                {
                    "simbolo": simbolo,
                    "porcentaje": float(info["percent_change"]),
                }
            )
        except (TypeError, ValueError):
            continue

    return resultados


def armar_top5_subas_bajas(cotizaciones: list) -> dict:
    ordenadas = sorted(cotizaciones, key=lambda x: x["porcentaje"], reverse=True)
    subas = [c for c in ordenadas if c["porcentaje"] > 0][:5]
    bajas = sorted(
        [c for c in ordenadas if c["porcentaje"] < 0],
        key=lambda x: x["porcentaje"],
    )[:5]
    return {"subas": subas, "bajas": bajas}


def main():
    if not API_KEY:
        print("Falta la variable de entorno TWELVE_DATA_API_KEY.", file=sys.stderr)
        sys.exit(1)

    print("Trayendo acciones argentinas (ADRs)...")
    cotiz_argentinas = traer_cotizaciones(ACCIONES_ARGENTINAS)
    print(f"  {len(cotiz_argentinas)} cotizaciones recibidas")

    print("Trayendo acciones del Dow Jones...")
    cotiz_dow = traer_cotizaciones(ACCIONES_DOW_JONES)
    print(f"  {len(cotiz_dow)} cotizaciones recibidas")

    data = {
        "actualizado": datetime.now(timezone.utc).isoformat(),
        "merval": armar_top5_subas_bajas(cotiz_argentinas),
        "dowjones": armar_top5_subas_bajas(cotiz_dow),
    }

    salida = Path(__file__).resolve().parent.parent / "stocks.json"
    salida.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Listo: {salida}")


if __name__ == "__main__":
    main()
