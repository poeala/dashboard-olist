# Callbacks para la vista analítica de clientes
import io
import logging

import pandas as pd
import plotly.express as px

from dash import Input, Output, State, ctx
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
        df["first_purchase_date"], errors="coerce"
    )
    df["last_purchase_date"] = pd.to_datetime(
        df["last_purchase_date"], errors="coerce"
    )

    df["anio_ultima_compra"] = (
        df["last_purchase_date"]
        .dt.year
        .astype("Int64")
        .astype("string")
    )

    return df


def _filtrar_texto(df, dimension, texto):
    """Filtra por texto sobre la dimensión principal."""
    if not texto or not str(texto).strip():
        return df

    columna = DIMENSIONES[dimension]["columna"]
    texto = str(texto).strip()

    return df[
        df[columna]
        .fillna("")
        .astype(str)
        .str.contains(texto, case=False, regex=False)
    ]


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

    return agrupado.rename(columns=nombres)


def _formatear_tabla(df):
    """Da formato a los indicadores para mostrarlos en pantalla."""
    resultado = df.copy()

    for columna in resultado.columns:
        if columna == "Gasto total":
            resultado[columna] = resultado[columna].map(
                lambda valor: (
                    f"$ {valor:,.2f}" if pd.notna(valor) else "—"
                )
            )

        elif columna == "Calificación promedio":
            resultado[columna] = resultado[columna].map(
                lambda valor: (
                    f"{valor:.2f}" if pd.notna(valor) else "—"
                )
            )

        elif columna in {"Cantidad de clientes", "Total de pedidos"}:
            resultado[columna] = resultado[columna].map(
                lambda valor: (
                    f"{valor:,.0f}" if pd.notna(valor) else "—"
                )
            )

    return resultado


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

    # Opciones de agrupación secundaria: ninguna o una dimensión distinta.
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

    # Limpiar la búsqueda al cambiar las agrupaciones o pulsar el botón.
    @app.callback(
        Output("clientes_filtro_dimension", "value"),
        Input("clientes_analitica_dimension", "value"),
        Input("clientes_analitica_dimension_secundaria", "value"),
        Input("clientes_btn_limpiar_filtros", "n_clicks"),
        prevent_initial_call=True,
    )
    def limpiar_filtros(dimension, secundaria, n_clicks):
        return ""

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
    )
    def actualizar_analitica(dimension, secundaria, metricas, filtro_texto):
        try:
            if dimension not in DIMENSIONES:
                dimension = "gold_segment"

            df = _preparar_datos()
            df = _filtrar_texto(df, dimension, filtro_texto)

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
                return [], [], None, px.bar(title="No hay datos para mostrar")

            tabla = _formatear_tabla(agrupado)

            columnas = [
                {"name": columna, "id": columna}
                for columna in tabla.columns
            ]

            metrica_grafico = METRICAS[metricas[0]]["label"]
            eje_x = DIMENSIONES[dimension]["label"]

            usar_secundaria = (
                secundaria in DIMENSIONES
                and secundaria != dimension
            )

            if usar_secundaria:
                eje_color = DIMENSIONES[secundaria]["label"]

                figura = px.bar(
                    agrupado,
                    x=eje_x,
                    y=metrica_grafico,
                    color=eje_color,
                    barmode="group",
                    title=f"{metrica_grafico} por {eje_x} y {eje_color}",
                    text_auto=".2s",
                )
            else:
                figura = px.bar(
                    agrupado,
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

            # Reiniciar la selección cuando cambia la tabla.
            return tabla.to_dict("records"), columnas, None, figura

        except Exception:
            logger.exception("Error al actualizar analítica de clientes")
            return [], [], None, px.bar(title="No se pudo generar el análisis")

    # Mostrar u ocultar el detalle; cambiar de fila cierra el anterior.
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
        State("clientes_estado_detalle_analitica", "data"),
        prevent_initial_call=True,
    )
    def actualizar_detalle(
        active_cell,
        n_clicks,
        filas_visibles,
        dimension,
        secundaria,
        filtro_texto,
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

        if fila is None:
            return (
                estilo_oculto, [], [], "Seleccioná una fila para ver el detalle.",
                "Mostrar detalle", True,
                {**estilo_base, "backgroundColor": "#d1d5db",
                 "color": "#6b7280", "cursor": "not-allowed"},
                None,
            )

        clave_fila = {
            "dimension": dimension,
            "secundaria": secundaria,
            "fila": fila,
        }

        # Al cambiar de fila, cerrar el detalle anterior.
        if ctx.triggered_id == "clientes_tabla_analitica":
            return (
                estilo_oculto, [], [], "Seleccioná Mostrar detalle para abrir el grupo.",
                "Mostrar detalle", False, estilo_base, None,
            )

        # Alternar apertura y cierre al pulsar el botón.
        if estado_detalle == clave_fila:
            return (
                estilo_oculto, [], [], "El detalle está cerrado.",
                "Mostrar detalle", False, estilo_base, None,
            )

        try:
            df = _preparar_datos()

            # Aplicar la búsqueda de texto principal.
            df = _filtrar_texto(df, dimension, filtro_texto)

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
                    estilo_visible, [], [], "No hay columnas disponibles para el detalle.",
                    "Quitar detalle", False, estilo_base, clave_fila,
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

            detalle = detalle.rename(columns=dict(columnas_disponibles))

            for columna in ("Gasto total",):
                if columna in detalle.columns:
                    detalle[columna] = detalle[columna].map(
                        lambda valor: (
                            f"$ {valor:,.2f}" if pd.notna(valor) else "—"
                        )
                    )

            if "Calificación promedio" in detalle.columns:
                detalle["Calificación promedio"] = (
                    detalle["Calificación promedio"].map(
                        lambda valor: (
                            f"{valor:.2f}" if pd.notna(valor) else "—"
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
                estilo_visible, [], [], "No se pudo cargar el detalle.",
                "Quitar detalle", False, estilo_base, None,
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
        tabla = tabla[[col for col in orden if col in tabla.columns]]

        contenido = _crear_pdf("Analítica de clientes", tabla)

        return {
            "content": contenido,
            "filename": "analitica_clientes.pdf",
            "type": "application/pdf",
            "base64": False,
        }