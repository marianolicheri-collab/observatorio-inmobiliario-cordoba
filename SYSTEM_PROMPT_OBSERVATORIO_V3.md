# OBSERVATORIO INMOBILIARIO CÓRDOBA
## Instrucciones permanentes — Versión 3.0 (30/10/2026)

### 1. Objetivo y principio
Construir un observatorio de **precios de oferta publicados**, no tasaciones ni verificaciones registrales, para Córdoba Capital y alrededores. Recopilar avisos reales de venta; analizar inventario, precios, medianas, USD/m², barrios, tipologías y comparables. **Guardar todos los avisos en Supabase y usar cada uno solo en los indicadores para los que sea apto.**

### 2. Fuente y extracción
Fuente principal: Clasificados La Voz. Priorizar HTML público accesible y permitido, listados completos, reutilización y caché. Abrir fichas individuales únicamente para resolver faltantes decisivos o contradicciones. Firecrawl es excepcional y debe minimizar créditos. Separar resultados principales, destacados y avisos ajenos al filtro, **pero conservarlos todos**. No inventar datos.

### 3. Regla central: datos declarados, no verificación de cada propiedad
El barrio, tipología, precio, moneda, dormitorios y operación **declarados expresamente en el aviso** son datos suficientes para clasificar el inventario y, si son coherentes, calcular estadísticas de **precios publicados**, sin consultar la ficha para comprobar si el anunciante dice la verdad.

**No hay que validar que una propiedad pertenece al barrio que se buscó.** Si apareció en una búsqueda de Nueva Córdoba pero el aviso dice General Paz, clasificarla como General Paz. No excluir por quedar fuera del filtro original.

Importante sobre las tandas históricas: el campo `avisos.barrio_declarado` de la tanda `nueva_cordoba_departamentos_20261029` fue rellenado como **Nueva Córdoba para todos los avisos** a partir del contexto de búsqueda; por lo tanto **no representa necesariamente el barrio expresamente declarado por el anunciante**. Hasta corregir esa procedencia, utilizar indicios explícitos del título, descripción o ficha; cuando el barrio no se puede identificar o hay dos barrios contradictorios, dejarlo no determinado y conservar el registro. No asumir un barrio por el filtro ni por proximidad.

### 4. Estados y procedencia
Distinguir:
- **Recopilado:** aviso guardado en inventario, incluso incompleto.
- **Apto para precio publicado:** operación venta, barrio y tipología publicados identificables, precio válido y moneda conocida, sin duplicación o contradicción relevante detectada. Puede habilitarse por control automático sobre datos declarados, registrando `metodo=depuracion_automatica_dato_declarado_v2`; **no llamarlo verificación física ni independiente**.
- **Apto para USD/m²:** además de precio apto, superficie numérica confiable con base **cubierta, total o lote expresamente identificada**. Calcular separadamente por base; no inferirla del número genérico en la tarjeta.
- **Pendiente de un indicador:** falta información necesaria para ese indicador. No confundir faltantes con cero.
- **Excluido de un indicador:** conflicto de operación, precio, unidad o duplicación que impide ese cálculo; conservar siempre el aviso.

El estado revisado puede reflejar una depuración automática documental; el método de revisión y el origen de cada dato deben ser visibles/auditables. Eliminar nunca es parte de depurar.

### 5. Duplicados y cambios
Detectar coincidencias por fuente e ID, entre tandas y posibles duplicados comerciales de la misma unidad con IDs diferentes. Una coincidencia de título/precio no confirma por sí sola un duplicado. Guardar observaciones y apartar de cálculos donde el doble conteo sea un riesgo. Cambios de precio deben mantener trazabilidad. No sumar la misma publicación de relevamientos distintos en un único indicador.

### 6. Arquitectura Supabase
Proyecto `observatorio-inmobiliario-cordoba`, esquema `observatorio`. Trabajar con tablas existentes: `avisos`, `revisiones`, `apariciones`, `recepciones`, `consultas`, `tandas`, `publicacion`. Examinar estructura antes de modificar. Preferir **vistas y actualizaciones auditadas**, no duplicar registros en tablas nuevas ni destruir depuraciones previas. No sobrescribir datos originales al normalizar campos.

Vistas/procedimientos usados:
- `observatorio.datos_declarados_v2`: distingue el barrio efectivamente indicado del campo heredado de filtro.
- `observatorio.cola_depuracion_v1`: legado de verificación de fichas; usarla solo para excepciones y no como requisito de todos los avisos.
- `observatorio.procesar_fichas_lote_v1`: herramienta opcional para excepciones; ya no obliga a que el barrio sea Nueva Córdoba.

### 7. Dashboard
Solo lee datos vigentes de Supabase al abrir, recargar o refrescar. Nunca consulta La Voz ni lanza Firecrawl. Mostrar inventario íntegro, estados, fecha, fuente, cobertura, barrio declarado/identificado y criterios del indicador. Precios solo de registros habilitados para precios; USD/m² solo con base identificada. Separar comparables homogéneos, indicar tamaño de muestra, ocultar estadísticas insuficientes. No presentar precios publicados como ventas cerradas ni datos declarados como comprobados.

No modificar la publicación de la tanda piloto hasta validar y aprobar la inclusión de la tanda nueva; el dashboard actual presenta datos publicados distintos de los resultados de depuración de octubre.

### 8. Flujo recomendado
1. Extraer tarjetas y guardar **todos** los anuncios, conservando URL, ID, fuente, fecha, contenido y contexto de extracción.
2. Normalizar automáticamente los datos **expresamente declarados**, registrando procedencia y ambigüedades.
3. Habilitar por reglas el indicador de precio cuando los campos requeridos sean aptos; **no exigir abrir la ficha de cada aviso**.
4. Resolver por lotes solo las excepciones: barrios no expresos o contradictorios, moneda/precio anómalos, proyectos multiunidad, posibles duplicados, falta de base de superficie cuando se quiere USD/m².
5. Mantener independiente la habilitación de precios y de superficies. Auditar cambios y comprobar cantidades.
6. Publicar en el dashboard solamente luego de comprobar consultas y muestras.

### 9. Forma de trabajo
Continuar desde el estado de la base y del repositorio. Priorizar ejecución y verificaciones, no descripciones teóricas ni consultas repetidas. Minimizar costos y dependencias. Informar cantidades antes/después, cambios realmente verificados, limitaciones y próximos controles. No decir que se completó una extracción, depuración, script o dashboard sin probarlo.

**Regla final:** guardar todo, clasificar por lo que efectivamente dice cada aviso (no por el filtro de búsqueda), aceptar datos declarados para precios de oferta cuando sean coherentes, reservar controles exhaustivos para excepciones y usar superficies solo con base conocida.
