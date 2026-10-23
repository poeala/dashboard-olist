"""Pagos: registros para participación monetaria; pedidos para ticket y cuotas."""
import numpy as np
import pandas as pd

METHODS = {
    "credit_card": "Tarjeta de crédito", "boleto": "Boleto",
    "voucher": "Voucher", "debit_card": "Tarjeta de débito",
}


def preparar_pagos(rows):
    rows = rows.copy()
    payments = rows[rows["has_payment"].fillna(False)].copy()
    # Solo eliminar repeticiones idénticas; una clave conflictiva requiere revisión.
    columns = ["order_id", "payment_sequential", "payment_type", "payment_value", "payment_installments"]
    payments = payments.drop_duplicates(columns)
    keyed = payments[payments["payment_sequential"].notna()]
    if keyed.duplicated(["order_id", "payment_sequential"]).any():
        raise ValueError("Registros de pago contradictorios para una misma clave")
    for col in ("payment_value", "payment_installments"):
        payments[col] = pd.to_numeric(payments[col], errors="coerce")
    payments["valid_value"] = (
        np.isfinite(payments["payment_value"]) & payments["payment_value"].ge(0)
        & payments["payment_sequential"].notna()
    )
    payments["valid_installments"] = (
        np.isfinite(payments["payment_installments"])
        & payments["payment_installments"].ge(1)
        & payments["payment_installments"].mod(1).eq(0)
    )
    types = payments["payment_type"].astype("string").str.strip().str.lower()
    payments["method"] = types.map(METHODS).fillna("Sin información / otro")
    payments["known_method"] = types.isin(METHODS)
    payments["valid_amount"] = payments["payment_value"].where(payments["valid_value"])
    payments["valid_quota"] = payments["payment_installments"].where(payments["valid_installments"])
    grouped = payments.groupby("order_id")
    summary = grouped.agg(
        records=("has_payment", "size"), valid_amounts=("valid_value", "all"),
        known_method=("known_method", "all"), method_count=("method", "nunique"),
        method=("method", "first"), known_installments=("valid_installments", "all"),
        installments=("valid_quota", "max"),
    )
    summary["amount"] = grouped["valid_amount"].sum(min_count=1)
    orders = rows[["order_id", "purchase_date", "gold_segment"]].drop_duplicates("order_id").set_index("order_id")
    orders = orders.join(summary).reset_index()
    orders["complete"] = orders["valid_amounts"].eq(True) & orders["records"].gt(0)
    orders["known_method"] = orders["known_method"].eq(True)
    orders["known_installments"] = orders["known_installments"].eq(True)
    orders["method"] = orders["method"].fillna("Sin información / otro")
    orders.loc[orders["method_count"].gt(1), "method"] = "Pagos mixtos"
    orders.loc[~orders["known_method"], "method"] = "Sin información / otro"
    orders["gold_segment"] = orders["gold_segment"].fillna("Sin segmento")
    orders["financed"] = orders["known_installments"] & orders["installments"].gt(1)
    orders["mixed"] = orders["known_method"] & orders["method_count"].gt(1)
    complete = orders[orders["complete"]].copy()
    payments = payments[payments["order_id"].isin(complete["order_id"])]
    quality = {
        "source_orders": len(orders), "without_payment": int(orders["records"].isna().sum()),
        "invalid_orders": int((orders["records"].notna() & ~orders["complete"]).sum()),
        "unknown_installments": int((~complete["known_installments"]).sum()),
        "unknown_method": int((~complete["known_method"]).sum()),
    }
    return payments, complete, quality


def resumen_pagos(orders):
    quotas = orders[orders["known_installments"]]
    methods = orders[orders["known_method"]]
    return {
        "amount": orders["amount"].sum() if len(orders) else None,
        "orders": len(orders), "ticket": orders["amount"].mean(),
        "financed_pct": 100 * quotas["financed"].mean() if len(quotas) else None,
        "avg_installments": quotas["installments"].mean(),
        "mixed_pct": 100 * methods["mixed"].mean() if len(methods) else None,
        "quota_orders": len(quotas), "method_orders": len(methods),
    }


def participacion_pagos(payments):
    result = payments.groupby("method", as_index=False).agg(
        amount=("payment_value", "sum"), records=("order_id", "size"), orders=("order_id", "nunique"),
    )
    total = result["amount"].sum()
    result["share"] = 100 * result["amount"] / total if total > 0 else np.nan
    return result.sort_values("amount", ascending=False)


def agrupar_pedidos_pago(orders, dimension="method"):
    return orders.groupby(dimension, as_index=False).agg(
        orders=("order_id", "size"), amount=("amount", "sum"),
        ticket=("amount", "mean"), median=("amount", "median"),
    )


