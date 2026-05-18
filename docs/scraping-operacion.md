# Scraping De Propiedades

Guia rapida para ejecutar el scraping manual, revisar si termino y verificar datos en Postgres.

## Scraping Automatico

El proyecto tiene `celery_beat` configurado para ejecutar el inventario de propiedades automaticamente todos los dias a las `03:00 AM` hora Colombia.

El inventario no solo consulta la ciudad completa. Tambien consulta barrios principales de Cartagena y Barranquilla para evitar que los portales devuelvan solo el primer lote de resultados de una busqueda muy amplia.

Servicios involucrados:

- `celery_beat`: programa la tarea diaria.
- `celery_worker`: ejecuta los spiders.
- `postgres`: guarda las propiedades.

## Ejecutar Scraping Manual

Desde la raiz del proyecto:

```bash
docker compose exec celery_worker celery -A app.tasks.celery_app.celery call app.tasks.scraping_tasks.refresh_property_inventory
```

El comando devuelve un ID de tarea parecido a:

```text
6cc59907-f8df-460c-a02f-adb62e9f3140
```

Ese ID confirma que la tarea fue enviada al worker.

## Controlar Profundidad Del Scraping

Variables disponibles en `.env` o en la terminal antes de levantar Docker:

```text
SCRAPER_MAX_PAGES=40
SCRAPER_ZONE_MAX_PAGES=3
MISSING_INACTIVE_THRESHOLD=3
```

Significado:

- `SCRAPER_MAX_PAGES`: paginas maximas para la busqueda amplia por ciudad.
- `SCRAPER_ZONE_MAX_PAGES`: paginas maximas por cada barrio.
- `MISSING_INACTIVE_THRESHOLD`: cantidad de scrapes consecutivos en los que una propiedad debe faltar antes de marcarse como `inactive`.

Si quieres intentar traer mas resultados, sube `SCRAPER_ZONE_MAX_PAGES`, por ejemplo:

```text
SCRAPER_ZONE_MAX_PAGES=5
```

Luego reinicia Celery:

```bash
docker compose restart celery_worker celery_beat
```

## Saber Si El Scraping Sigue Activo

```bash
docker compose exec celery_worker celery -A app.tasks.celery_app.celery inspect active
```

Si sigue corriendo, veras algo como:

```text
* {'id': '...', 'name': 'app.tasks.scraping_tasks.refresh_property_inventory', ...}
```

Si ya termino, veras:

```text
- empty -
```

## Ver Logs Del Scraping

```bash
docker compose logs -f celery_worker
```

Cuando termina correctamente, debe aparecer algo parecido a:

```text
Task app.tasks.scraping_tasks.refresh_property_inventory[...] succeeded
```

Si falla, busca mensajes como:

```text
ERROR
raised unexpected
```

## Ver Cuantos Datos Entraron

```bash
docker compose exec postgres psql -U urbanest -d urbanest -c "SELECT city, operation, status, source, COUNT(*) FROM properties GROUP BY city, operation, status, source ORDER BY city, operation, status, source;"
```

Esto muestra conteos por ciudad, operacion, estado y fuente.

## Ver Las Ultimas Propiedades Guardadas

```bash
docker compose exec postgres psql -U urbanest -d urbanest -c "SELECT id, city, operation, status, source, price, left(title, 80) AS title FROM properties ORDER BY last_seen_at DESC LIMIT 20;"
```

## Vaciar Propiedades Y Volver A Scrappear

Usar solo si quieres borrar el inventario actual.

```bash
docker compose exec postgres psql -U urbanest -d urbanest -c "TRUNCATE TABLE properties, search_queries, scraping_jobs RESTART IDENTITY CASCADE;"
```

Luego lanza el scraping manual:

```bash
docker compose exec celery_worker celery -A app.tasks.celery_app.celery call app.tasks.scraping_tasks.refresh_property_inventory
```

## Abrir PgAdmin

URL:

```text
http://localhost:5050
```

Credenciales:

```text
Email: admin@urbanest.dev
Password: urbanest
```

Conexion a Postgres desde pgAdmin:

```text
Host: postgres
Port: 5432
Database: urbanest
Username: urbanest
Password: urbanest
```

## Notas

- Si `inspect active` muestra `empty`, el scraping ya termino o no hay tarea corriendo.
- Si la tabla `properties` queda vacia, revisa `docker compose logs -f celery_worker`.
- El warning de SQLAlchemy sobre tipo `vector` no es necesariamente un error; Postgres si reconoce `pgvector`.
- Los inmuebles desaparecidos del portal no se marcan como `inactive` inmediatamente. Primero sube `missing_count`.
- Si una propiedad vuelve a aparecer, queda `active` y `missing_count` vuelve a `0`.
- Por defecto una propiedad se marca como `inactive` despues de faltar en `3` scrapes confiables consecutivos.
- Para evitar falsos inactivos, el sistema no marca masivamente como `inactive` si una fuente devolvio muy pocos resultados frente a lo que ya habia activo.


## Extra
- Para monitorear:
    docker compose exec celery_worker celery -A app.tasks.celery_app.celery inspect active

- Para ver conteos:
    docker compose exec postgres psql -U urbanest -d urbanest -c "SELECT city, operation, source, COUNT(*) FROM properties WHERE status='active' GROUP BY city, operation, source ORDER BY city, operation, source;"

- Ahora puedes lanzar por separado:
    docker compose exec celery_worker celery -A app.tasks.celery_app.celery call app.tasks.scraping_tasks.refresh_property_inventory --kwargs='{"city":"Cartagena","operation":"rent"}'

    docker compose exec celery_worker celery -A app.tasks.celery_app.celery call app.tasks.scraping_tasks.refresh_property_inventory --kwargs='{"city":"Cartagena","operation":"sale"}'
    
- O todo completo:
    docker compose exec celery_worker celery -A app.tasks.celery_app.celery call app.tasks.scraping_tasks.refresh_property_inventory