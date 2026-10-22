# Desplegar Olist en Coolify

La aplicación usa dos contenedores: `web` (React + Nginx, puerto interno 80)
y `dashboard` (Dash + Gunicorn, puerto interno 8050). PostgreSQL sigue en tu
proyecto de Supabase; este despliegue no crea otra base ni ejecuta migraciones.

## 1. Subir el código

Subir este proyecto completo a un repositorio Git al que tengas acceso de
escritura. Coolify necesita la versión que incluya `compose.coolify.yaml`,
ambos Dockerfiles y `frontend/package-lock.json`. Si usás el repositorio
original, los cambios locales deben estar subidos antes de desplegar.

`.env`, `.venv`, `node_modules` y los logs están excluidos de Git.
No subir el archivo `env` recibido ni sus credenciales.

## 2. Crear la aplicación

En tu proyecto y entorno de Coolify, agregar una aplicación desde el
repositorio Git, eligiendo la rama donde subiste los cambios.

| Ajuste | Valor |
| --- | --- |
| Build Pack / Build strategy | Docker Compose / Compose |
| Base Directory | `/` |
| Docker Compose Location | `/compose.coolify.yaml` |
| Servicio que recibe el dominio | `web` |
| Puerto interno del dominio | `80` |

Guardar y cargar la definición Compose. Este archivo contiene toda la
configuración del despliegue. No usar `compose.yaml` en Coolify:
ese archivo agrega el puerto local 8080 para Docker Desktop.
No es necesario configurar comandos de instalación o de build adicionales.

## 3. Configurar Supabase

En **Environment Variables**, cargar estos valores como variables de ejecución
(runtime), no de build. Usar los datos de conexión PostgreSQL de tu proyecto,
no la URL de la API de Supabase ni una clave `anon`/`service_role`.

| Variable | Valor |
| --- | --- |
| `DB_HOST` | Host de la conexión PostgreSQL |
| `DB_PORT` | Puerto indicado por Supabase, normalmente `5432` |
| `DB_NAME` | Base indicada por Supabase, normalmente `postgres` |
| `DB_USER` | Usuario indicado por Supabase |
| `DB_PASSWORD` | Contraseña de la base |
| `DB_SSLMODE` | `require` |

Podés reutilizar los valores del `.env` local que ya funciona. Si tu servidor
Coolify solo tiene IPv4 y el host directo de Supabase requiere IPv6, usar
**Connect → Session pooler** en Supabase. Copiar su host, puerto y usuario
exactos: el usuario puede incluir el identificador del proyecto.

Las credenciales se inyectan únicamente en `dashboard`; no se copian al build
de React ni a las imágenes. No hace falta subir un archivo `.env` al servidor.
Si la contraseña contiene caracteres especiales, ingresarla como valor literal
en el campo de la variable de Coolify.

La base debe permitir la conexión desde el servidor de Coolify y contener las
tablas `gld_sales_detail`, `gld_date_dimension`, `gld_order_logistics` y
`gld_customer_analytics` y `gld_payment_detail` para Pagos.

## 4. Dominio y despliegue

En **Domains**, asignar el dominio al servicio **web**:
`https://olist.tudominio.com:80`. El `:80` selecciona el puerto interno del
contenedor; los visitantes acceden por HTTPS normal, sin escribir ese puerto.
El DNS del dominio debe apuntar al servidor donde está el proxy de Coolify.
No asignar un dominio al servicio `dashboard`.

Seleccionar **Deploy**. Esperar a que ambos servicios estén saludables.
Gunicorn carga las ventas al arrancar, por lo que la primera inicialización
puede tardar. Coolify termina HTTPS y Nginx mantiene React y `/dashboard/`
bajo el mismo dominio.

La aplicación no incluye inicio de sesión. Si el dashboard debe ser privado,
configurar el control de acceso correspondiente antes de compartir el dominio.

## 5. Comprobar

- `/`: muestra el portal React.
- `/healthz`: responde `{"status":"ok","service":"olist-web"}`.
- `/dashboard/healthz`: responde con `service: "olist-dashboard"`.
- En Ventas, Logística y Clientes, abrir Gerencial, Analítica y Decisiones y probar los filtros.
- El logo, los gráficos y las descargas deben funcionar dentro del iframe.

La salud de Dash confirma que terminó de arrancar; no consulta PostgreSQL
en cada comprobación. Las consultas posteriores también requieren conexión.
Ventas carga al inicio; Logística y Clientes cargan al primer acceso de cada
proceso. Para renovar las instantáneas, reiniciar el backend. Las reglas y
limitaciones analíticas se documentan en `METRICAS.md`.

## Diagnóstico

| Síntoma | Revisar |
| --- | --- |
| Error antes de construir | Variables obligatorias y ruta del Compose |
| `dashboard` no saludable | Logs de ese servicio, credenciales, tablas y conectividad con Supabase |
| Conexión a Supabase agotada / sin ruta IPv6 | Usar los datos del Session pooler si el servidor solo tiene IPv4 |
| Dominio devuelve 502/503 | Dominio asignado a `web:80`, salud de ambos servicios y proxy de Coolify |
| Portal carga pero dashboard no | Respuesta de `/dashboard/healthz` y logs de Nginx/Gunicorn |

Los logs van a la salida estándar y tienen rotación. No hay volúmenes de datos
locales: el estado persistente pertenece a Supabase. Para actualizar, subir
los cambios a la rama configurada y desplegarla nuevamente desde Coolify.

Referencias: [Docker Compose en Coolify](https://coolify.io/docs/applications/builds/docker-compose)
y [conexiones PostgreSQL de Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres).
