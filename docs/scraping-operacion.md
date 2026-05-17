# Scraping De Propiedades

Guia rapida para ejecutar el scraping manual, revisar si termino y verificar datos en Postgres.

## Scraping Automatico

El proyecto tiene `celery_beat` configurado para ejecutar el inventario de propiedades automaticamente todos los dias a las `03:00 AM` hora Colombia.

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
- Los inmuebles desaparecidos del portal se marcan como `inactive` cuando el refresco diario encuentra datos para esa fuente y ciudad.
