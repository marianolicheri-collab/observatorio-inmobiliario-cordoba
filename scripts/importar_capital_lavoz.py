#!/usr/bin/env python3
"""Importar un lote JSON local de La Voz a Supabase, sin consultas web.
Uso: OBSERVATORIO_DATABASE_URL=... python scripts/importar_capital_lavoz.py --page 12 --json pagina12.json
Requiere: pip install 'psycopg[binary]'
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path

TANDA = "cordoba_capital_venta_general_20261030"
CONSULTA = "capital_venta_general"

def normalizar(payload):
    result = payload["data"]["results"]
    rows = []
    for pos, a in enumerate(result["data"]):
        price = a.get("price") or {}
        address = a.get("address") or {}
        estate = a.get("real_estate") or {}
        rawprice = str(price.get("amount") or "").replace(".", "").replace(",", ".")
        try:
            amount = float(rawprice) if rawprice else None
        except ValueError:
            amount = None
        if not str(a.get("url", "")).startswith("https://clasificados.lavoz.com.ar/avisos/"):
            raise ValueError("URL de aviso ajena al dominio de La Voz")
        rows.append({
            "id": str(a["id"]), "url": a["url"], "title": a.get("title"),
            "body": a.get("body"), "province": address.get("province"),
            "city": address.get("city"), "neighborhood": address.get("neighborhood"),
            "type": (a.get("subcategory") or {}).get("name"),
            "operation": (a.get("third_level") or {}).get("name"),
            "currency": {"U$S":"USD","$":"ARS"}.get(price.get("currency")),
            "price": amount, "date": a.get("publish_date"),
            "extra": {"origen":"api_search_capital_general",
                      "posicion":pos, "barrio_origen":"api.address.neighborhood",
                      "dormitorios_texto_api":estate.get("number_bedrooms"),
                      "banos_texto_api":estate.get("number_bathrooms"),
                      "superficie_generica_api_m2":estate.get("total_area"),
                      "base_superficie":"no_identificada",
                      "apto_credito_api":estate.get("apt_credit"),
                      "apto_escritura_api":estate.get("apt_deed"),
                      "anunciante_api":(a.get("user") or {}).get("trade_name"),
                      "destacado_api":(a.get("products") or {}).get("highlight")}
        })
    return rows, result

def importar(conn, page, raw, url):
    payload = json.loads(raw)
    rows, result = normalizar(payload)
    if int(result.get("current_page", -1)) != page:
        raise ValueError("La página recibida no coincide con la solicitada")
    if len(rows) > 24 or not rows:
        raise ValueError("Cantidad de registros inesperada")
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("ID duplicado dentro de la página")
    checksum = hashlib.sha256(raw).hexdigest()
    blob = gzip.compress(raw)
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("""select t.id,c.id from observatorio.tandas t
                join observatorio.consultas c on c.tanda_id=t.id
                where t.clave=%s and c.clave=%s""",(TANDA,CONSULTA))
            found = cur.fetchone()
            if not found:
                raise ValueError("No existe tanda o consulta general en Supabase")
            t_id,c_id = found
            inserted = 0
            for r in rows:
                extra = dict(r["extra"], pagina=page, descripcion_extraida=True)
                cur.execute("""insert into observatorio.avisos(
                    tanda_id,fuente,id_fuente,url,titulo,descripcion,
                    provincia_declarada,localidad_declarada,barrio_declarado,
                    tipologia_publicada,operacion_publicada,moneda_publicada,
                    precio_publicado,fecha_publicada_texto,caracteristicas_publicadas)
                    values (%s,'lavoz',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                    on conflict(tanda_id,id_fuente) do nothing returning id_fuente""",
                    (t_id,r["id"],r["url"],r["title"],r["body"],r["province"],
                    r["city"],r["neighborhood"],r["type"],r["operation"],
                    r["currency"],r["price"],r["date"],json.dumps(extra,ensure_ascii=False)))
                if cur.fetchone():
                    inserted += 1
                    cur.execute("""insert into observatorio.revisiones(tanda_id,id_fuente,estado,motivos)
                        values (%s,%s,'pendiente',%s::jsonb)
                        on conflict(tanda_id,id_fuente) do nothing""",
                        (t_id,r["id"],json.dumps([{"metodo":"ingesta_api_lavoz","pagina":page}])))
            cur.execute("""insert into observatorio.recepciones(
                tanda_id,consulta_id,pagina,url_origen,capturada_en,sha256,formato,original_comprimido)
                values (%s,%s,%s,%s,now(),%s,'gzip_json_utf8',%s)
                on conflict(consulta_id,pagina) do update set
                original_comprimido=excluded.original_comprimido,sha256=excluded.sha256
                returning id""",(t_id,c_id,page,url,checksum,blob))
            recepcion_id = cur.fetchone()[0]
            for pos,r in enumerate(rows):
                cur.execute("""insert into observatorio.apariciones(
                    recepcion_id,tanda_id,id_fuente,posicion)
                    values (%s,%s,%s,%s)
                    on conflict(recepcion_id,id_fuente) do nothing""",
                    (recepcion_id,t_id,r["id"],pos))
    return {"pagina":page,"encontrados":len(rows),"nuevos":inserted,
            "repetidos":len(rows)-inserted,"archivo_sha256":checksum}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--page",type=int,required=True)
    parser.add_argument("--json",required=True)
    parser.add_argument("--origin-url",default=None)
    args = parser.parse_args()
    dsn = os.environ.get("OBSERVATORIO_DATABASE_URL")
    if not dsn:
        parser.error("Falta OBSERVATORIO_DATABASE_URL")
    raw = Path(args.json).read_bytes()
    origin = args.origin_url or (
        "https://clasificados.lavoz.com.ar/api/search?page="
        +str(args.page)+"&filters=tid%3A6330%20ss_operacion%3AVenta%20tid_location_should%3A3194")
    import psycopg
    with psycopg.connect(dsn) as conn:
        print(json.dumps(importar(conn,args.page,raw,origin),ensure_ascii=False))

if __name__ == "__main__":
    main()