def preferencias_segmento(orders):
    usable = orders[orders["known_method"] & orders["gold_segment"].ne("Sin segmento")]
    result = usable.groupby(["gold_segment", "method"], as_index=False).agg(orders=("order_id", "size"))
    result["segment_orders"] = result.groupby("gold_segment")["orders"].transform("sum")
    result["share"] = 100 * result["orders"] / result["segment_orders"]
    return result


MINIMUM_ORDERS = 30
MINIMUM_DIFFERENCE = 20
QUOTA_RANGES = [("1 cuota", 1, 1), ("2–3 cuotas", 2, 3),
                ("4–6 cuotas", 4, 6), ("7 o más cuotas", 7, float("inf"))]


def participacion_por_tipo_pedido(payments, orders):
    """Clasifica cada pedido una vez; todo el importe mixto queda separado."""
    result = agrupar_pedidos_pago(orders)
    records = orders.groupby("method")["records"].sum()
    result["records"] = result["method"].map(records)
    total = result["amount"].sum()
    result["share"] = 100 * result["amount"] / total if total > 0 else np.nan
    return result.sort_values("amount", ascending=False)


def evolucion_pagos(orders, daily=False):
    """Mantiene períodos ausentes como huecos, nunca como importes cero."""
    source = orders.dropna(subset=["purchase_date"]).copy()
    source["period"] = source["purchase_date"].dt.to_period("D" if daily else "M")
    result = source.groupby("period").agg(
        amount=("amount", "sum"), ticket=("amount", "mean"), orders=("order_id", "size"),
    )
    if not result.empty:
        result = result.reindex(pd.period_range(result.index.min(), result.index.max(),
                                               freq="D" if daily else "M"))
    result.index.name = "period"
    result = result.reset_index()
    result["period"] = result["period"].dt.to_timestamp()
    return result


def _credito_exclusivo(orders):
    return orders[orders["known_method"] & orders["known_installments"]
                  & orders["method"].eq("Tarjeta de crédito")]


def resumen_cuotas(orders):
    credit = _credito_exclusivo(orders)
    result = []
    for label, low, high in QUOTA_RANGES:
        amounts = credit.loc[credit["installments"].between(low, high), "amount"]
        result.append({"range": label, "orders": len(amounts), "median": amounts.median(),
                       "p25": amounts.quantile(.25), "p75": amounts.quantile(.75)})
    return pd.DataFrame(result)


def comparaciones_pago(orders, minimum=MINIMUM_ORDERS, uplift=MINIMUM_DIFFERENCE):
    """Única fuente de reglas para pantalla y pruebas; conserva motivos no evaluables."""
    results = []

    def compare(kind, label, group, rest, reference, metric, action, followup):
        value = group["amount"].agg(metric)
        base = rest["amount"].agg(metric)
        if len(group) < minimum or len(rest) < minimum:
            status, gap = "Muestra insuficiente", None
        elif pd.isna(base) or base <= 0:
            status, gap = "Referencia monetaria no positiva", None
        else:
            gap = 100 * (value / base - 1)
            status = "Hallazgo" if gap >= uplift else "Sin hallazgo según estas reglas"
        results.append({
            "kind": kind, "group": label, "reference": reference,
            "metric": "Ticket promedio" if metric == "mean" else "Mediana",
            "orders": len(group), "reference_orders": len(rest),
            "value": value, "reference_value": base, "gap": gap,
            "status": status, "action": action, "followup": followup,
        })

    known = orders[orders["known_method"]]
    for method in METHODS.values():
        compare("medio", method, known[known["method"].eq(method)],
                known[known["method"].ne(method)], "Resto de pedidos con medio conocido", "mean",
                "Comparar categorías, períodos y perfiles similares; revisar comisiones y margen.",
                "Si persiste la diferencia, evaluar un piloto con control y medir conversión y margen incremental.")
    credit = _credito_exclusivo(orders)
    single = credit[credit["installments"].eq(1)]
    for label, low, high in QUOTA_RANGES[1:]:
        compare("cuotas", label, credit[credit["installments"].between(low, high)],
                single, "Crédito exclusivo en una cuota", "median",
                "Revisar productos y períodos comparables; estimar costo de financiación y margen.",
                "Evaluar un piloto con control y medir conversión y margen neto de costos financieros.")
    return results


def oportunidades_pago(orders, minimum=MINIMUM_ORDERS, uplift=MINIMUM_DIFFERENCE):
    return sorted(
        (item for item in comparaciones_pago(orders, minimum, uplift) if item["status"] == "Hallazgo"),
        key=lambda item: (-item["gap"], item["group"]),
    )
