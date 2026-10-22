"""Cálculos puros: grano, denominadores y cortes temporales explícitos."""
import pandas as pd

ALL = "__todos__"


def filtrar_periodo(df, year=ALL, month=ALL):
    result = df.copy()
    if year not in (None, ALL):
        result = result[result["purchase_date"].dt.year == int(year)]
    if month not in (None, ALL):
        result = result[result["purchase_date"].dt.month == int(month)]
    return result.copy()


def corte_periodo(df, year=ALL, month=ALL):
    cutoff = df.attrs.get("cutoff", df["purchase_date"].max())
    if pd.isna(cutoff):
        return pd.NaT
    cutoff = pd.Timestamp(cutoff).tz_localize(None).normalize()
    if year not in (None, ALL):
        month_value = int(month) if month not in (None, ALL) else 12
        requested = pd.Timestamp(int(year), month_value, 1) + pd.offsets.MonthEnd(0)
        return min(cutoff, requested)
    if month not in (None, ALL):
        requested = pd.Timestamp(cutoff.year, int(month), 1) + pd.offsets.MonthEnd(0)
        if requested > cutoff:
            requested = requested - pd.DateOffset(years=1)
        return requested
    return cutoff


def pedidos_logistica(rows):
    """Una fila por pedido, sumando fletes de vendedores solo una vez."""
    grouped = rows.groupby("order_id")
    orders = grouped.agg(
        purchase_date=("purchase_date", "min"),
        customer_state=("customer_state", "first"),
        delivered_date=("delivered_date", "max"),
        estimated_date=("estimated_date", "max"),
        delivery_days=("delivery_days", "max"),
        review_score=("review_score", "max"),
    )
    orders[["freight", "product_value"]] = grouped[["freight", "product_value"]].sum(min_count=1)
    orders = orders.reset_index()
    return _delivery_columns(orders)


def _delivery_columns(df):
    result = df.copy()
    result["eligible"] = result["delivered_date"].notna() & result["estimated_date"].notna()
    result["late"] = result["eligible"] & (result["delivered_date"] > result["estimated_date"])
    result["delivered"] = result["delivered_date"].notna()
    result["valid_days"] = result["delivery_days"].where(
        result["delivered"] & result["delivery_days"].ge(0)
    )
    result["valid_review"] = result["review_score"].where(result["review_score"].between(1, 5))
    result["delivery_result"] = "Sin fechas comparables"
    result.loc[result["eligible"], "delivery_result"] = "En plazo"
    result.loc[result["late"], "delivery_result"] = "Con retraso"
    return result


def resumen_logistica(orders):
    eligible = int(orders["eligible"].sum())
    late = int(orders["late"].sum())
    return {
        "orders": len(orders), "eligible": eligible, "late": late,
        "late_pct": 100 * late / eligible if eligible else None,
        "avg_days": orders["valid_days"].mean(),
        "avg_freight": orders["freight"].mean(),
        "without_delivery": int((~orders["delivered"]).sum()),
    }


def agrupar_logistica(rows, dimension="customer_state"):
    if dimension == "customer_state":
        grouped_rows = pedidos_logistica(rows)
    else:
        # Cada proveedor se evalúa en pedidos asociados, no en artículos.
        grouped_rows = _delivery_columns(rows.drop_duplicates(["order_id", "seller_id"]))
    if dimension == "distance_band":
        grouped_rows["distance_band"] = pd.cut(
            grouped_rows["distance_km"].where(grouped_rows["distance_km"].ge(0)),
            [-0.01, 100, 500, 1000, float("inf")],
            labels=["Hasta 100 km", "100–500 km", "500–1.000 km", "Más de 1.000 km"],
        ).astype("object")
    grouped_rows["group"] = grouped_rows[dimension].fillna("Sin información").astype(str)
    # Para estado de origen/distancia puede haber varios vendedores del
    # mismo pedido en un grupo: sumar fletes, contar el pedido una sola vez.
    by_order = grouped_rows.groupby(["group", "order_id"])
    grouped_orders = by_order.agg(
        eligible=("eligible", "max"), late=("late", "max"),
        valid_days=("valid_days", "max"), valid_review=("valid_review", "max"),
    )
    grouped_orders["freight"] = by_order["freight"].sum(min_count=1)
    grouped_orders = grouped_orders.reset_index()
    stats = grouped_orders.groupby("group", as_index=False).agg(
        orders=("order_id", "size"), eligible=("eligible", "sum"),
        late=("late", "sum"), avg_days=("valid_days", "mean"),
        avg_freight=("freight", "mean"), avg_review=("valid_review", "mean"),
    )
    stats["late_pct"] = 100 * stats["late"] / stats["eligible"].where(stats["eligible"] > 0)
    return stats.sort_values(["orders", "group"], ascending=[False, True])


