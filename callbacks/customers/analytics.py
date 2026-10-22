# Callbacks para la vista analítica de clientes
import io
import logging

import pandas as pd
import plotly.express as px

from dash import Input, Output, State, ctx, html
from dash.dash_table.Format import Format, Scheme
from dash.exceptions import PreventUpdate

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)
from reportlab.lib.styles import getSampleStyleSheet

from data.business import cargar_clientes_gold
from components.customer_analysis import customer_analysis

logger = logging.getLogger(__name__)

TODOS = "__todos__"
NINGUNA = "__ninguna__"

DIMENSIONES = {
    "gold_segment": {
        "label": "Segmento histórico",
        "columna": "customer_segment",
    },
    "anio_ultima_compra": {
        "label": "Año de última compra",
        "columna": "anio_ultima_compra",
    },
    "preferred_payment_type": {
        "label": "Tipo de pago preferido",
        "columna": "preferred_payment_type",
    },
}

METRICAS = {
    "clientes": {
        "label": "Cantidad de clientes",
        "columna": "customer_id",
        "agregacion": "nunique",
    },
    "total_orders": {
        "label": "Total de pedidos",
        "columna": "total_orders",
        "agregacion": "sum",
    },
    "total_spent": {
        "label": "Gasto total",
        "columna": "total_spent",
        "agregacion": "sum",
    },
    "avg_review_score": {
        "label": "Calificación promedio",
        "columna": "avg_review_score",
        "agregacion": "mean",
    },
}

COLUMNAS_DETALLE = [
    ("customer_id", "Cliente"),
    ("customer_segment", "Segmento histórico"),
    ("last_purchase_date", "Última compra"),
    ("preferred_payment_type", "Pago preferido"),
    ("total_orders", "Total de pedidos"),
    ("total_spent", "Gasto total"),
    ("avg_review_score", "Calificación promedio"),
]


def _preparar_datos():
    """Carga la tabla Gold y prepara el año de última compra."""
    df = cargar_clientes_gold().copy()

    if df.empty:
        return df

    df["first_purchase_date"] = pd.to_datetime(
        df["first_purchase_date"],
        errors="coerce",
    )
    df["last_purchase_date"] = pd.to_datetime(
        df["last_purchase_date"],
        errors="coerce",
    )

    df["anio_ultima_compra"] = (
        df["last_purchase_date"]
        .dt.year
        .astype("Int64")
        .astype("string")
    )

    return df


def _filtrar_texto(df, dimension, texto):
    """Filtra los datos por el texto de una dimensión."""
    if df.empty or dimension not in DIMENSIONES:
        return df

    if texto is None or not str(texto).strip():
        return df

    columna = DIMENSIONES[dimension]["columna"]
    texto = str(texto).strip()

    return df[
        df[columna]
        .fillna("")
        .astype(str)
        .str.contains(texto, case=False, regex=False)
    ]


def _filtrar_dimensiones(df, dimension, secundaria, filtro_principal, filtro_secundario):
    """Aplica los filtros de la agrupación principal y la secundaria."""
    df = _filtrar_texto(df, dimension, filtro_principal)

    if secundaria in DIMENSIONES and secundaria != dimension:
        df = _filtrar_texto(df, secundaria, filtro_secundario)

    return df


