
"""Presentación de Pagos: contexto, exploración y decisiones."""

import json

import pandas as pd
import plotly.express as px
from dash import dcc, html, dash_table

from components.business import cards, chart, table, number, money
from data.payment_metrics import (
    preparar_pagos,
    resumen_pagos,
    participacion_pagos,
    agrupar_pedidos_pago,
    preferencias_segmento,
    oportunidades_pago,
)


MINIMUM_ORDERS = 30
MINIMUM_DIFFERENCE = 20


def participacion_por_tipo_pedido(payments, orders):
    """Agrupa el importe por clasificación de pago del pedido."""
    columns = ["method", "amount", "share", "records", "orders"]

    if payments.empty or orders.empty:
        return pd.DataFrame(columns=columns)

    classified = payments.copy()
    order_methods = orders.set_index("order_id")["method"]
    classified["method"] = (
        classified["order_id"]
        .map(order_methods)
        .fillna("Sin información / otro")
    )

    result = classified.groupby("method", as_index=False).agg(
        amount=("payment_value", "sum"),
        records=("order_id", "size"),
        orders=("order_id", "nunique"),
    )

    total = result["amount"].sum()
    result["share"] = (
        100 * result["amount"] / total
        if total > 0 else float("nan")
    )

    return result.sort_values("amount", ascending=False)


def _periodo_pagos(orders):
    """Devuelve el rango de fechas presente en los pedidos."""
    if orders.empty or "purchase_date" not in orders.columns:
        return "Sin período disponible"

    dates = pd.to_datetime(
        orders["purchase_date"],
        errors="coerce",
    ).dropna()

    if dates.empty:
        return "Sin período disponible"

    start = dates.min()
    end = dates.max()

    months = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre",
        "diciembre",
    ]

    if start.year == end.year and start.month == end.month:
        return f"{months[start.month - 1].capitalize()} {start.year}"

    if start.year == end.year:
        return f"Año {start.year}"

    return f"{start:%d/%m/%Y} – {end:%d/%m/%Y}"


def _prioridad_diferencia(gap):
    """
    Prioridad orientativa según la magnitud de la diferencia detectada.
    No representa riesgo ni impacto económico demostrado.
    """
    if gap >= 40:
        return "Alta"
    return "Media"


def _tabla_hallazgos(items, period):
    """Muestra los hallazgos y resalta visualmente su prioridad."""
    if not items:
        return html.Div([
            html.H3("Sin hallazgos para revisar"),
            html.P(
                "No se detectaron diferencias de al menos 20 % con "
                "30 pedidos comparables por grupo. Esto no significa "
                "que no existan oportunidades; solo que estas reglas "
                "no encontraron evidencia suficiente."
            ),
        ], className="business-empty")

    df = pd.DataFrame(items).copy()
    df["Prioridad"] = df["gap"].apply(_prioridad_diferencia)
    df["Período"] = period

    columns = [
        "Prioridad",
        "finding",
        "Período",
        "evidence",
        "action",
    ]

    selected = df[columns].rename(columns={
        "finding": "Hallazgo",
        "evidence": "Evidencia",
        "action": "Acción sugerida",
    })

    records = json.loads(
        selected.to_json(orient="records", date_format="iso")
    )

    return html.Div([
        html.H3("Hallazgos detectados"),
        html.P(
            "La prioridad refleja únicamente el tamaño de la diferencia: "
            "Alta desde 40 % y Media entre 20 % y menos de 40 %. "
            "No equivale a una medición de riesgo ni garantiza una "
            "oportunidad comercial.",
            className="business-note",
        ),
        dash_table.DataTable(
            id="business-payments-findings-table",
            data=records,
            columns=[
                {"name": col, "id": col}
                for col in selected.columns
            ],
            page_size=10,
            sort_action="native",
            filter_action="native",
            export_format="csv",
            export_headers="display",
            style_table={"overflowX": "auto"},
            style_cell={
                "fontFamily": "Arial",
                "fontSize": 12,
                "padding": "10px",
                "textAlign": "left",
                "whiteSpace": "normal",
                "height": "auto",
                "minWidth": "90px",
                "maxWidth": "290px",
            },
            style_header={
                "backgroundColor": "#e8eff7",
                "color": "#003D7C",
                "fontWeight": "600",
            },
            style_data_conditional=[
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "#f8fafc",
                },
                {
                    "if": {
                        "filter_query": '{Prioridad} = "Alta"',
                        "column_id": "Prioridad",
                    },
                    "backgroundColor": "#fee2e2",
                    "color": "#991b1b",
                    "fontWeight": "bold",
                },
                {
                    "if": {
                        "filter_query": '{Prioridad} = "Media"',
                        "column_id": "Prioridad",
                    },
                    "backgroundColor": "#fef3c7",
                    "color": "#92400e",
                    "fontWeight": "bold",
                },
            ],
        ),
    ], className="business-table")


