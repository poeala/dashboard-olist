"""Regiones de Brasil y métricas al grano de pedido (destino del cliente)."""

REGIONS = {
    "N": ("Norte", ("AC", "AP", "AM", "PA", "RO", "RR", "TO")),
    "NE": ("Nordeste", ("AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE")),
    "CO": ("Centro-Oeste", ("DF", "GO", "MT", "MS")),
    "SE": ("Sudeste", ("ES", "MG", "RJ", "SP")),
    "S": ("Sur", ("PR", "RS", "SC")),
}
STATE_REGION = {state: code for code, (_, states) in REGIONS.items() for state in states}


def resumen_regiones(orders):
    """Recibe pedidos_logistica: una fila por pedido, con eligible y late."""
    selected = orders.copy()
    selected["region"] = selected["customer_state"].astype("string").str.strip().str.upper().map(STATE_REGION)
    regions = []
    for code, (name, states) in REGIONS.items():
        group = selected[selected["region"] == code]
        eligible = int(group["eligible"].sum())
        late = int(group["late"].sum())
        regions.append({
            "id": code, "name": name, "states": ", ".join(states),
            "orders": len(group), "eligible": eligible, "late": late,
            "late_pct": 100 * late / eligible if eligible else None,
        })
    return {"regions": regions, "unmapped": int(selected["region"].isna().sum())}