def _agrupar(df, dimension, secundaria, metricas):
    """Agrupa por una o dos dimensiones y calcula los indicadores."""
    if df.empty:
        return pd.DataFrame()

    columnas_grupo = [DIMENSIONES[dimension]["columna"]]

    usar_secundaria = (
        secundaria in DIMENSIONES
        and secundaria != dimension
    )

    if usar_secundaria:
        columnas_grupo.append(DIMENSIONES[secundaria]["columna"])

    agregaciones = {}

    for metrica in metricas:
        definicion = METRICAS[metrica]
        columna = definicion["columna"]

        if columna in df.columns:
            agregaciones[metrica] = (
                columna,
                definicion["agregacion"],
            )

    if not agregaciones:
        return pd.DataFrame()

    agrupado = (
        df.groupby(columnas_grupo, dropna=False)
        .agg(**agregaciones)
        .reset_index()
    )

    nombres = {
        DIMENSIONES[dimension]["columna"]:
            DIMENSIONES[dimension]["label"]
    }

    if usar_secundaria:
        nombres[DIMENSIONES[secundaria]["columna"]] = (
            DIMENSIONES[secundaria]["label"]
        )

    nombres.update({
        metrica: METRICAS[metrica]["label"]
        for metrica in agregaciones
    })

    agrupado = agrupado.rename(columns=nombres)

    # Calcular variaciones únicamente cuando la agrupación principal es temporal.
    if dimension == "anio_ultima_compra":
        agrupado["_anio_orden"] = pd.to_numeric(
            agrupado["Año de última compra"],
            errors="coerce",
        )

        columnas_variacion = (
            [DIMENSIONES[secundaria]["label"]]
            if usar_secundaria
            else []
        )

        agrupado = agrupado.sort_values(
            columnas_variacion + ["_anio_orden"],
            na_position="last",
        )

        for metrica in metricas:
            etiqueta = METRICAS[metrica]["label"]

            if etiqueta not in agrupado.columns:
                continue

            if columnas_variacion:
                agrupado[f"{etiqueta} - Variación"] = (
                    agrupado.groupby(
                        columnas_variacion,
                        dropna=False,
                    )[etiqueta].diff()
                )

                anterior = (
                    agrupado.groupby(
                        columnas_variacion,
                        dropna=False,
                    )[etiqueta].shift(1)
                )
            else:
                agrupado[f"{etiqueta} - Variación"] = (
                    agrupado[etiqueta].diff()
                )

                anterior = agrupado[etiqueta].shift(1)

            agrupado[f"{etiqueta} - % variación"] = (
                (agrupado[etiqueta] - anterior)
                / anterior.where(anterior != 0)
                * 100
            )

        agrupado = agrupado.drop(columns=["_anio_orden"])

    else:
        # Para otras dimensiones no hay una secuencia temporal comparable.
        for metrica in metricas:
            etiqueta = METRICAS[metrica]["label"]
            agrupado[f"{etiqueta} - Variación"] = float("nan")
            agrupado[f"{etiqueta} - % variación"] = float("nan")

    return agrupado


def _calcular_total(df, dimension, secundaria, metricas):
    """Calcula los indicadores globales de los clientes filtrados."""
    total = {}

    for metrica in metricas:
        definicion = METRICAS[metrica]
        columna = definicion["columna"]
        etiqueta = definicion["label"]

        if columna not in df.columns:
            total[etiqueta] = float("nan")
            continue

        if definicion["agregacion"] == "nunique":
            total[etiqueta] = df[columna].nunique()
        elif definicion["agregacion"] == "sum":
            total[etiqueta] = df[columna].sum()
        elif definicion["agregacion"] == "mean":
            total[etiqueta] = df[columna].mean()
        else:
            total[etiqueta] = float("nan")

        total[f"{etiqueta} - Variación"] = float("nan")
        total[f"{etiqueta} - % variación"] = float("nan")

    total[DIMENSIONES[dimension]["label"]] = "TOTAL"

    if secundaria in DIMENSIONES and secundaria != dimension:
        total[DIMENSIONES[secundaria]["label"]] = ""

    return total


def _formatear_tabla(df):
    """Mantiene los valores numéricos y redondea los decimales."""
    resultado = df.copy()

    columnas_enteras = {
        "Cantidad de clientes",
        "Total de pedidos",
    }

    columnas_decimales = {
        "Gasto total",
        "Calificación promedio",
    }

    for columna in resultado.columns:
        es_variacion = (
            columna.endswith(" - Variación")
            or columna.endswith(" - % variación")
        )

        es_numerica = (
            columna in columnas_enteras
            or columna in columnas_decimales
            or es_variacion
        )

        if not es_numerica:
            continue

        resultado[columna] = pd.to_numeric(
            resultado[columna],
            errors="coerce",
        )

        if columna in columnas_decimales:
            resultado[columna] = resultado[columna].round(2)

        elif columna.endswith(" - % variación"):
            resultado[columna] = resultado[columna].round(2)

        elif columna.endswith(" - Variación"):
            metrica = columna.removesuffix(" - Variación")

            if metrica in columnas_decimales:
                resultado[columna] = resultado[columna].round(2)

    return resultado


