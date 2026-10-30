#!/usr/bin/env python3
"""Extrae datos DECLARADOS de tarjetas La Voz ya descargadas, sin visitar fichas.
Uso: python scripts/extraer_listado_lavoz.py pagina.md > tarjetas.jsonl
El script no consulta Internet ni Supabase; usar la salida para ingesta controlada.
"""
import json
import re
import sys

URL = r"https://clasificados\.lavoz\.com\.ar/avisos/inmuebles/(?:departamento|casa|ph|duplex|terreno)/\d+/[^)\s]+"
CARD = re.compile(
    r"\[([^\]\n]{4,250})\]\((" + URL + r")\)\s*\n+"
    r"\s*(U\$S\s*[\d.]+|\$\s*[\d.]+|a consultar)",
    re.IGNORECASE,
)
ROOM = re.compile(r"(\d+)\s*dorm\.", re.IGNORECASE)
BATH = re.compile(r"(\d+)\s*bañ", re.IGNORECASE)
AREA = re.compile(r"(\d+(?:[.,]\d+)?)\s*m²", re.IGNORECASE)
ID = re.compile(r"/inmuebles/([^/]+)/(\d+)/")

def extract(markdown):
    # Quitar barra lateral de filtros: procesar solamente las tarjetas de resultados.
    body = markdown.split("Ver listaVer grilla", 1)[-1]
    records = {}
    for match in CARD.finditer(body):
        title, url, price_str = match.groups()
        id_match = ID.search(url)
        if not id_match:
            continue
        tipo, ident = id_match.groups()
        # La ficha incluye su descripción y anunciante antes del siguiente aviso.
        trailing = body[match.end():match.end() + 120]
        rooms = ROOM.search(trailing)
        bathrooms = BATH.search(trailing)
        area = AREA.search(trailing)
        currency = "USD" if price_str.upper().startswith("U$S") else ("ARS" if price_str.startswith("$") else None)
        amount = int(re.sub(r"\D", "", price_str)) if currency else None
        surface = float(area.group(1).replace(",", ".")) if area else None
        flags = []
        if currency == "ARS":
            flags.append("precio_ars_verificar_operacion_y_moneda")
        if amount is None:
            flags.append("sin_precio")
        if surface is None:
            flags.append("sin_superficie")
        elif surface > 1000 or surface <= 10:
            flags.append("superficie_atipica_no_usable")
        records[ident] = {
            "fuente": "lavoz", "id_fuente": ident, "url": url,
            "titulo": title.replace(r"\|", "|"), "tipologia_categorizada": tipo,
            "moneda_publicada": currency, "precio_publicado": amount,
            "dormitorios_declarados": int(rooms.group(1)) if rooms else None,
            "banos_declarados": int(bathrooms.group(1)) if bathrooms else None,
            "superficie_declarada_m2": surface,
            "base_superficie": None,  # El listado no identifica cubierta vs. total.
            "estado": "pendiente",
            "advertencias": flags,
        }
    return list(records.values())

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Uso: extraer_listado_lavoz.py pagina.md")
    with open(sys.argv[1], encoding="utf-8") as handle:
        for item in extract(handle.read()):
            print(json.dumps(item, ensure_ascii=False))
