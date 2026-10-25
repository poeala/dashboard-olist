# Consultar ventas, enriquecerlas con calendario y cargar pagos por separado
import pandas as pd
from sqlalchemy import text

from data.database import engine
from data.definitions import PERIOD_CUTOFF_SQL
from data.query_cache import read_sql_cached


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

    df = read_sql_cached(consulta, engine)

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

    df["order_status"] = (
        df["order_status"].fillna("Sin estado")
    )

    df["review_score"] = pd.to_numeric(
        df["review_score"],
        errors="coerce"
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

    df = read_sql_cached(consulta, engine)

    # Normalizar las columnas numéricas.
    df["payment_value"] = pd.to_numeric(
        df["payment_value"],
        errors="coerce"
    )

    df["payment_installments"] = pd.to_numeric(
        df["payment_installments"],
        errors="coerce"
    )

    df["payment_type"] = df["payment_type"].fillna(
        "Sin información"
    )

    return df


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
        "mes": (
            "TO_CHAR(s.order_purchase_date, 'YYYY-MM')",
            "Mes"
        ),
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
        "pedidos": (
            "COUNT(DISTINCT s.order_id)",
            "Pedidos únicos"
        ),
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

    # Aplicar el filtro de estado.
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

    df = read_sql_cached(
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

    return df.rename(columns=nombres)


def consultar_detalle_ventas_agrupadas(
    dimension,
    valor_dimension,
    dimension_secundaria=None,
    valor_dimension_secundaria=None,
    anio=None,
    estado=None,
    limite=5000
):
    # Definir las dimensiones permitidas.
    dimensiones = {
        "anio": "d.year",
        "trimestre": "d.quarter",
        "mes": "TO_CHAR(s.order_purchase_date, 'YYYY-MM')",
        "fecha": "s.order_purchase_date",
        "categoria": (
            "COALESCE(s.product_category_name, 'Sin categoría')"
        ),
        "vendedor": "s.seller_id",
        "estado": "COALESCE(s.order_status, 'Sin estado')"
    }

    if dimension not in dimensiones:
        raise ValueError("Dimensión principal no válida")

    if (
        dimension_secundaria
        and dimension_secundaria != dimension
        and dimension_secundaria not in dimensiones
    ):
        raise ValueError("Dimensión secundaria no válida")

    # Preparar los filtros de la consulta.
    filtros = [
        f"s.order_purchase_date < ({PERIOD_CUTOFF_SQL})"
    ]

    parametros = {}

    if anio is not None:
        filtros.append("d.year = :anio")
        parametros["anio"] = int(anio)

    # Aplicar el filtro general de estado.
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
            "LOWER(TRIM(s.order_status)) NOT IN "
            "('delivered', 'canceled', 'unavailable'))"
        )

    else:
        filtros.append("s.order_status = :estado")
        parametros["estado"] = estado

    # Agregar el filtro correspondiente a una dimensión.
    def agregar_filtro_dimension(nombre, valor, parametro):
        expresion = dimensiones[nombre]

        # Comparar con NULL cuando la dimensión no tiene valor.
        if valor is None:
            filtros.append(f"{expresion} IS NULL")
            return

        if nombre in ("anio", "trimestre"):
            filtros.append(f"{expresion} = :{parametro}")
            parametros[parametro] = int(valor)

        elif nombre == "fecha":
            filtros.append(
                f"{expresion} = CAST(:{parametro} AS DATE)"
            )
            parametros[parametro] = str(valor)[:10]

        else:
            filtros.append(f"{expresion} = :{parametro}")
            parametros[parametro] = str(valor)

    agregar_filtro_dimension(
        dimension,
        valor_dimension,
        "valor_dimension"
    )

    # Aplicar la agrupación secundaria si corresponde.
    if (
        dimension_secundaria
        and dimension_secundaria != dimension
    ):
        agregar_filtro_dimension(
            dimension_secundaria,
            valor_dimension_secundaria,
            "valor_dimension_secundaria"
        )

    # Consultar los artículos que originan la agrupación.
    consulta = text(f"""
        SELECT
            s.order_id,
            s.order_item_id,
            s.order_purchase_date,
            s.order_purchase_time,
            s.product_id,
            s.customer_unique_id,
            s.seller_id,
            COALESCE(
                s.product_category_name,
                'Sin categoría'
            ) AS product_category_name,
            COALESCE(
                s.order_status,
                'Sin estado'
            ) AS order_status,
            s.price,
            s.freight_value,
            s.item_total_value,
            s.review_score
        FROM gld_sales_detail s
        INNER JOIN gld_date_dimension d
            ON s.order_purchase_date = d.date
        WHERE {" AND ".join(filtros)}
        ORDER BY
            s.order_purchase_date DESC,
            s.order_id,
            s.order_item_id
        LIMIT :limite
    """)

    parametros["limite"] = int(limite)

    df = read_sql_cached(
        consulta,
        engine,
        params=parametros
    )

    # Asignar nombres legibles a las columnas.
    df = df.rename(columns={
        "order_id": "Pedido",
        "order_item_id": "N.º de artículo",
        "order_purchase_date": "Fecha",
        "order_purchase_time": "Hora",
        "product_id": "Producto",
        "customer_unique_id": "Comprador",
        "seller_id": "Vendedor",
        "product_category_name": "Categoría",
        "order_status": "Estado",
        "price": "Precio",
        "freight_value": "Costo de envío",
        "item_total_value": "Total del artículo",
        "review_score": "Calificación"
    })

    # Convertir las fechas y horas para mostrarlas en Dash.
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(
            df["Fecha"],
            errors="coerce"
        ).dt.strftime("%Y-%m-%d")

    if "Hora" in df.columns:
        df["Hora"] = df["Hora"].apply(
            lambda valor: (
                str(valor) if pd.notna(valor) else None
            )
        )

    return df