def _ordenar_tabla_total_al_final(tabla, sort_by, dimension):
    """Ordena las filas de detalle y conserva TOTAL al final."""
    if tabla.empty:
        return tabla

    columna_dimension = DIMENSIONES[dimension]["label"]

    if columna_dimension not in tabla.columns:
        return tabla

    es_total = tabla[columna_dimension].eq("TOTAL")

    filas = tabla.loc[~es_total].copy()
    total = tabla.loc[es_total].copy()

    if sort_by:
        columnas = []
        direcciones = []

        for criterio in sort_by:
            columna = criterio.get("column_id")
            direccion = criterio.get("direction", "asc")

            if columna in filas.columns:
                columnas.append(columna)
                direcciones.append(direccion == "asc")

        if columnas:
            filas = filas.sort_values(
                by=columnas,
                ascending=direcciones,
                na_position="last",
                kind="mergesort",
            )

    return pd.concat(
        [filas, total],
        ignore_index=True,
    )


def _es_columna_numerica(columna):
    """Indica si una columna debe tratarse como numérica en Dash."""
    return (
        columna in {
            "Cantidad de clientes",
            "Total de pedidos",
            "Gasto total",
            "Calificación promedio",
        }
        or columna.endswith(" - Variación")
        or columna.endswith(" - % variación")
    )


def _es_columna_decimal(columna):
    """Indica las columnas que se muestran con dos decimales."""
    columnas_decimales = {
        "Gasto total",
        "Calificación promedio",
    }

    if columna in columnas_decimales:
        return True

    if columna.endswith(" - % variación"):
        return True

    if columna.endswith(" - Variación"):
        metrica = columna.removesuffix(" - Variación")
        return metrica in columnas_decimales

    return False


def _crear_pdf(titulo, tabla):
    """Genera un PDF con los resultados agrupados."""
    buffer = io.BytesIO()

    documento = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24,
    )

    estilos = getSampleStyleSheet()
    elementos = [
        Paragraph(titulo, estilos["Title"]),
        Spacer(1, 12),
    ]

    filas = [tabla.columns.tolist()]

    for _, fila in tabla.iterrows():
        filas.append([
            "—" if pd.isna(valor) else str(valor)
            for valor in fila.tolist()
        ])

    tabla_pdf = Table(filas, repeatRows=1)
    tabla_pdf.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#253858")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9DEE8")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F3F5F9"),
        ]),
    ]))

    elementos.append(tabla_pdf)
    documento.build(elementos)

    buffer.seek(0)
    return buffer.getvalue()


