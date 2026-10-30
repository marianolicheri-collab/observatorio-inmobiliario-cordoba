#!/usr/bin/env python3
"""Cola Supabase -> fichas La Voz -> validación por lotes. Ejecución MANUAL.
pip install 'psycopg[binary]' beautifulsoup4
OBSERVATORIO_DATABASE_URL obligatoria; FIRECRAWL_API_KEY solo con --provider firecrawl.
Sin --apply: simulación, no modifica revisiones.
"""
import argparse, hashlib, json, os, re, sys, time, urllib.request
from pathlib import Path

TANDA = "nueva_cordoba_departamentos_20261029"
BASE = "https://clasificados.lavoz.com.ar/avisos/inmuebles/departamento/"

def get_page(url, provider, timeout):
    if not url.startswith(BASE): raise ValueError("URL fuera de La Voz")
    if provider == "firecrawl":
        token = os.environ.get("FIRECRAWL_API_KEY")
        if not token: raise RuntimeError("Configurar FIRECRAWL_API_KEY")
        req = urllib.request.Request(
            "https://api.firecrawl.dev/v2/scrape",
            data=json.dumps({"url":url,"formats":["markdown"]}).encode(),
            headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=timeout) as f: data=json.load(f)
        if not data.get("success",False): raise RuntimeError("Extracción Firecrawl fallida")
        return data.get("data",{}).get("markdown","")
    req = urllib.request.Request(url,headers={"User-Agent":"ObservatorioCordoba/1.0","Accept":"text/html"})
    with urllib.request.urlopen(req,timeout=timeout) as f: html=f.read(3000000).decode("utf-8","replace")
    from bs4 import BeautifulSoup
    soup=BeautifulSoup(html,"html.parser")
    for x in soup(["script","style","nav","footer"]): x.decompose()
    title=soup.find("h1")
    if not title: raise RuntimeError("HTML sin ficha principal verificable")
    txt=soup.get_text("\n",strip=True)
    if "Descripción" not in txt: raise RuntimeError("HTML sin descripción verificable")
    # HTML heterogéneo: se procesa como texto; si faltan secciones, queda pendiente.
    return "# "+title.get_text(" ",strip=True)+"\n"+txt