def _tabla_reglas(minimum=MINIMUM_ORDERS, uplift=MINIMUM_DIFFERENCE):
    """Explica qué se compara y para qué sirve cada regla."""
    rules = pd.DataFrame([
        {
            "Hallazgo": "Diferencia de ticket por medio de pago",
            "Regla de detección": (
                "Se compara el ticket promedio de cada medio individual "
                "con el ticket promedio del resto de los pedidos con "
                "medio identificado. Se muestra el hallazgo si la diferencia "
                "es de al menos 20 %. Los pedidos con pagos mixtos no se "
                "consideran un medio individual."
            ),
            "Evidencia mínima": (
                f"Al menos {minimum} pedidos en el medio analizado y "
                f"{minimum} en el grupo de comparación."
            ),
            "Utilidad": (
                "Identificar medios asociados a compras de mayor importe "
                "y decidir si conviene profundizar el análisis por categoría "
                "de producto, tipo de cliente o costo de pago."
            ),
        },
        {
            "Hallazgo": "Importe de compras en cuotas",
            "Regla de detección": (
                "Se compara la mediana del importe de los pedidos con "
                "tarjeta en más de una cuota contra la mediana de los "
                "pedidos con tarjeta en una cuota. Se informa si la "
                "diferencia es de al menos 20 %. Se revisan por separado "
                "los rangos de 2–3, 4–6 y 7 o más cuotas."
            ),
            "Evidencia mínima": (
                f"Al menos {minimum} pedidos en el rango de cuotas "
                f"y {minimum} pedidos de crédito en una cuota."
            ),
            "Utilidad": (
                "Conocer qué importes aparecen en las compras financiadas "
                "y evaluar si tiene sentido estudiar costos y condiciones "
                "de financiación. No demuestra que las cuotas generen "
                "compras de mayor valor."
            ),
        },
    ])

    return table(
        rules,
        {
            "Hallazgo": "Hallazgo",
            "Regla de detección": "Regla de detección",
            "Evidencia mínima": "Evidencia mínima",
            "Utilidad": "¿Para qué sirve?",
        },
        "Reglas de detección",
        "Los umbrales son criterios prácticos de exploración, no pruebas "
        "de significancia estadística. Las diferencias pueden explicarse "
        "por el tipo de producto, los compradores u otros factores.",
        table_id="business-payments-rules-table",
    )


