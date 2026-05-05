# Urbanest IA / RentRadar AI

MVP local para buscar precios de inmuebles en arriendo en Cartagena, Colombia, a partir de consultas en lenguaje natural. La app centraliza resultados de scraping y fallbacks mock, analiza precios y presenta oportunidades de mercado en una interfaz tipo chat.

## Arquitectura

- Frontend: React + Vite + Tailwind CSS
- Backend: FastAPI
- IA local: Ollama
- Jobs: Celery + Redis
- Base de datos: PostgreSQL
- Scraping: Scrapy + Playwright con capa ética y fallback mock
- Orquestación: Docker Compose

## Estructura

```text
urbanest-ia/
  docker-compose.yml
  .env.example
  README.md
  frontend/
  backend/
  scraper/
  db/
```

## Requisitos

- Docker y Docker Compose
- Espacio para descargar un modelo de Ollama

## Levantar el proyecto

1. Crear el archivo `.env` a partir de `.env.example`.
2. Ejecutar:

```bash
docker compose up --build
```

3. Descargar el modelo en Ollama:

```bash
docker compose exec ollama ollama pull qwen2.5:3b
```

`qwen2.5:3b` queda como modelo recomendado por defecto para este MVP porque es bastante más liviano. Si quieres priorizar aún más velocidad, puedes probar `llama3.2:1b`; si quieres más calidad y tienes más RAM, puedes volver a `llama3.1`.

## Flujo del MVP

1. El usuario abre el frontend en `http://localhost:5173`.
2. Escribe una búsqueda en lenguaje natural.
3. FastAPI intenta estructurar la búsqueda con Ollama.
4. Si Ollama no responde, entra un parser de respaldo en Python.
5. Se crea un job de scraping.
6. Celery ejecuta el scraping ético o un fallback mock.
7. Los resultados se normalizan y se guardan en PostgreSQL.
8. El frontend consulta el estado del job y muestra el resumen.

## Endpoints

- `POST /api/chat`
- `GET /api/properties`
- `GET /api/properties/search`
- `GET /api/jobs/{id}`

## Ejemplo de uso

```json
POST /api/chat
{
  "message": "busca apartamentos en arriendo en Manga entre 1.5 y 2.5 millones, con 2 habitaciones"
}
```

Respuesta inicial:

```json
{
  "reply": "Entendí tu búsqueda y empecé a rastrear opciones.",
  "parsed_query": {
    "city": "Cartagena",
    "zone": "Manga",
    "property_type": "apartamento",
    "price_min": 1500000,
    "price_max": 2500000,
    "bedrooms": 2,
    "bathrooms": null,
    "keywords": ["arriendo"]
  },
  "results": [],
  "job_id": 1
}
```

## Limitaciones del MVP

- El scraping real de portales puede cambiar por estructura HTML, robots.txt o bloqueos.
- Facebook Marketplace queda preparado con Playwright mock, sin automatizar login ni evasión.
- Por defecto el sistema usa fallback mock para garantizar una demo local funcional.
- La detección de oportunidades es heurística y debe refinarse con más datos históricos.

## Nota ética y legal sobre scraping

- Se revisa `robots.txt` antes de iniciar scraping real.
- Se respetan delays y límites básicos.
- No se intentan evadir captchas, logins o protecciones.
- Solo se almacenan datos públicos del anuncio.
- Facebook Marketplace queda en modo mock/preparado para desarrollo responsable.

## Sugerencias de mejora

- Añadir histórico de precios por inmueble.
- Incorporar rankings por barrio y alertas.
- Agregar panel comparativo por fuente.
- Persistir conversaciones y búsquedas por usuario.
