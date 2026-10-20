
# Consultar ventas, enriquecerlas con calendario y cargar pagos por separado
import pandas as pd
from sqlalchemy import text
from data.database import engine
from data.definitions import PERIOD_CUTOFF_SQL


def cargar_ventas():
    # Consultar el detalle de ventas con sus dimensiones.
    consulta = text(f"""
        SELECT
            s.order_id,
            s.order_item_id,
            s.order_purchase_date,
            s.order_purchase_time,
            s.product_id,
            s.customer_unique_id,
            s.seller_id,
            s.product_category_name,
            s.order_status,
            s.price,
            s.freight_value,
            s.item_total_value,
            s.review_score,
            d.year AS anio,
            d.quarter AS trimestre,
            d.month AS mes_numero,
            d.day AS dia,
            d.day_of_week,
            d.day_name,
            d.is_weekend
        FROM gld_sales_detail s
        INNER JOIN gld_date_dimension d
            ON s.order_purchase_date = d.date
        WHERE s.order_purchase_date < ({PERIOD_CUTOFF_SQL})
    """)

    df = pd.read_sql(consulta, engine)

    # Normalizar las columnas de fechas.
    df["order_purchase_date"] = pd.to_datetime(
        df["order_purchase_date"]
    )
    df["mes"] = (
        df["order_purchase_date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    # Preparar las dimensiones para los gráficos y filtros.
    df["seller_label"] = df["seller_id"].str[:8]
    df["product_category_name"] = (
        df["product_category_name"].fillna("Sin categoría")
    )
    df["order_status"] = df["order_status"].fillna("Sin estado")
    df["review_score"] = pd.to_numeric(
        df["review_score"], errors="coerce"
    )

    return df


def cargar_pagos():
    # Consultar los pagos sin mezclarlos con el detalle de artículos.
    consulta = text("""
        SELECT
            order_id,
            payment_sequential,
            payment_type,
            payment_value,
            payment_installments
        FROM gld_payment_detail
    """)

    df = pd.read_sql(consulta, engine)

    # Normalizar las columnas numéricas.
    df["payment_value"] = pd.to_numeric(
        df["payment_value"], errors="coerce"
    )
    df["payment_installments"] = pd.to_numeric(
        df["payment_installments"], errors="coerce"
    )
    df["payment_type"] = df["payment_type"].fillna(
        "Sin información"
    )

    return df


# Consultar ventas agrupadas según la configuración del análisis.
def consultar_ventas_agrupadas(
    dimension,
    dimension_secundaria=None,
    metricas=None,
    anio=None,
    trimestre=None,
    mes=None,
    estado=None
):
    # Definir las dimensiones y métricas permitidas.
    dimensiones = {
        "anio": ("d.year", "Año"),
        "trimestre": ("d.quarter", "Trimestre"),
        "mes": ("TO_CHAR(s.order_purchase_date, 'YYYY-MM')", "Mes"),
        "fecha": ("s.order_purchase_date", "Fecha"),
        "categoria": (
            "COALESCE(s.product_category_name, 'Sin categoría')",
            "Categoría"
        ),
        "vendedor": ("s.seller_id", "Vendedor"),
        "estado": (
            "COALESCE(s.order_status, 'Sin estado')",
            "Estado"
        )
    }

    medidas = {
        "facturacion": ("SUM(s.price)", "Facturación"),
        "articulos": ("COUNT(*)", "Cantidad de artículos"),
        "pedidos": ("COUNT(DISTINCT s.order_id)", "Pedidos únicos"),
        "compradores": (
            "COUNT(DISTINCT s.customer_unique_id)",
            "Compradores únicos"
        )
    }

    # Validar la configuración recibida.
    if dimension not in dimensiones:
        raise ValueError("Dimensión principal no válida")

    if (
        dimension_secundaria
        and dimension_secundaria not in dimensiones
    ):
        raise ValueError("Dimensión secundaria no válida")

    metricas = metricas or ["facturacion"]
    metricas = list(dict.fromkeys(metricas))

    if not metricas or any(m not in medidas for m in metricas):
        raise ValueError("Las métricas seleccionadas no son válidas")

    # Preparar las columnas de agrupación.
    grupos = [dimension]

    if dimension_secundaria and dimension_secundaria != dimension:
        grupos.append(dimension_secundaria)

    columnas = [
        f"{dimensiones[g][0]} AS {g}"
        for g in grupos
    ]

    columnas.extend(
        f"{medidas[m][0]} AS {m}"
        for m in metricas
    )

    agrupacion = ", ".join(
        dimensiones[g][0] for g in grupos
    )

    # Preparar los filtros y sus parámetros.
    filtros = [
        f"s.order_purchase_date < ({PERIOD_CUTOFF_SQL})"
    ]

    parametros = {}

    if anio is not None:
        filtros.append("d.year = :anio")
        parametros["anio"] = int(anio)

    if trimestre is not None:
        filtros.append("d.quarter = :trimestre")
        parametros["trimestre"] = int(trimestre)

    if mes is not None:
        filtros.append("d.month = :mes")
        parametros["mes"] = int(mes)

    # Aplicar el filtro de estado según la opción seleccionada.
    estados_excluidos = ["canceled", "unavailable"]

    if estado in (None, "__todos__"):
        filtros.append(
            "(s.order_status IS NULL OR "
            "LOWER(TRIM(s.order_status)) NOT IN "
            "('canceled', 'unavailable'))"
        )

    elif estado == "__entregado__":
        filtros.append(
            "LOWER(TRIM(s.order_status)) = 'delivered'"
        )

    elif estado == "__en_proceso__":
        filtros.append(
            "(s.order_status IS NULL OR "
            "(LOWER(TRIM(s.order_status)) NOT IN "
            "('delivered', 'canceled', 'unavailable')))"
        )

    else:
        # Compatibilidad con llamadas anteriores que envíen
        # un estado específico de la base.
        filtros.append("s.order_status = :estado")
        parametros["estado"] = estado

    # Ejecutar la consulta agrupada en PostgreSQL.
    consulta = text(f"""
        SELECT
            {", ".join(columnas)}
        FROM gld_sales_detail s
        INNER JOIN gld_date_dimension d
            ON s.order_purchase_date = d.date
        WHERE {" AND ".join(filtros)}
        GROUP BY {agrupacion}
        ORDER BY {agrupacion}
    """)

    df = pd.read_sql(
        consulta,
        engine,
        params=parametros
    )

    # Devolver los resultados resumidos y los nombres de las columnas.
    nombres = {
        g: dimensiones[g][1]
        for g in grupos
    }

    nombres.update({
        m: medidas[m][1]
        for m in metricas
    })

    df = df.rename(columns=nombres)

    return df
