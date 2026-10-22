/* Leaflet 1.9.4 is served locally from assets/00_leaflet. */
(function () {
    "use strict";
    let active = null;
    let request = 0;
    const geometries = new Map();
    const colors = ["#fff1d6", "#fed28b", "#f99d59", "#e95b3c", "#b51f32"];
    const noData = "#dce3eb";
    const integer = new Intl.NumberFormat("es-AR");
    const decimal = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 1 });

    function dispose() {
        if (active) {
            active.resize.disconnect();
            active.map.remove();
            active = null;
        }
    }
    // Dash replaces dynamic layouts when filters or navigation change.
    new MutationObserver(function () {
        if (active && !active.element.isConnected) dispose();
    }).observe(document.documentElement, { childList: true, subtree: true });

    async function geometry(url) {
        if (!geometries.has(url)) {
            geometries.set(url, fetch(url).then(function (response) {
                if (!response.ok) throw new Error("GeoJSON unavailable");
                return response.json();
            }).catch(function (error) {
                geometries.delete(url);
                throw error;
            }));
        }
        return geometries.get(url);
    }

    function details(region) {
        const box = document.createElement("div");
        const title = document.createElement("strong");
        title.textContent = region.name;
        box.append(title);
        [region.states, "Pedidos: " + integer.format(region.orders),
            "Entregas comparables: " + integer.format(region.eligible),
            "Tardíos: " + integer.format(region.late),
            "Retrasos: " + (region.late_pct === null ? "Sin datos" : decimal.format(region.late_pct) + " %")
        ].forEach(function (text) {
            const line = document.createElement("div");
            line.textContent = text;
            box.append(line);
        });
        return box;
    }

    async function render(data, metric) {
        const current = ++request;
        if (!data) return window.dash_clientside.no_update;
        try {
            const geojson = await geometry(data.geojson_url);
            // Let React finish mounting the sibling map container.
            await new Promise(window.requestAnimationFrame);
            if (current !== request) return window.dash_clientside.no_update;
            const element = document.getElementById("logistics-region-map");
            if (!element) return window.dash_clientside.no_update;
            if (!window.L) throw new Error("Leaflet unavailable");
            if (active && active.element !== element) dispose();
            const L = window.L;
            if (!active) {
                const map = L.map(element, {
                    scrollWheelZoom: false, minZoom: 2, maxZoom: 7,
                    zoomSnap: 0.25, attributionControl: true,
                });
                const resize = new ResizeObserver(function () { map.invalidateSize(); });
                resize.observe(element);
                active = { element, map, resize };
                map.attributionControl.addAttribution("Límites: GeoJSON de estados del proyecto");
            }
            const state = active;
            if (state.layer) state.map.removeLayer(state.layer);
            if (state.legend) state.legend.remove();
            if (state.reset) state.reset.remove();
            const byId = Object.fromEntries(data.regions.map(r => [r.id, r]));
            const isRate = metric === "late_pct";
            const key = isRate ? "late_pct" : "orders";
            const maximum = Math.max(1, ...data.regions.map(r => r.orders));
            const step = Math.max(1, Math.ceil(maximum / 5));
            function fill(region) {
                if (isRate && region.late_pct === null) return noData;
                const index = isRate ? Math.floor(region.late_pct / 20)
                    : Math.max(0, Math.ceil(region.orders / step) - 1);
                return colors[Math.min(4, index)];
            }
            state.layer = L.geoJSON(geojson, {
                style: feature => ({
                    color: "#fff", weight: 2, fillOpacity: 0.92,
                    fillColor: fill(byId[feature.id]),
                }),
                onEachFeature: function (feature, layer) {
                    const region = byId[feature.id];
                    layer.bindTooltip(details(region), { sticky: true });
                    layer.bindPopup(details(region));
                    layer.on({
                        mouseover: function () { layer.setStyle({ color: "#003D7C", weight: 3 }); layer.bringToFront(); },
                        mouseout: function () { state.layer.resetStyle(layer); },
                    });
                    layer.on("add", function () {
                        const path = layer.getElement();
                        path.setAttribute("tabindex", "0");
                        path.setAttribute("role", "button");
                        path.setAttribute("aria-label", region.name + ": " + (region[key] === null ? "Sin datos" : decimal.format(region[key]) + (isRate ? " % de retrasos" : " pedidos")));
                        path.addEventListener("keydown", function (event) {
                            if (event.key === "Enter" || event.key === " ") {
                                event.preventDefault(); layer.openPopup();
                            }
                        });
                    });
                },
            }).addTo(state.map);
            const bounds = state.layer.getBounds();
            const fit = () => state.map.fitBounds(bounds, { padding: [18, 18] });
            if (!state.fitted) { fit(); state.fitted = true; }
            state.map.setMaxBounds(bounds.pad(0.5));
            state.reset = L.control({ position: "topleft" });
            state.reset.onAdd = function () {
                const button = L.DomUtil.create("button", "logistics-map-reset");
                button.type = "button"; button.textContent = "Ver Brasil";
                L.DomEvent.disableClickPropagation(button);
                L.DomEvent.on(button, "click", fit);
                return button;
            };
            state.reset.addTo(state.map);
            state.legend = L.control({ position: "bottomright" });
            state.legend.onAdd = function () {
                const box = L.DomUtil.create("div", "logistics-map-legend");
                const heading = document.createElement("strong");
                heading.textContent = isRate ? "Retrasos (%)" : "Pedidos";
                box.append(heading);
                colors.forEach(function (color, index) {
                    const row = document.createElement("div");
                    const swatch = document.createElement("i");
                    swatch.style.backgroundColor = color;
                    const low = isRate ? index * 20 : index === 0 ? 0 : index * step + 1;
                    const high = isRate ? (index + 1) * 20 : (index + 1) * step;
                    const label = isRate ? decimal.format(low) + "–" + (index < 4 ? "<" : "") + decimal.format(high) + " %"
                        : integer.format(low) + "–" + integer.format(high);
                    row.append(swatch, document.createTextNode(label)); box.append(row);
                });
                if (isRate) {
                    const row = document.createElement("div");
                    const swatch = document.createElement("i");
                    swatch.style.backgroundColor = noData;
                    row.append(swatch, document.createTextNode("Sin datos")); box.append(row);
                }
                L.DomEvent.disableClickPropagation(box);
                return box;
            };
            state.legend.addTo(state.map);
            return isRate ? "Escala fija de 0 a 100 %. Gris: sin entregas comparables."
                : "Mayor intensidad = más pedidos. Escala ajustada al período seleccionado.";
        } catch (error) {
            if (current !== request) return window.dash_clientside.no_update;
            dispose();
            return "No pudimos cargar el mapa. Consultá los datos por región o recargá la vista para reintentar.";
        }
    }
    window.dash_clientside = Object.assign({}, window.dash_clientside, { logisticsMap: { render } });
}());
