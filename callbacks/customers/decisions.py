# Callbacks para la vista de toma de decisiones de clientes

import pandas as pd
import plotly.express as px

from dash import Input, Output, State

from data.business import cargar_clientes_gold


def preparar_datos_clientes():
    """Carga y prepara los datos Gold de clientes."""

    df = cargar_clientes_gold().copy()

    # Convertir las fechas.
    for columna in ["first_purchase_date", "last_purchase_date"]:
        if columna in df.columns:
            df[columna] = pd.to_datetime(
                df[columna],
                errors="coerce"
            )

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

    df_base = preparar_datos_clientes()

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

        fechas = df_base["last_purchase_date"].dropna()

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

    # Actualizar indicadores, gráficos y hallazgos.
    @app.callback(
        Output("decisiones_clientes_total", "children"),
        Output("decisiones_clientes_recurrentes", "children"),
        Output("decisiones_clientes_gasto_promedio", "children"),
        Output("decisiones_clientes_resena_promedio", "children"),
        Output("decisiones_clientes_grafico_segmentos", "figure"),
        Output("decisiones_clientes_grafico_gasto", "figure"),
        Output("decisiones_clientes_tabla_hallazgos", "columns"),
        Output("decisiones_clientes_tabla_hallazgos", "data"),
        Input("selector_dashboard", "value"),
        Input("selector_vista", "value"),
        Input("decisiones_clientes_filtro_anio", "value"),
        Input("decisiones_clientes_filtro_mes", "value"),
    )
    def actualizar_decisiones(
        dashboard,
        vista,
        anio,
        mes,
    ):

        df = df_base.copy()

        # Aplicar los filtros de última compra.
        if anio not in (None, "todos"):
            df = df[
                df["last_purchase_date"].dt.year == int(anio)
            ]

        if (
            anio not in (None, "todos")
            and mes not in (None, "todos")
        ):
            df = df[
                df["last_purchase_date"].dt.month == int(mes)
            ]

        total_clientes = df["customer_id"].nunique()

        clientes_recurrentes = df.loc[
            df["cliente_recurrente"],
            "customer_id",
        ].nunique()

        porcentaje_recurrentes = (
            clientes_recurrentes / total_clientes * 100
            if total_clientes
            else 0
        )

        gasto_promedio = df["total_spent"].mean()
        resena_promedio = df["avg_review_score"].mean()

        def formato_moneda(valor):
            if pd.isna(valor):
                return "N/D"

            valor = f"{valor:,.2f}"
            valor = valor.replace(",", "X")
            valor = valor.replace(".", ",")
            valor = valor.replace("X", ".")

            return f"R$ {valor}"

        # Indicadores.
        texto_total = f"{total_clientes:,}".replace(",", ".")
        texto_recurrentes = f"{porcentaje_recurrentes:.1f}%"
        texto_gasto = formato_moneda(gasto_promedio)

        texto_resena = (
            f"{resena_promedio:.2f}/5"
            if pd.notna(resena_promedio)
            else "N/D"
        )

        # Gráfico 1: cantidad de clientes por segmento.
        datos_segmentos = (
            df.groupby("customer_segment")
            .agg(
                Clientes=("customer_id", "nunique")
            )
            .reset_index()
            .sort_values("Clientes", ascending=False)
        )

        fig_segmentos = px.bar(
            datos_segmentos,
            x="customer_segment",
            y="Clientes",
            title="Cantidad de clientes por segmento",
            labels={
                "customer_segment": "Segmento",
                "Clientes": "Cantidad de clientes",
            },
            text="Clientes",
        )

        fig_segmentos.update_layout(
            template="plotly_white",
            showlegend=False,
            margin=dict(l=30, r=20, t=60, b=50),
        )

        fig_segmentos.update_traces(
            textposition="outside",
            cliponaxis=False,
        )

        # Gráfico 2: gasto promedio por segmento.
        datos_gasto = (
            df.groupby("customer_segment")
            .agg(
                Gasto_promedio=("total_spent", "mean"),
                Clientes=("customer_id", "nunique"),
            )
            .reset_index()
            .sort_values("Gasto_promedio", ascending=True)
        )

        fig_gasto = px.bar(
            datos_gasto,
            x="Gasto_promedio",
            y="customer_segment",
            orientation="h",
            title="Gasto promedio por cliente y segmento",
            labels={
                "customer_segment": "Segmento",
                "Gasto_promedio": "Gasto promedio (R$)",
                "Clientes": "Cantidad de clientes",
            },
            hover_data=["Clientes"],
        )

        fig_gasto.update_layout(
            template="plotly_white",
            showlegend=False,
            margin=dict(l=30, r=30, t=60, b=40),
        )

        # Preparar hallazgos.
        hallazgos = []

        # Hallazgo 1: clientes con gasto acumulado alto.
        if not df.empty and df["total_spent"].notna().any():

            umbral_gasto = df["total_spent"].quantile(0.75)

            clientes_alto_gasto = df[
                df["total_spent"] >= umbral_gasto
            ]

            if not clientes_alto_gasto.empty:
                hallazgos.append({
                    "Prioridad": "Media",
                    "Hallazgo": "Clientes con gasto acumulado alto",
                    "Evidencia": (
                        f"{len(clientes_alto_gasto)} clientes tienen un "
                        f"gasto acumulado igual o superior a "
                        f"{formato_moneda(umbral_gasto)}."
                    ),
                    "Acción sugerida": (
                        "Analizar sus segmentos y frecuencia de compra "
                        "para identificar oportunidades de fidelización."
                    ),
                })

        # Hallazgo 2: segmentos con baja recurrencia.
        datos_recurrencia = (
            df.groupby("customer_segment")
            .agg(
                Clientes=("customer_id", "nunique"),
                Recurrentes=("cliente_recurrente", "sum"),
            )
            .reset_index()
        )

        if not datos_recurrencia.empty:

            datos_recurrencia["Porcentaje"] = (
                datos_recurrencia["Recurrentes"]
                / datos_recurrencia["Clientes"].replace(0, pd.NA)
                * 100
            )

            segmentos_baja_recurrencia = datos_recurrencia[
                (datos_recurrencia["Clientes"] >= 20)
                & (datos_recurrencia["Porcentaje"] < 25)
            ]

            for _, fila in segmentos_baja_recurrencia.iterrows():
                hallazgos.append({
                    "Prioridad": "Media",
                    "Hallazgo": (
                        f"Baja recurrencia en {fila['customer_segment']}"
                    ),
                    "Evidencia": (
                        f"{fila['Porcentaje']:.1f}% de recurrencia "
                        f"entre {int(fila['Clientes'])} clientes."
                    ),
                    "Acción sugerida": (
                        "Revisar la frecuencia de compra y evaluar "
                        "acciones de fidelización para el segmento."
                    ),
                })

        # Hallazgo 3: segmentos con puntuación promedio baja.
        datos_resenas = (
            df.groupby("customer_segment")
            .agg(
                Clientes=("customer_id", "nunique"),
                Puntuacion=("avg_review_score", "mean"),
            )
            .reset_index()
        )

        segmentos_resenas_bajas = datos_resenas[
            (datos_resenas["Clientes"] >= 20)
            & (datos_resenas["Puntuacion"].notna())
            & (datos_resenas["Puntuacion"] <= 3.5)
        ]

        for _, fila in segmentos_resenas_bajas.iterrows():
            hallazgos.append({
                "Prioridad": "Media",
                "Hallazgo": (
                    f"Puntuación baja en {fila['customer_segment']}"
                ),
                "Evidencia": (
                    f"Puntuación promedio de "
                    f"{fila['Puntuacion']:.2f}/5 "
                    f"en {int(fila['Clientes'])} clientes."
                ),
                "Acción sugerida": (
                    "Revisar las reseñas y analizar posibles problemas "
                    "en la experiencia de compra."
                ),
            })

        columnas = [
            {"name": "Prioridad", "id": "Prioridad"},
            {"name": "Hallazgo", "id": "Hallazgo"},
            {"name": "Evidencia", "id": "Evidencia"},
            {"name": "Acción sugerida", "id": "Acción sugerida"},
        ]

        return (
            texto_total,
            texto_recurrentes,
            texto_gasto,
            texto_resena,
            fig_segmentos,
            fig_gasto,
            columnas,
            hallazgos,
        )