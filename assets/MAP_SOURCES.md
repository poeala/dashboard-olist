# Mapa regional de Logística

- Leaflet 1.9.4: https://leafletjs.com/download.html. Distribución local
  descargada de `https://unpkg.com/leaflet@1.9.4/dist/`, licencia BSD-2-Clause
  conservada en `00_leaflet/LICENSE`. No necesita CDN ni teselas externas.
- `br_regions.geojson`: derivado de `br_states.geojson`, que ya formaba parte
  del proyecto. Se unieron los estados de cada una de las cinco grandes
  regiones mediante Shapely y se simplificaron los límites con tolerancia
  de 0,01 grados para visualización. No es cartografía catastral.
- La procedencia/licencia original del GeoJSON estatal no estaba documentada
  en el repositorio; este cambio conserva esa fuente y no la atribuye al IBGE.
- Agrupación de las 27 unidades federativas en `data/brazil_regions.py`.
  La API del IBGE documenta las cinco regiones N, NE, SE, S y CO:
  https://servicodados.ibge.gov.br/api/docs/malhas?versao=3#malhas-regioes-id-get

Regeneración (Shapely es una dependencia de desarrollo, no del servidor):

```powershell
python -m pip install shapely
python scripts/build_brazil_regions.py
```

El navegador solo recibe los conteos regionales. Los filtros de compra se
aplican antes del agrupamiento; los pedidos con varios vendedores cuentan
una sola vez. Retrasos = tardíos / entregas con ambas fechas × 100; ausencia
de fechas comparables se representa con gris, y cero retrasos con el tono
mínimo. La escala de pedidos se recalcula por período; la de retrasos es fija.