def _hallazgos_pago(orders, minimum=MINIMUM_ORDERS, uplift=MINIMUM_DIFFERENCE):
    """
    Genera solo dos tipos de hallazgo:
    1. Ticket promedio superior por medio de pago.
    2. Mediana de importe superior para un rango de cuotas.
    """
    results = []

    known = orders[
        orders["known_method"]
        & orders["amount"].notna()
        & orders["method"].ne("Pagos mixtos")
    ].copy()

    # Hallazgo 1: diferencia de ticket por medio de pago.
    for method in known["method"].dropna().unique():
        group = known[known["method"].eq(method)]
        rest = orders[
            orders["known_method"]
            & orders["amount"].notna()
            & orders["method"].ne(method)
        ]

        if len(group) < minimum or len(rest) < minimum:
            continue

        group_ticket = group["amount"].mean()
        rest_ticket = rest["amount"].mean()

        if pd.isna(rest_ticket) or rest_ticket <= 0 or pd.isna(group_ticket):
            continue

        gap = 100 * (group_ticket / rest_ticket - 1)

        if gap >= uplift:
            results.append({
                "gap": gap,
                "finding": f"Ticket promedio mayor · {method}",
                "evidence": (
                    f"Ticket promedio de {money(group_ticket)} en "
                    f"{number(len(group))} pedidos, frente a "
                    f"{money(rest_ticket)} en {number(len(rest))} "
                    f"pedidos comparables (+{number(gap, 1)} %)."
                ),
                "action": (
                    "Revisar si la diferencia se mantiene al comparar "
                    "categorías de productos y valores de compra similares. "
                    "Antes de proponer una promoción, considerar comisiones "
                    "y margen."
                ),
            })

    # Hallazgo 2: importe mediano por rango de cuotas.
    credit = orders[
        orders["known_method"]
        & orders["method"].eq("Tarjeta de crédito")
        & orders["known_installments"]
        & orders["amount"].notna()
    ]

    single = credit[credit["installments"].eq(1)]

    if len(single) >= minimum:
        single_median = single["amount"].median()

        if pd.notna(single_median) and single_median > 0:
            ranges = [
                ("2–3 cuotas", 2, 3),
                ("4–6 cuotas", 4, 6),
                ("7 o más cuotas", 7, float("inf")),
            ]

            for label, low, high in ranges:
                group = credit[credit["installments"].between(low, high)]

                if len(group) < minimum:
                    continue

                group_median = group["amount"].median()
                gap = 100 * (group_median / single_median - 1)

                if gap >= uplift:
                    results.append({
                        "gap": gap,
                        "finding": f"Mayor importe mediano · {label}",
                        "evidence": (
                            f"Mediana de {money(group_median)} en "
                            f"{number(len(group))} pedidos con tarjeta "
                            f"en {label}, frente a {money(single_median)} "
                            f"en {number(len(single))} pedidos en una cuota "
                            f"(+{number(gap, 1)} %)."
                        ),
                        "action": (
                            "Analizar costos de financiación, margen y "
                            "composición de productos en ese rango. La "
                            "diferencia describe compras observadas y no "
                            "prueba que ofrecer cuotas aumente las ventas."
                        ),
                    })

    return sorted(
        results,
        key=lambda item: (-item["gap"], item["finding"]),
    )


