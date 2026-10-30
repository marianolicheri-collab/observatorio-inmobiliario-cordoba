# Relevamiento general de Córdoba Capital — La Voz

Fuente: API pública de búsqueda por venta de inmuebles de Córdoba Capital. La consulta devuelve páginas con tipologías mezcladas, no necesita buscar barrio por barrio ni abrir cada ficha.

- Consulta: `https://clasificados.lavoz.com.ar/api/search?page=1&filters=tid%3A6330%20ss_operacion%3AVenta%20tid_location_should%3A3194`
- Última prueba realizada 30/10/2026: el portal declaró 16.814 resultados, 701 páginas de 24. **No son 16.814 propiedades únicas comprobadas**.
- Tanda creada: `observatorio.tandas.clave = cordoba_capital_venta_general_20261030`.
- Páginas 1 y 2 recogidas y normalizadas con origen `api_search_capital_general`: 48 avisos guardados, 45 habilitados para precio declarado y 3 pendientes. Barrio se lee del `address.neighborhood` del API, **no del filtro**. Los 48 originales se conservan; superficie `total_area` no habilita USD/m² sin base comprobada.
- **No publicar** la tanda general hasta comprobar muestras, cobertura y duplicados entre relevamientos.
- Al recolectar más páginas, no sobrescribir avisos ni revisiones previas por ID; conservar páginas de origen y registrar contradicciones.
- El scraper general se ejecuta **manualmente**, usa caché y respeto de las restricciones del portal. No debe ejecutarse desde el dashboard.
- En esta prueba la fuente se recuperó mediante un servicio de acceso al contenido. El script local de recolección se probó a nivel de parser, pero no la extracción directa completa desde su propio entorno: la conexión directa al dominio estaba bloqueada.

Advertencias específicas: La Voz devuelve un aviso con título de alquiler en los resultados de venta, otro sin precio USD válido y un posible anuncio de varias casas. No habilitarlos automáticamente. La descripción del listado aporta información sustancial y permite evitar fichas.

Para próximas tandas, archivar la respuesta original comprimida en `observatorio.recepciones.original_comprimido` cuando el acceso lo permita. La presente carga inicial guardó título, descripción, origen, URL y página en `avisos`, **no el JSON bruto de ambas páginas en recepciones**.