def registrar_callbacks_analitica_clientes(app):

    # Opciones de agrupación secundaria.
    @app.callback(
        Output("clientes_analitica_dimension_secundaria", "options"),
        Input("clientes_analitica_dimension", "value"),
    )
    def actualizar_opciones_secundarias(dimension):
        if dimension not in DIMENSIONES:
            dimension = "gold_segment"

        return [
            {"label": "Ninguna", "value": NINGUNA}
        ] + [
            {"label": definicion["label"], "value": clave}
            for clave, definicion in DIMENSIONES.items()
            if clave != dimension
        ]

    # Mostrar el segundo filtro solamente si hay una segunda agrupación.
    @app.callback(
        Output("clientes_contenedor_filtro_secundario", "style"),
        Input("clientes_analitica_dimension", "value"),
        Input("clientes_analitica_dimension_secundaria", "value"),
    )
    def mostrar_filtro_secundario(dimension, secundaria):
        usar_secundaria = (
            secundaria in DIMENSIONES
            and secundaria != dimension
        )

        if usar_secundaria:
            return {
                "flex": "1",
                "minWidth": "220px",
            }

        return {"display": "none"}

    # Limpiar los filtros al cambiar las agrupaciones o pulsar Limpiar.
    @app.callback(
        Output("clientes_filtro_dimension", "value"),
        Output("clientes_filtro_dimension_secundaria", "value"),
        Input("clientes_analitica_dimension", "value"),
        Input("clientes_analitica_dimension_secundaria", "value"),
        Input("clientes_btn_limpiar_filtros", "n_clicks"),
        prevent_initial_call=True,
    )
    def limpiar_filtros(dimension, secundaria, n_clicks):
        return "", ""

    @app.callback(
        Output("clientes_patrones_analitica", "children"),
        Input("clientes_analitica_dimension", "value"),
        Input("clientes_analitica_dimension_secundaria", "value"),
        Input("clientes_filtro_dimension", "value"),
        Input("clientes_filtro_dimension_secundaria", "value"),
    )
    def actualizar_patrones(dimension, secundaria, filtro_principal, filtro_secundario):
        try:
            df = _filtrar_dimensiones(
                _preparar_datos(), dimension, secundaria, filtro_principal, filtro_secundario,
            )
            return customer_analysis(df)
        except Exception:
            logger.exception("Error al actualizar patrones de clientes")
            return html.Div("No se pudieron cargar los patrones de clientes.", role="alert")

    # Tabla y gráfico.
    @app.callback(
        Output("clientes_tabla_analitica", "data"),
        Output("clientes_tabla_analitica", "columns"),
        Output("clientes_tabla_analitica", "active_cell"),
        Output("clientes_grafico_analitica", "figure"),
        Input("clientes_analitica_dimension", "value"),
        Input("clientes_analitica_dimension_secundaria", "value"),
        Input("clientes_analitica_metricas", "value"),
        Input("clientes_filtro_dimension", "value"),
        Input("clientes_filtro_dimension_secundaria", "value"),
        Input("clientes_tabla_analitica", "sort_by"),
    )
    def actualizar_analitica(
        dimension,
        secundaria,
        metricas,
        filtro_principal,
        filtro_secundario,
        sort_by,
    ):
        try:
            if dimension not in DIMENSIONES:
                dimension = "gold_segment"

            df = _preparar_datos()

            df = _filtrar_dimensiones(
                df,
                dimension,
                secundaria,
                filtro_principal,
                filtro_secundario,
            )

            metricas = [
                metrica
                for metrica in (metricas or [])
                if metrica in METRICAS
            ]

            if df.empty or not metricas:
                titulo = (
                    "No hay datos para mostrar"
                    if df.empty
                    else "Seleccioná al menos un indicador"
                )
                return [], [], None, px.bar(title=titulo)

            agrupado = _agrupar(
                df,
                dimension,
                secundaria,
                metricas,
            )

            if agrupado.empty:
                return [], [], None, px.bar(
                    title="No hay datos para mostrar"
                )

            # El gráfico no incluye la fila TOTAL.
            agrupado_grafico = agrupado.copy()

            # El total se calcula sobre los clientes que cumplen ambos filtros.
            total = _calcular_total(
                df,
                dimension,
                secundaria,
                metricas,
            )

            agrupado = pd.concat(
                [agrupado, pd.DataFrame([total])],
                ignore_index=True,
            )

            tabla = _formatear_tabla(agrupado)

            tabla = _ordenar_tabla_total_al_final(
                tabla,
                sort_by,
                dimension,
            )

            columnas = []

            for columna in tabla.columns:
                if _es_columna_numerica(columna):
                    precision = (
                        2 if _es_columna_decimal(columna) else 0
                    )

                    columnas.append({
                        "name": columna,
                        "id": columna,
                        "type": "numeric",
                        "format": Format(
                            precision=precision,
                            scheme=Scheme.fixed,
                        ),
                    })
                else:
                    columnas.append({
                        "name": columna,
                        "id": columna,
                    })

            metrica_grafico = METRICAS[metricas[0]]["label"]
            eje_x = DIMENSIONES[dimension]["label"]

            usar_secundaria = (
                secundaria in DIMENSIONES
                and secundaria != dimension
            )

            if usar_secundaria:
                eje_color = DIMENSIONES[secundaria]["label"]

                figura = px.bar(
                    agrupado_grafico,
                    x=eje_x,
                    y=metrica_grafico,
                    color=eje_color,
                    barmode="group",
                    title=(
                        f"{metrica_grafico} por "
                        f"{eje_x} y {eje_color}"
                    ),
                    text_auto=".2s",
                )
            else:
                figura = px.bar(
                    agrupado_grafico,
                    x=eje_x,
                    y=metrica_grafico,
                    title=f"{metrica_grafico} por {eje_x}",
                    text_auto=".2s",
                )

            figura.update_layout(
                template="plotly_white",
                margin=dict(l=20, r=20, t=60, b=40),
                legend_title_text="",
            )

            return tabla.to_dict("records"), columnas, None, figura

        except Exception:
            logger.exception("Error al actualizar analítica de clientes")
            return [], [], None, px.bar(
                title="No se pudo generar el análisis"
            )

    # Mostrar u ocultar el detalle.
    @app.callback(
        Output("clientes_contenedor_detalle_analitica", "style"),
        Output("clientes_tabla_detalle_analitica", "data"),
        Output("clientes_tabla_detalle_analitica", "columns"),
        Output("clientes_texto_detalle_analitica", "children"),
        Output("clientes_btn_detalle_analitica", "children"),
        Output("clientes_btn_detalle_analitica", "disabled"),
        Output("clientes_btn_detalle_analitica", "style"),
        Output("clientes_estado_detalle_analitica", "data"),
        Input("clientes_tabla_analitica", "active_cell"),
        Input("clientes_btn_detalle_analitica", "n_clicks"),
        State("clientes_tabla_analitica", "derived_viewport_data"),
        State("clientes_analitica_dimension", "value"),
        State("clientes_analitica_dimension_secundaria", "value"),
        State("clientes_filtro_dimension", "value"),
        State("clientes_filtro_dimension_secundaria", "value"),
        State("clientes_estado_detalle_analitica", "data"),
        prevent_initial_call=True,
    )
    def actualizar_detalle(
        active_cell,
        n_clicks,
        filas_visibles,
        dimension,
        secundaria,
        filtro_principal,
        filtro_secundario,
        estado_detalle,
    ):
        estilo_base = {
            "backgroundColor": "#003D7C",
            "color": "white",
            "border": "none",
            "borderRadius": "6px",
            "padding": "9px 14px",
            "fontSize": "12px",
            "fontWeight": "600",
            "cursor": "pointer",
        }

        estilo_oculto = {"display": "none"}

        estilo_visible = {
            "backgroundColor": "white",
            "padding": "12px",
            "borderRadius": "8px",
            "marginBottom": "14px",
            "boxShadow": "0 1px 5px #dddddd",
        }

        if dimension not in DIMENSIONES:
            dimension = "gold_segment"

        filas_visibles = filas_visibles or []
        fila = None

        if active_cell and filas_visibles:
            indice = active_cell.get("row")

            if indice is not None and 0 <= indice < len(filas_visibles):
                fila = filas_visibles[indice]

        if fila is None or fila.get(
            DIMENSIONES[dimension]["label"]
        ) == "TOTAL":
            return (
                estilo_oculto,
                [],
                [],
                "Seleccioná una fila para ver el detalle.",
                "Mostrar detalle",
                True,
                {
                    **estilo_base,
                    "backgroundColor": "#d1d5db",
                    "color": "#6b7280",
                    "cursor": "not-allowed",
                },
                None,
            )

        clave_fila = {
            "dimension": dimension,
            "secundaria": secundaria,
            "fila": fila,
        }

        if ctx.triggered_id == "clientes_tabla_analitica":
            return (
                estilo_oculto,
                [],
                [],
                "Seleccioná Mostrar detalle para abrir el grupo.",
                "Mostrar detalle",
                False,
                estilo_base,
                None,
            )

        if estado_detalle == clave_fila:
            return (
                estilo_oculto,
                [],
                [],
                "El detalle está cerrado.",
                "Mostrar detalle",
                False,
                estilo_base,
                None,
            )

        try:
            df = _preparar_datos()

            df = _filtrar_dimensiones(
                df,
                dimension,
                secundaria,
                filtro_principal,
                filtro_secundario,
            )

            dimensiones_grupo = [dimension]

            if secundaria in DIMENSIONES and secundaria != dimension:
                dimensiones_grupo.append(secundaria)

            for clave in dimensiones_grupo:
                columna = DIMENSIONES[clave]["columna"]
                etiqueta = DIMENSIONES[clave]["label"]
                valor = fila.get(etiqueta)

                if columna not in df.columns:
                    continue

                if valor is None or pd.isna(valor):
                    df = df[df[columna].isna()]
                else:
                    df = df[
                        df[columna].fillna("").astype(str) == str(valor)
                    ]

            columnas_disponibles = [
                (origen, destino)
                for origen, destino in COLUMNAS_DETALLE
                if origen in df.columns
            ]

            if not columnas_disponibles:
                return (
                    estilo_visible,
                    [],
                    [],
                    "No hay columnas disponibles para el detalle.",
                    "Quitar detalle",
                    False,
                    estilo_base,
                    clave_fila,
                )

            detalle = df[
                [origen for origen, _ in columnas_disponibles]
            ].copy()

            if "last_purchase_date" in detalle.columns:
                detalle["last_purchase_date"] = (
                    pd.to_datetime(
                        detalle["last_purchase_date"],
                        errors="coerce",
                    ).dt.strftime("%Y-%m-%d")
                )

            detalle = detalle.rename(
                columns=dict(columnas_disponibles)
            )

            if "Gasto total" in detalle.columns:
                detalle["Gasto total"] = detalle["Gasto total"].map(
                    lambda valor: (
                        f"$ {valor:,.2f}"
                        if pd.notna(valor)
                        else "—"
                    )
                )

            if "Calificación promedio" in detalle.columns:
                detalle["Calificación promedio"] = (
                    detalle["Calificación promedio"].map(
                        lambda valor: (
                            f"{valor:.2f}"
                            if pd.notna(valor)
                            else "—"
                        )
                    )
                )

            columnas = [
                {"name": destino, "id": destino}
                for _, destino in columnas_disponibles
            ]

            return (
                estilo_visible,
                detalle.to_dict("records"),
                columnas,
                f"Clientes incluidos en el grupo seleccionado: {len(detalle)}.",
                "Quitar detalle",
                False,
                estilo_base,
                clave_fila,
            )

        except Exception:
            logger.exception("Error al cargar el detalle de clientes")
            return (
                estilo_visible,
                [],
                [],
                "No se pudo cargar el detalle.",
                "Quitar detalle",
                False,
                estilo_base,
                None,
            )

    # Exportar la tabla agrupada a PDF.
    @app.callback(
        Output("clientes_descargar_analitica_pdf", "data"),
        Input("clientes_btn_exportar_analitica_pdf", "n_clicks"),
        State("clientes_tabla_analitica", "data"),
        State("clientes_tabla_analitica", "columns"),
        prevent_initial_call=True,
    )
    def exportar_pdf(n_clicks, datos, columnas):
        if not n_clicks or not datos or not columnas:
            raise PreventUpdate

        tabla = pd.DataFrame(datos)
        orden = [columna["id"] for columna in columnas]
        tabla = tabla[
            [columna for columna in orden if columna in tabla.columns]
        ]

        contenido = _crear_pdf("Analítica de clientes", tabla)

        return {
            "content": contenido,
            "filename": "analitica_clientes.pdf",
            "type": "application/pdf",
            "base64": False,
        }