def evaluar_regla_logistica(groups, baseline_pct, min_sample=30, floor_pct=10, margin_pp=5):
    """Regla descriptiva; la referencia proviene de pedidos únicos, no de grupos."""
    limit = None if baseline_pct is None or pd.isna(baseline_pct) else max(floor_pct, baseline_pct + margin_pp)
    eligible = groups["eligible"].ge(min_sample) & groups["late_pct"].notna()
    selected = eligible & (groups["late_pct"].gt(limit) if limit is not None else False)
    return limit, selected


def sensibilidad_logistica(groups, baseline_pct, min_sample=30):
    """Varía un parámetro por vez, manteniendo datos, referencia y mínimo de casos."""
    scenarios = (
        ("Base", 10, 5),
        ("Piso 5 %", 5, 5),
        ("Piso 15 %", 15, 5),
        ("Margen +2 pp", 10, 2),
        ("Margen +10 pp", 10, 10),
    )
    _, base_mask = evaluar_regla_logistica(groups, baseline_pct, min_sample)
    base = set(groups.loc[base_mask, "group"])
    detail = groups[["group", "eligible", "late_pct"]].copy()
    enough = groups["eligible"].ge(min_sample) & groups["late_pct"].notna()
    summaries = []
    for name, floor, margin in scenarios:
        limit, mask = evaluar_regla_logistica(groups, baseline_pct, min_sample, floor, margin)
        selected = set(groups.loc[mask, "group"])
        summaries.append({
            "scenario": name, "floor": floor, "margin": margin, "limit": limit,
            "evaluable": int(enough.sum()) if limit is not None else 0,
            "selected": len(selected), "retained": len(selected & base),
            "entered": len(selected - base), "exited": len(base - selected),
        })
        detail[name] = "No evaluable"
        if limit is not None:
            detail.loc[enough, name] = "No seleccionado"
            detail.loc[mask, name] = "Seleccionado"
    return pd.DataFrame(summaries), detail


def perfil_clientes(orders, reference_date):
    usable = orders[orders["customer_id"].notna()].drop_duplicates(["customer_id", "order_id"]).copy()
    usable["valid_review"] = usable["review_score"].where(usable["review_score"].between(1, 5))
    by_customer = usable.groupby("customer_id")
    profiles = by_customer.agg(
        orders=("order_id", "nunique"),
        first_purchase=("purchase_date", "min"),
        last_purchase=("purchase_date", "max"),
        review_sum=("valid_review", "sum"),
        review_orders=("valid_review", "count"),
        gold_segment=("gold_segment", "first"),
    )
    profiles["spent"] = by_customer["product_value"].sum(min_count=1)
    profiles = profiles.reset_index()
    profiles["repeat"] = profiles["orders"] > 1
    profiles["recency_days"] = (reference_date - profiles["last_purchase"]).dt.days
    threshold = profiles["spent"].quantile(.75)
    profiles["high_value"] = profiles["spent"].notna() & profiles["spent"].ge(threshold)
    profiles["segment"] = "Compra única"
    profiles.loc[profiles["repeat"], "segment"] = "Recurrente"
    profiles.loc[profiles["high_value"], "segment"] += " · alto valor"
    profiles.attrs["high_value_threshold"] = threshold
    return profiles


def resumen_clientes(profiles):
    customers = len(profiles)
    orders = int(profiles["orders"].sum())
    spent = profiles["spent"].sum(min_count=1)
    return {
        "customers": customers, "orders": orders,
        "repeat": int(profiles["repeat"].sum()),
        "repeat_pct": 100 * profiles["repeat"].sum() / customers if customers else None,
        "spent": spent,
        "ticket": spent / orders if orders else None,
    }


def agrupar_clientes(profiles, dimension="segment"):
    data = profiles.copy()
    data["group"] = data[dimension].fillna("Sin información")
    by_segment = data.groupby("group")
    groups = by_segment.agg(
        customers=("customer_id", "size"), orders=("orders", "sum"),
        repeat=("repeat", "sum"), recency_days=("recency_days", "mean"),
        review_sum=("review_sum", "sum"), review_orders=("review_orders", "sum"),
    )
    groups["spent"] = by_segment["spent"].sum(min_count=1)
    groups = groups.reset_index()
    groups["repeat_pct"] = 100 * groups["repeat"] / groups["customers"]
    groups["ticket"] = groups["spent"] / groups["orders"]
    groups["avg_review"] = groups["review_sum"] / groups["review_orders"].where(groups["review_orders"] > 0)
    return groups.sort_values("customers", ascending=False)
