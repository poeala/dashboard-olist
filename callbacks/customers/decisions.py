# Callbacks para la vista de toma de decisiones de clientes

import pandas as pd

from dash import Input, Output, State

from data.business import cargar_clientes_gold


def preparar_datos_clientes():
    """Carga y prepara los datos Gold de clientes."""

    df = cargar_clientes_gold().copy()

    # Convertir las fechas.
    for columna in ["first_purchase_date", "last_purchase_date"]:
        df[columna] = pd.to_datetime(df.get(columna, pd.Series(pd.NaT, index=df.index)), errors="coerce")

    # Convertir las métricas a valores numéricos.
    for columna in [
        "total_orders",
        "total_spent",
        "avg_review_score",
    ]:
        if columna in df.columns:
            df[columna] = pd.to_numeric(
                df[columna],
                errors="coerce"
            )
        else:
            df[columna] = pd.NA

    # Completar los segmentos sin información.
    if "customer_segment" not in df.columns:
        df["customer_segment"] = "Sin segmento"

    df["customer_segment"] = (
        df["customer_segment"]
        .fillna("Sin segmento")
        .astype(str)
    )

    # Completar identificadores faltantes si fuera necesario.
    if "customer_id" not in df.columns:
        df["customer_id"] = range(1, len(df) + 1)

    # Evitar contar varias veces al mismo cliente.
    df = df.drop_duplicates(
        subset=["customer_id"]
    )

    # Identificar clientes con más de una compra.
    df["cliente_recurrente"] = (
        df["total_orders"].fillna(0) > 1
    )

    return df


def registrar_callbacks_decisiones_clientes(app):

    meses = {
        1: "Enero",
        2: "Febrero",
        3: "Marzo",
        4: "Abril",
        5: "Mayo",
        6: "Junio",
        7: "Julio",
        8: "Agosto",
        9: "Septiembre",
        10: "Octubre",
        11: "Noviembre",
        12: "Diciembre",
    }

    # Cargar las opciones de los filtros.
    @app.callback(
        Output("decisiones_clientes_filtro_anio", "options"),
        Output("decisiones_clientes_filtro_anio", "value"),
        Input("selector_dashboard", "value"),
        State("decisiones_clientes_filtro_anio", "value"),
    )
    def cargar_anios(dashboard, anio_actual):
        df_base = preparar_datos_clientes()
        if "last_purchase_date" not in df_base.columns:
            return [{"label": "Todos", "value": "todos"}], "todos"

        anios = sorted(
            df_base["last_purchase_date"]
            .dropna()
            .dt.year
            .unique()
            .tolist()
        )

        opciones = [
            {"label": "Todos", "value": "todos"}
        ]

        opciones += [
            {"label": str(anio), "value": int(anio)}
            for anio in anios
        ]

        valores_validos = ["todos"] + anios

        if anio_actual not in valores_validos:
            anio_actual = "todos"

        return opciones, anio_actual

    @app.callback(
        Output("decisiones_clientes_filtro_mes", "options"),
        Output("decisiones_clientes_filtro_mes", "value"),
        Output("decisiones_clientes_filtro_mes", "disabled"),
        Input("decisiones_clientes_filtro_anio", "value"),
        State("decisiones_clientes_filtro_mes", "value"),
    )
    def cargar_meses(anio, mes_actual):

        if anio in (None, "todos"):
            return (
                [{"label": "Todos", "value": "todos"}],
                "todos",
                True,
            )

        fechas = preparar_datos_clientes()["last_purchase_date"].dropna()

        meses_disponibles = sorted(
            fechas[fechas.dt.year == int(anio)]
            .dt.month
            .unique()
            .tolist()
        )

        opciones = [
            {"label": "Todos", "value": "todos"}
        ]

        opciones += [
            {
                "label": meses[mes],
                "value": int(mes),
            }
            for mes in meses_disponibles
        ]

        valores_validos = ["todos"] + meses_disponibles

        if mes_actual not in valores_validos:
            mes_actual = "todos"

        return opciones, mes_actual, False

    @app.callback(
        Output("decisiones_clientes_tabla_hallazgos", "columns"),
        Output("decisiones_clientes_tabla_hallazgos", "data"),
        Output("decisiones_clientes_estado", "children"),
        Input("decisiones_clientes_filtro_anio", "value"),
        Input("decisiones_clientes_filtro_mes", "value"),
    )
    def actualizar_decisiones(anio, mes):
        df = preparar_datos_clientes()
        if anio not in (None, "todos"):
            df = df[df["last_purchase_date"].dt.year == int(anio)]
            if mes not in (None, "todos"):
                df = df[df["last_purchase_date"].dt.month == int(mes)]
        hallazgos = generar_intervenciones(df)
        columnas = [{"name": name, "id": name} for name in (
            "Prioridad", "Segmento", "Clientes alcanzados", "Hallazgo",
            "Evidencia", "Acción sugerida", "Seguimiento",
        )]
        if df.empty:
            estado = "No hay clientes para los filtros seleccionados."
        elif not hallazgos:
            estado = "Sin intervenciones que cumplan los umbrales y el mínimo de casos. Esto no equivale a ausencia de problemas."
        else:
            estado = f"{len(hallazgos)} intervenciones para revisar, ordenadas por prioridad."
        return columnas, hallazgos, estado


