# Olist · Business Intelligence

Tablero de prueba para presentar el trabajo realizado para la cátedra de
**Análisis de Datos Masivos** de la carrera de **Maestría en Ciencia de Datos
de UCASAL**, realizado por **Fabio Quaino y María Luz Andrade**.
La identidad visual y sus fuentes se documentan en [BRANDING.md](BRANDING.md).

Portal React + Bootstrap con el dashboard Dash existente embebido.
La web está en español, se adapta a móvil e incluye navegación entre las
vistas Gerencial, Analítica y Decisiones en **Ventas, Logística y Clientes**,
recarga, pantalla completa y apertura en otra pestaña. Pagos permanece pendiente.
Las definiciones, denominadores y reglas de hallazgos están en [METRICAS.md](METRICAS.md).

Logística → Gerencial incluye un mapa Leaflet de las cinco regiones de Brasil,
con GeoJSON local, zoom y detalle por región. Permite alternar entre pedidos
únicos y porcentaje de entregas con retraso, respetando los filtros de año y
mes. Incluye leyenda y tabla accesible. Leaflet y los límites se sirven desde
el propio dashboard; no requiere CDN ni servicios de mapas externos.
Las fuentes y la regeneración del GeoJSON están en [MAP_SOURCES.md](assets/MAP_SOURCES.md).

## Desarrollo local

Requisitos: Python 3.13 y Node.js 22.14 o posterior.

En la raíz del repositorio, crear el entorno Python:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Completar `.env` con las credenciales PostgreSQL/Supabase. Si el archivo ya
existe, conservarlo. Las tablas Gold que necesita la aplicación son
`gld_sales_detail`, `gld_date_dimension`, `gld_order_logistics` y
`gld_customer_analytics`. `gld_payment_detail` queda disponible para el módulo
de Pagos pendiente.
El backend consulta las ventas al iniciar; necesita acceso a la base para arrancar.

Iniciar Python:

```powershell
.\.venv\Scripts\python.exe app.py
```

En otra terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Abrir **http://127.0.0.1:5173**. El dashboard también se puede abrir directamente
en **http://127.0.0.1:8050/dashboard/**.

Vite reenvía `/dashboard/` a Python. Para cambiar la dirección del backend,
copiar `frontend/.env.example` a `frontend/.env` y modificar `DASH_PROXY_TARGET`.
No colocar credenciales de base de datos en variables `VITE_*`: esas variables
son públicas en el navegador.

## Ejecutar con Docker

Para publicar en Coolify, seguir [COOLIFY.md](COOLIFY.md). Usar
`compose.coolify.yaml` allí y `compose.yaml` para ejecutar localmente.

Con Docker Desktop activo y el `.env` de la raíz configurado:

```powershell
docker compose up --build -d --wait --wait-timeout 240
```

Abrir **http://127.0.0.1:8080**.

```powershell
docker compose logs -f
docker compose down
```

Nginx sirve React y reenvía el dashboard a Gunicorn en la red interna.
El puerto del backend no se publica y el portal queda ligado a localhost.
Ambos servicios incluyen comprobaciones de salud y reinicio automático.
Coolify recibe las credenciales mediante variables de entorno y publica
únicamente `web:80` detrás de su proxy HTTPS. Este proyecto no incluye autenticación de usuarios.
Un hosting exclusivamente estático no ejecuta Python ni conecta por sí mismo
a PostgreSQL: necesita este backend desplegado y el proxy `/dashboard/`.

## Integración

```text
Navegador → React / Bootstrap
             └── iframe /dashboard/?area=logistica&vista=gerencial&embed=1
                    └── Vite (desarrollo) o Nginx (Docker)
                           └── Dash / Python → PostgreSQL / Supabase
```

El prefijo `/dashboard/` se aplica a los recursos y callbacks de Dash.
`embed=1` oculta la navegación duplicada; sin ese parámetro el dashboard
conserva sus selectores. `area` acepta `ventas`, `logistica` y `clientes`;
`vista` acepta `gerencial`, `analitica` y `decisiones`. Ejemplo de enlace al
portal: `http://localhost:8080/?area=clientes&vista=analitica`.
El logo usa la URL de recursos de Dash para funcionar bajo el prefijo.

La web comprueba `/dashboard/healthz` antes de montar el iframe y muestra
un estado recuperable si el backend no responde. Esta comprobación confirma
que la aplicación arrancó y cargó los datos iniciales; no garantiza que cada
consulta posterior a la base vaya a funcionar. Los datos mantienen el ciclo
de carga de la aplicación original; recargar el iframe no reinicia Python.
Logística y Clientes cargan una instantánea de solo lectura al primer acceso
de cada proceso y la conservan hasta reiniciar el backend.
Cambiar de área o vista vuelve a montar el dashboard y reinicia sus filtros.

## Verificación

Desde la raíz, las pruebas de integración verifican los recursos y callbacks
de Dash sin consultar la base:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Para React:

```powershell
cd frontend
npm test
npm run build
```

`npm test` comprueba enlaces, vistas inválidas y detección de errores del
backend, incluida una respuesta HTML que podría devolver un hosting mal
configurado. `npm run build` genera `frontend/dist`.

Para servir ese build localmente, con Python activo:

```powershell
npm run preview
```

Abrir **http://127.0.0.1:4173**.

Las credenciales quedan en `.env`, excluido de Git y de las imágenes Docker.
Los valores de ejemplo no incluyen contraseñas.
