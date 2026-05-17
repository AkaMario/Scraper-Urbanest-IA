# Normalizacion de ubicaciones en Cartagena

## Objetivo

La busqueda debe interpretar barrios de Cartagena con un nombre canonico. Si el usuario pide un barrio especifico, por ejemplo `olaya`, primero se intentan devolver solo inmuebles de `Olaya Herrera`. Solo cuando no hay resultados exactos se amplia la busqueda a barrios cercanos definidos por el backend.

## Como se logro

Se creo el archivo interno `backend/app/services/cartagena_locations.py` con tres piezas:

- `NEIGHBORHOOD_ALIASES`: convierte alias y nombres cortos a un barrio canonico. Ejemplo: `olaya` y `olaya herrera` se normalizan a `Olaya Herrera`.
- `NEARBY_NEIGHBORHOODS`: mapa interno de cercania entre barrios. Ejemplo: `Olaya Herrera` puede ampliar a `La Maria`, `La Esperanza`, `El Pozon` y `Zaragocilla`.
- Funciones de apoyo para normalizar texto sin tildes y obtener barrios cercanos.

El parser (`backend/app/services/query_parser.py`) ahora usa ese mapa para detectar mas barrios y guardar la zona canonica en `zone` y `neighborhood`.

El procesamiento del scraping (`backend/app/tasks/scraping_tasks.py`) sigue este orden:

1. Busca y filtra por el barrio exacto pedido.
2. Si hay resultados exactos, guarda solo esos resultados.
3. Consulta en paralelo el barrio exacto y los barrios cercanos definidos en el mapa interno.
4. Si hay resultados exactos, guarda solo esos resultados.
5. Si no hay exactos pero si cercanos, guarda el primer barrio cercano con resultados y marca `location_match_scope=nearby` en la busqueda interna.

El normalizador (`scraper/normalizer.py`) tambien compara contra zonas aceptadas para que, cuando se active el fallback, los resultados cercanos no sean descartados por el filtro del barrio original.

La respuesta final (`backend/app/ollama_client.py`) avisa cuando la busqueda fue ampliada a barrios cercanos, en vez de presentarlos como si fueran del barrio exacto.

## Visibilidad del mapa

El mapa vive solo en codigo backend. No se expone en endpoints publicos ni en componentes del frontend. La interfaz solo recibe los resultados finales y el resumen de la busqueda.

## Dificultades

- Las fuentes inmobiliarias no siempre reportan el barrio con el mismo nombre que usa el usuario. Un anuncio puede decir `Olaya`, `Olaya Herrera` o traer una subzona.
- Algunos barrios tienen nombres compuestos o alias comunes. Por eso se normaliza texto quitando tildes, signos y diferencias de mayusculas.
- Si se filtra demasiado fuerte por barrio exacto, se pierden anuncios validos. Si se filtra demasiado amplio, se mezclan barrios no solicitados. La solucion separa el flujo exacto del fallback cercano.
- El fallback a cercanos aumenta el costo de scraping porque ejecuta consultas adicionales. Para evitar respuestas muy lentas, las consultas de barrio exacto y cercanos se ejecutan en paralelo y luego se priorizan los resultados exactos.
