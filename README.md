# El Cercho Backend

Backend FastAPI async para el panel y la landing de El Cercho.

## Arranque

1. Copia `backend/.env.example` a `backend/.env`.
2. Ajusta `JWT_SECRET_KEY` y contraseñas seed.
3. Ejecuta desde la raíz del repo:

```bash
docker-compose up --build
```

La API queda en `http://localhost:8000`, con healthcheck en `/health`.

## Decisiones

- Refresh tokens: se guardan en Postgres para auditar familias, revocación y reutilización. Redis queda para rate limiting, cache de dashboard y contadores volátiles.
- `DataContext`: el frontend conserva su interfaz pública para evitar reescribir pantallas; por debajo sincroniza con la API.
- Landing: consume catálogo y blog en runtime con fallback estático para no dejar la web vacía si la API no está disponible en desarrollo. Para SEO estricto, el siguiente paso sería SSR/SSG.
- Contadores Redis/Postgres: el modelo deja `consultations` y `views` en Postgres como fuente visible. Redis está preparado para cache/contadores; en esta fase se invalida cache al escribir y no se agrega sincronización periódica compleja.
- Bulk update de insumos: se procesa síncrono porque el volumen actual del panel es pequeño. Celery ya existe para moverlo a background cuando el catálogo crezca.

## Variables

Ver `backend/.env.example`: DB, Redis, Celery, CORS, JWT, Sentry y email son configurables por entorno. `SENTRY_DSN` vacío deshabilita Sentry.

## Auth/RBAC

Roles:
- `Super Admin`: todos los permisos.
- `Editor de Contenido`: categorías, productos y blog; lectura de usuarios.
- `Ventas`: cotizaciones y lectura de usuarios.

Credenciales seed por defecto: `hugo@elcercho.mx` / `Admin123!`.