def generar_intervenciones(df, minimo=20):
    """Reglas sobre clientes Gold; no reinterpretar el historial como un período."""
    if df.empty:
        return []
    df = df.drop_duplicates("customer_id").copy()
    for columna in ("total_orders", "total_spent", "avg_review_score"):
        df[columna] = pd.to_numeric(df[columna], errors="coerce")
    df["customer_segment"] = df["customer_segment"].fillna("Sin segmento")
    gastos = df.loc[df["total_spent"].ge(0), "total_spent"]
    umbral = gastos.quantile(.75)
    hallazgos = []

    def agregar(prioridad, segmento, clientes, hallazgo, evidencia, accion, seguimiento):
        hallazgos.append(dict(zip(
            ("Prioridad", "Segmento", "Clientes alcanzados", "Hallazgo", "Evidencia", "Acción sugerida", "Seguimiento"),
            (prioridad, segmento, int(clientes), hallazgo, evidencia, accion, seguimiento),
        )))

    for segmento, grupo in df.groupby("customer_segment", sort=True):
        resenas = grupo.loc[grupo["avg_review_score"].between(1, 5), "avg_review_score"]
        if len(resenas) >= minimo and resenas.mean() <= 3.5:
            agregar(
                "Alta" if resenas.mean() <= 3 else "Media", segmento, len(resenas),
                "Baja satisfacción",
                f"Media de promedios por cliente: {resenas.mean():.2f}/5; "
                f"{len(resenas)} de {len(grupo)} clientes con calificación válida.",
                "Revisar reseñas, entregas y categorías del segmento; priorizar la resolución de los problemas identificados.",
                "Comparar calificaciones y motivos de reclamo después de la intervención.",
            )
        pedidos = grupo.loc[grupo["total_orders"].ge(1), "total_orders"]
        recurrentes = int(pedidos.ge(2).sum())
        tasa = recurrentes / len(pedidos) * 100 if len(pedidos) else None
        if len(pedidos) >= minimo and tasa < 25:
            agregar(
                "Media", segmento, len(pedidos), "Baja recurrencia",
                f"{recurrentes} de {len(pedidos)} clientes con pedidos válidos "
                f"tienen al menos dos compras ({tasa:.1f} %; umbral < 25 %).",
                "Comparar cohortes con igual tiempo de observación y probar una campaña de segunda compra en el segmento.",
                "Medir segunda compra en una ventana común y comparar con un grupo de control.",
            )
        oportunidad = grupo[grupo["total_orders"].eq(1) & grupo["total_spent"].ge(umbral)]
        if len(oportunidad) >= minimo and pd.notna(umbral) and umbral > 0:
            agregar(
                "Media", segmento, len(oportunidad), "Alto gasto con compra única",
                f"{len(oportunidad)} clientes con una compra y gasto histórico ≥ R$ {umbral:,.2f} "
                "(percentil 75 de clientes filtrados con gasto válido).",
                "Evaluar una propuesta de segunda compra adecuada a las categorías adquiridas y probarla en un grupo acotado.",
                "Comparar conversión a segunda compra y margen incremental con un grupo de control.",
            )
    return sorted(hallazgos, key=lambda h: (
        0 if h["Prioridad"] == "Alta" else 1,
        -h["Clientes alcanzados"], h["Segmento"], h["Hallazgo"],
    ))
