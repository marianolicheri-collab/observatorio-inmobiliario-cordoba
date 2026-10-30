# Actualización de criterio (30/10/2026)

**IMPORTANTE:** la depuración habitual ahora es documental automática sobre los datos efectivamente publicados y se rige por [SYSTEM_PROMPT_OBSERVATORIO_V3.md](../SYSTEM_PROMPT_OBSERVATORIO_V3.md). La selección por la búsqueda original no determina el barrio. Las reglas `observatorio.datos_declarados_v2` habilitan precios declarados aptos sin abrir cada ficha. La vista `observatorio.inventario_analisis_v2` reúne todos los avisos por ID único y conserva pendientes.

**El siguiente script es opcional para EXCEPCIONES**, no el proceso obligatorio de todos los avisos. La vista `observatorio.cola_depuracion_v1` es una cola heredada del enfoque anterior y sus prioridades no deben interpretarse como que cada anuncio requiere ficha individual.

# Depuración de fichas La Voz por lotes

Proceso independiente del dashboard. **No se ejecuta automáticamente al abrirlo**.

## Requisitos

Python 3.10+, `pip install 'psycopg[binary]' beautifulsoup4`. Configurar de forma privada `OBSERVATORIO_DATABASE_URL` (acceso PostgreSQL autorizado a esquema `observatorio`). No subir credenciales ni caché al repositorio. Solo si se requiere usar Firecrawl, configurar `FIRECRAWL_API_KEY` y controlar los créditos.

## Ejecutar

```bash
# Simulación, sin modificar Supabase
python scripts/depurar_lote_lavoz.py --max 10 --provider html

# Si HTML público no ofrece la ficha estructurada, utilizar Firecrawl excepcionalmente
python scripts/depurar_lote_lavoz.py --max 10 --provider firecrawl

# Validar y registrar las fichas preparadas
python scripts/depurar_lote_lavoz.py --max 10 --provider firecrawl --apply
```

`--max` acepta 1–50. El sistema lee `observatorio.cola_depuracion_v1` (prioridad P2), recupera cada URL desde la caché o el proveedor escogido, extrae campos de la ficha y envía el lote a `observatorio.procesar_fichas_lote_v1`. La función verifica URL original, barrio, operación y precio, guarda evidencia y deja pendientes los conflictos. No toca `observatorio.publicacion`.

La caché es local en `.cache/lavoz-fichas` y evita consultas repetidas. Con 50 anuncios nuevos puede haber **50 consultas externas**; una única llamada se refiere a la validación en Supabase, no a la extracción. Nunca dar por confirmada una superficie sin base clara, ni incluir duplicados sin comprobar.

**Situación:** el script quedó guardado en GitHub, pero no hay un servicio de ejecución programada ni credenciales configuradas para ejecutarlo desde este repositorio. La función SQL ya se probó con ocho fichas reales en una operación. La ejecución completa desde el script requiere una prueba desde un entorno con acceso a la base y al portal.