def parse_ficha(markdown,row):
    title=re.search(r"^#\s+(.+)$",markdown,re.M)
    head=markdown.split("## Contactar al Anunciante")[0].split("## Datos del Anunciante")[0]
    price=re.search(r"U\$S\s*([\d.]+(?:,\d+)?)",head,re.I)
    f=re.search(r"## Características(.*?)(?=\n## Descripción|\Z)",markdown,re.S|re.I)
    d=re.search(r"^## Descripción\s*(.*?)(?=^## Ubicación|\Z)",markdown,re.S|re.I|re.M)
    feat=f.group(1) if f else ""
    desc=d.group(1).strip()[:15000] if d else ""
    def field(label):
        x=re.search(r"\b"+re.escape(label)+r"\s*:?\s*\n+([^\n]+)",feat,re.I)
        return x.group(1).strip() if x else None
    ttl=title.group(1).strip() if title else ""
    barrio=field("Barrio")
    tipo=(field("Tipo de Departamento") or "").lower()
    typ={"departamento":"departamento","piso":"piso","semipiso":"semipiso",
         "duplex":"duplex","dúplex":"duplex","triplex":"triplex","tríplex":"triplex"}.get(tipo)
    if re.search(r"\bd[uú]plex\b",ttl,re.I): typ="duplex"
    if re.search(r"\btr[ií]plex\b",ttl,re.I): typ="triplex"
    rooms=re.match(r"(\d+)\s+[Dd]orm",field("Cantidad de Dormitorios") or "")
    dorm=int(rooms.group(1)) if rooms else None
    if re.search(r"1\s*(?:y\s*medio|y\s*1/2|1/2)",ttl+" "+desc,re.I): dorm=None
    amount=price.group(1).replace(".","").replace(",",".") if price else None
    op="venta" if re.search(r"\b(venta|vende|vendo)\b",ttl+" "+desc,re.I) else None
    if barrio and not re.search(r"nueva\s+c[oó]rdoba|nva\.?\s*cba",ttl+" "+desc,re.I): barrio=None
    # Discrepancia de precios: no habilitar automáticamente.
    for other in re.findall(r"(?:precio|valor)\s*[:\-]?\s*(?:USD|U\$S|U\$D)\s*([\d.]+)",desc,re.I):
        if amount and float(other.replace(".","")) != float(amount): op=None
    # La base de superficie debe constar expresamente en descripción.
    base=None; surface=None
    for kind,pattern in [
        ("cubierta",r"superficie\s+cubierta\s*(?:de\s*|:\s*)?(\d+(?:[,.]\d+)?)\s*m"),
        ("total",r"superficie\s+total\s*(?:de\s*|:\s*)?(\d+(?:[,.]\d+)?)\s*m"),
        ("cubierta",r"(\d+(?:[,.]\d+)?)\s*m(?:²|2)?\s*cubiertos"),
        ("total",r"(\d+(?:[,.]\d+)?)\s*m(?:²|2)?\s*totales")]:
        m=re.search(pattern,desc,re.I)
        if m:
            n=float(m.group(1).replace(",","."))
            if 15<=n<=1000: base,surface=kind,n; break
    return dict(id_fuente=row["id_fuente"],url=row["url"],titulo_ficha=ttl,
                descripcion_ficha=desc,barrio_ficha=barrio,operacion_ficha=op,
                tipologia_ficha=typ,moneda_ficha="USD" if amount else None,
                precio_ficha=amount,dormitorios_ficha=dorm,
                base_superficie=base,superficie_ficha=surface)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tanda",default=TANDA)
    ap.add_argument("--max",type=int,default=10)
    ap.add_argument("--provider",choices=["html","firecrawl"],default="html")
    ap.add_argument("--apply",action="store_true")
    ap.add_argument("--cache-dir",default=".cache/lavoz-fichas")
    ap.add_argument("--sleep",type=float,default=1.0)
    args=ap.parse_args()
    if not 1<=args.max<=50 or args.sleep<0.5: ap.error("max 1-50 y sleep >= 0.5")
    dsn=os.environ.get("OBSERVATORIO_DATABASE_URL")
    if not dsn: ap.error("Falta OBSERVATORIO_DATABASE_URL")
    import psycopg
    cache=Path(args.cache_dir);cache.mkdir(parents=True,exist_ok=True)
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT id_fuente,url FROM observatorio.cola_depuracion_v1
                WHERE tanda=%s AND estado='pendiente'
                  AND cola_prioridad='P2_candidato_alta_evidencia_declarada'
                ORDER BY id_fuente DESC LIMIT %s""",(args.tanda,args.max))
            records=[{"id_fuente":x,"url":y} for x,y in cur.fetchall()]
        fichas=[]
        for row in records:
            path=cache/(hashlib.sha256(row["url"].encode()).hexdigest()+".md")
            try:
                if path.exists(): content=path.read_text(encoding="utf-8")
                else:
                    content=get_page(row["url"],args.provider,25)
                    path.write_text(content,encoding="utf-8")
                    time.sleep(args.sleep)
                fichas.append(parse_ficha(content,row))
                print("Ficha preparada:",row["id_fuente"],file=sys.stderr)
            except Exception as exc:
                print("Pendiente por error:",row["id_fuente"],str(exc),file=sys.stderr)
        if not fichas: return 1
        if args.apply:
            with conn.cursor() as cur:
                cur.execute("SELECT observatorio.procesar_fichas_lote_v1(%s,%s::jsonb)",
                            (args.tanda,json.dumps(fichas,ensure_ascii=False)))
                result=cur.fetchone()[0]
            conn.commit()
        else:
            result={"simulacion":True,"preparadas":len(fichas),"fichas":fichas}
            conn.rollback()
        print(json.dumps(result,ensure_ascii=False,indent=2,default=str))
    return 0

if __name__=="__main__": raise SystemExit(main())
