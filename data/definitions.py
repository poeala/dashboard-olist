"""Definiciones compartidas para comparar las áreas sobre el mismo histórico."""
import pandas as pd

EXCLUDED_STATUSES = {"canceled", "unavailable"}

# Conserva el criterio de Ventas: omitir el último mes si su última fecha
# observada no es el último día del mes. No certifica completitud del origen.
PERIOD_CUTOFF_SQL = """
    SELECT CASE
        WHEN MAX(order_purchase_date) = (
            date_trunc('month', MAX(order_purchase_date))
            + interval '1 month - 1 day'
        )::date
        THEN date_trunc('month', MAX(order_purchase_date)) + interval '1 month'
        ELSE date_trunc('month', MAX(order_purchase_date))
    END::date
    FROM gld_sales_detail
"""


def ventas_validas(df):
    """Valor de productos, sin pedidos cancelados o no disponibles."""
    statuses = df["order_status"].fillna("").astype(str).str.strip().str.lower()
    return df.loc[~statuses.isin(EXCLUDED_STATUSES)].copy()


def facturacion_mensual(df):
    """Solo comparar meses consecutivos; no asumir ventas cero en meses ausentes."""
    valid = ventas_validas(df)
    dates = pd.to_datetime(valid["order_purchase_date"], errors="coerce")
    valid["periodo"] = dates.dt.to_period("M")
    valid["price"] = pd.to_numeric(valid["price"], errors="coerce")
    values = valid.dropna(subset=["periodo", "price"]).groupby("periodo")["price"].sum()
    if len(values):
        values = values.reindex(pd.period_range(values.index.min(), values.index.max(), freq="M"))
    values.index.name = "periodo"
    result = values.rename("Facturación").reset_index()
    result["Facturación anterior"] = result["Facturación"].shift(1)
    previous = result["Facturación anterior"].where(result["Facturación anterior"] != 0)
    result["Variación (%)"] = 100 * (result["Facturación"] - previous) / previous
    return result