def payments_content(
    rows,
    view,
    reference,
    minimum=MINIMUM_ORDERS,
    uplift=MINIMUM_DIFFERENCE,
    preference=MINIMUM_DIFFERENCE,
    daily=False,
    period_label=None,
):
    # Valores fijos: no dependen de controles en la pantalla.
    minimum = MINIMUM_ORDERS
    uplift = MINIMUM_DIFFERENCE

    payments, orders, quality = preparar_pagos(rows)
    stats = resumen_pagos(orders)
    content = []

    if orders.empty:
        content.append(html.Div(
            "No hay pedidos con pagos válidos para estos filtros.",
            className="business-empty",
        ))
        return html.Div(content)

    shares = participacion_pagos(payments)
    methods = agrupar_pedidos_pago(orders)
    period = period_label or _periodo_pagos(orders)

    labels = {
        "method": "Tipo de pago del pedido",
        "amount": "Importe de pagos (R$)",
        "ticket": "Ticket por pedido (R$)",
        "median": "Mediana del pedido (R$)",
        "share": "Participación del importe (%)",
        "orders": "Pedidos",
        "installments": "Cuotas máximas del pedido",
        "gold_segment": "Segmento de clientes",
    }

    if view == "gerencial":
        leading = shares.iloc[0] if not shares.empty else None
        payment_average = (
            payments["payment_value"].mean()
            if not payments.empty else None
        )

        financed_orders = orders[
            orders["known_installments"]
            & orders["installments"].gt(1)
        ]
        average_financed_installments = (
            financed_orders["installments"].mean()
            if not financed_orders.empty else None
        )

        content.append(cards([
            (
                "Pedidos en cuotas",
                number(stats["financed_pct"], 2, " %"),
                "Con cuotas conocidas.",
            ),
            (
                "Pedidos con pagos mixtos",
                number(stats["mixed_pct"], 2, " %"),
                "Con más de un medio.",
            ),
            (
                "Importe promedio por pago",
                money(payment_average),
                "Por registro de pago.",
            ),
            (
                "Cuotas promedio",
                number(average_financed_installments, 2),
                f"Sobre {number(len(financed_orders))} pedidos financiados.",
            ),
        ]))

        if daily:
            daily_orders = orders.dropna(subset=["purchase_date"]).copy()
            daily_orders["period"] = daily_orders["purchase_date"].dt.normalize()
            evolution = daily_orders.groupby("period", as_index=False).agg(
                amount=("amount", "sum"),
                ticket=("amount", "mean"),
                orders=("order_id", "nunique"),
            )
            evolution["period_label"] = evolution["period"].dt.strftime("%d/%m")
            period_label_chart = "Día de compra"
            x_column = "period_label"
            period_title = "diaria"
        else:
            monthly_orders = orders.dropna(subset=["purchase_date"]).copy()
            monthly_orders["period"] = (
                monthly_orders["purchase_date"].dt.to_period("M").astype(str)
            )
            evolution = monthly_orders.groupby("period", as_index=False).agg(
                amount=("amount", "sum"),
                ticket=("amount", "mean"),
                orders=("order_id", "nunique"),
            )
            period_label_chart = "Mes de compra"
            x_column = "period"
            period_title = "mensual"

        if not evolution.empty:
            amount_fig = px.line(
                evolution,
                x=x_column,
                y="amount",
                markers=True,
                labels={**labels, x_column: period_label_chart},
                hover_data={"orders": True, "amount": ":.2f"},
            )
            amount_fig.update_traces(
                hovertemplate=(
                    f"{period_label_chart}: %{{x}}<br>"
                    "Importe pagado: R$ %{y:,.2f}<br>"
                    "Pedidos: %{customdata[0]:,.0f}<extra></extra>"
                )
            )

            ticket_fig = px.line(
                evolution,
                x=x_column,
                y="ticket",
                markers=True,
                labels={**labels, x_column: period_label_chart},
                hover_data={"orders": True, "ticket": ":.2f"},
            )
            ticket_fig.update_traces(
                hovertemplate=(
                    f"{period_label_chart}: %{{x}}<br>"
                    "Ticket promedio: R$ %{y:,.2f}<br>"
                    "Pedidos: %{customdata[0]:,.0f}<extra></extra>"
                )
            )

            content.append(html.Div([
                chart(amount_fig, f"Evolución {period_title} del importe pagado"),
                chart(ticket_fig, f"Evolución {period_title} del ticket por pedido"),
            ], className="business-charts"))

        if leading is not None:
            content.append(html.P(
                f"Medio con mayor importe registrado: {leading['method']} "
                f"({number(leading['share'], 2)} % del importe). "
                f"El promedio de cuotas máximas es "
                f"{number(stats['avg_installments'], 2)} sobre "
                f"{number(stats['quota_orders'])} pedidos con cuotas conocidas. "
                "Los pagos mixtos combinan dos o más medios.",
                className="business-note",
            ))

    elif view == "analitica":
        payment_shares = participacion_por_tipo_pedido(payments, orders)
        preferences = preferencias_segmento(orders)

        payment_order = [
            "Tarjeta de crédito",
            "Tarjeta de débito",
            "Boleto",
            "Voucher",
            "Pagos mixtos",
            "Sin información / otro",
        ]

        if not payment_shares.empty:
            payment_shares["method"] = pd.Categorical(
                payment_shares["method"],
                categories=payment_order,
                ordered=True,
            )
            payment_shares = payment_shares.sort_values("method")

            pie_fig = px.pie(
                payment_shares,
                names="method",
                values="amount",
                hole=0.35,
                category_orders={"method": payment_order},
                labels={
                    "method": "Tipo de pago del pedido",
                    "amount": "Importe registrado (R$)",
                    "share": "Participación del importe (%)",
                },
                hover_data={
                    "orders": True,
                    "records": True,
                    "share": ":.2f",
                },
            )
            pie_fig.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate=(
                    "%{label}<br>Importe: R$ %{value:,.2f}<br>"
                    "Participación: %{percent}<extra></extra>"
                ),
            )
        else:
            pie_fig = None

        if not preferences.empty:
            preferences["gold_segment"] = preferences["gold_segment"].astype(str)
            preferences["method"] = pd.Categorical(
                preferences["method"],
                categories=payment_order,
                ordered=True,
            )
            preferences = preferences.sort_values(["gold_segment", "method"])

            segment_fig = px.bar(
                preferences,
                x="gold_segment",
                y="share",
                color="method",
                barmode="stack",
                category_orders={"method": payment_order},
                labels={
                    "gold_segment": "Segmento de clientes",
                    "share": "Distribución de pedidos (%)",
                    "method": "Tipo de pago del pedido",
                    "orders": "Pedidos",
                },
                hover_data={
                    "orders": True,
                    "segment_orders": True,
                    "share": ":.2f",
                },
            )
            segment_fig.update_layout(
                yaxis={
                    "title": "Distribución de pedidos (%)",
                    "range": [0, 100],
                    "ticksuffix": "%",
                },
                xaxis_title="Segmento de clientes",
                legend_title="Tipo de pago",
                barnorm="percent",
            )
            segment_fig.update_traces(
                hovertemplate=(
                    "Segmento: %{x}<br>Tipo de pago: %{fullData.name}<br>"
                    "Participación: %{y:.2f}%<extra></extra>"
                ),
            )
        else:
            segment_fig = None

        content.append(html.Div([
            chart(pie_fig, "Participación del importe por tipo de pago"),
            chart(segment_fig, "Composición de los pagos por segmento de clientes"),
        ], className="business-charts"))

        payment_shares_table = payment_shares.copy()
        payment_shares_table["method"] = payment_shares_table["method"].astype(str)

        methods_table = methods.copy()
        methods_table["method"] = methods_table["method"].astype(str)

        analytical_table = payment_shares_table.merge(
            methods_table[["method", "ticket", "median"]],
            on="method",
            how="outer",
        )

        analytical_table = analytical_table[[
            "method", "orders", "amount", "share", "ticket", "median",
        ]].rename(columns={
            "method": "Tipo de pago del pedido",
            "orders": "Pedidos",
            "amount": "Importe total (R$)",
            "share": "Participación del importe (%)",
            "ticket": "Ticket promedio (R$)",
            "median": "Mediana del pedido (R$)",
        })

        content.append(table(
            analytical_table,
            {
                "Tipo de pago del pedido": "Tipo de pago del pedido",
                "Pedidos": "Pedidos",
                "Importe total (R$)": "Importe total (R$)",
                "Participación del importe (%)": "Participación del importe (%)",
                "Ticket promedio (R$)": "Ticket promedio (R$)",
                "Mediana del pedido (R$)": "Mediana del pedido (R$)",
            },
            "Resumen de pagos por tipo",
            "Cada pedido se clasifica una sola vez. El ticket y la mediana "
            "usan el importe total por pedido. Los porcentajes describen "
            "pedidos o importes, no clientes únicos.",
        ))

        content.append(html.P(
            "La composición por segmento utiliza pedidos con medio conocido "
            "y segmento Gold disponible. La clasificación Gold es histórica "
            "y puede usar información fuera del período seleccionado.",
            className="business-note",
        ))

    else:
        detected = _hallazgos_pago(orders, minimum, uplift)

        # Los vouchers se cuentan por pedido, incluso si el pedido es mixto.
        known_method_orders = orders[orders["known_method"]]
        voucher_order_ids = payments.loc[
            payments["method"].eq("Voucher"),
            "order_id",
        ].dropna().unique()

        voucher_orders = known_method_orders[
            known_method_orders["order_id"].isin(voucher_order_ids)
        ]

        voucher_pct = (
            100 * len(voucher_orders) / len(known_method_orders)
            if not known_method_orders.empty else None
        )

        # Mayor diferencia de ticket entre medios individuales.
        ticket_findings = [
            item for item in detected
            if item["finding"].startswith("Ticket promedio mayor")
        ]
        largest_ticket_gap = (
            max(ticket_findings, key=lambda item: item["gap"])
            if ticket_findings else None
        )

        # Número de rangos de cuotas que superan el umbral.
        installment_findings = [
            item for item in detected
            if item["finding"].startswith("Mayor importe mediano")
        ]

        content.append(cards([
            (
                "Hallazgos detectados",
                number(len(detected)),
                "Diferencias que superan los criterios.",
            ),
            (
                "Pedidos con voucher",
                number(voucher_pct, 2, " %"),
                f"{number(len(voucher_orders))} de "
                f"{number(len(known_method_orders))} pedidos.",
            ),
            (
                "Mayor diferencia de ticket",
                (
                    number(largest_ticket_gap["gap"], 1, " %")
                    if largest_ticket_gap else "Sin hallazgo"
                ),
                (
                    largest_ticket_gap["finding"]
                    if largest_ticket_gap
                    else "Ningún medio supera el umbral del 20 %."
                ),
            ),
            (
                "Rangos de cuotas destacados",
                number(len(installment_findings)),
                "Rangos con mediana al menos 20 % mayor.",
            ),
        ], neutral=True))

        content.append(html.P(
            f"Período analizado: {period}. Se requieren al menos "
            f"{number(minimum)} pedidos en cada grupo y una diferencia "
            f"de al menos {number(uplift)} %. Los resultados describen "
            "asociaciones; no prueban que el medio de pago o las cuotas "
            "causen un importe mayor.",
            className="business-note",
        ))

        content.append(_tabla_hallazgos(detected, period))

        content.append(html.Details([
            html.Summary(
                "Ver reglas de detección",
                style={
                    "cursor": "pointer",
                    "fontWeight": "bold",
                    "fontSize": "15px",
                },
            ),
            html.P(
                "El ticket promedio se utiliza para comparar medios de pago; "
                "la mediana se utiliza en cuotas porque es menos sensible a "
                "compras excepcionalmente grandes. Solo se muestran "
                "diferencias positivas de al menos 20 %."
            ),
            _tabla_reglas(minimum, uplift),
            html.P(
                "Las diferencias pueden deberse a la categoría de producto, "
                "el importe inicial de la compra u otras características. "
                "Antes de implementar una acción comercial, habría que "
                "evaluar costos, margen y resultados mediante una prueba "
                "controlada.",
                className="business-note",
            ),
        ], open=False, style={
            "backgroundColor": "#ffffff",
            "padding": "14px",
            "borderRadius": "8px",
            "boxShadow": "0 1px 5px #dddddd",
            "marginBottom": "14px",
        }))

    content.append(html.P(
        "Las cuotas se calculan como el máximo de los registros de pago "
        "del pedido, no como su suma. Para considerarlas válidas se exige "
        "un entero mayor o igual a 1 en todos los registros. Un pedido "
        "está financiado si ese máximo supera 1. Varios registros del "
        "mismo medio no implican pagos mixtos. Los pedidos con importes "
        "inválidos se excluyen de los cálculos de importes y tickets.",
        className="business-note",
    ))

    return html.Div(content)
