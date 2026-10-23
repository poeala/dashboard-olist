"""Pagos: contexto por pedido, composición por medio y comparaciones descriptivas."""

import pandas as pd
import plotly.express as px
from dash import html

from components.business import cards, chart, table, number, money
from data.payment_metrics import (
    preparar_pagos, resumen_pagos, participacion_pagos, preferencias_segmento,
    participacion_por_tipo_pedido, evolucion_pagos, resumen_cuotas,
    comparaciones_pago, MINIMUM_ORDERS, MINIMUM_DIFFERENCE,
)


METHOD_COLORS = {
    "Tarjeta de crédito": "#003D7C", "Boleto": "#628EB8",
    "Voucher": "#B20D15", "Tarjeta de débito": "#E50019",
    "Pagos mixtos": "#7755A2", "Sin información / otro": "#8796A8",
}
LABELS = {
    "method": "Medio / tipo de pago", "amount": "Importe registrado (R$)",
    "ticket": "Ticket por pedido (R$)", "median": "Mediana (R$)",
    "share": "Participación del importe (%)", "orders": "Pedidos",
    "gold_segment": "Segmento histórico", "range": "Cuotas máximas del pedido",
}


def _chart(fig, title, note=None):
    # El título HTML se ajusta al ancho móvil sin recortar texto en Plotly.
    return html.Section([
        html.H3(title, className="payments-chart-title"), chart(fig, ""),
        html.P(note, className="business-note") if note else None,
    ], className="payments-chart-section")


def _context(rows, orders, quality, reference, period_label):
    dates = pd.to_datetime(rows["purchase_date"], errors="coerce").dropna()
    observed = (f"{dates.min():%d/%m/%Y}–{dates.max():%d/%m/%Y}"
                if not dates.empty else "Sin fechas observadas")
    cutoff = rows.attrs.get("cutoff", reference)
    cutoff_label = f"{pd.Timestamp(cutoff):%d/%m/%Y}" if pd.notna(cutoff) else "Sin datos"
    coverage = (100 * len(orders) / quality["source_orders"] if quality["source_orders"] else None)
    return html.Div([
        html.P([
            html.Strong(f"{period_label or 'Período seleccionado'} · "),
            f"Compras observadas: {observed}. Corte del histórico: {cutoff_label}.",
        ]),
        html.P("Las fechas observadas y el corte no garantizan meses completos. "
               "Los importes son pagos registrados, no margen ni ingresos netos liquidados.",
               className="business-note"),
        html.Details([
            html.Summary(f"Cobertura: {number(len(orders))} de {number(quality['source_orders'])} "
                         f"pedidos válidos ({number(coverage, 2, ' %')})"),
            html.Ul([
                html.Li(f"Sin pagos: {number(quality['without_payment'])} pedidos."),
                html.Li(f"Excluidos por importes o secuencias inválidos: {number(quality['invalid_orders'])} pedidos."),
                html.Li(f"Cuotas desconocidas: {number(quality['unknown_installments'])} pedidos válidos."),
                html.Li(f"Medios desconocidos: {number(quality['unknown_method'])} pedidos válidos."),
            ]),
            html.P("Cobertura sobre pedidos presentes en Ventas, sin cancelados ni no disponibles. "
                   "Los atributos desconocidos se excluyen solo de sus indicadores correspondientes."),
        ], open=any(quality[key] for key in quality if key != "source_orders")),
    ], className="payments-context")


def _gerencial(payments, orders, stats, daily):
    financed = orders[orders["financed"]]
    content = [cards([
        ("Importe total registrado", money(stats["amount"]), "Suma de pagos de pedidos válidos."),
        ("Pedidos con pagos válidos", number(stats["orders"]), "Cada pedido se cuenta una vez."),
        ("Ticket por pedido", money(stats["ticket"]), f"Sobre {number(stats['orders'])} pedidos."),
        ("Pedidos en cuotas", number(stats["financed_pct"], 2, " %"),
         f"{number(len(financed))} de {number(stats['quota_orders'])} con cuotas conocidas."),
    ])]
    content.append(html.Details([
        html.Summary("Otros indicadores de pagos"),
        html.Dl([
            html.Dt("Importe promedio por registro de pago"),
            html.Dd(f"{money(payments['payment_value'].mean())} · {number(len(payments))} registros"),
            html.Dt("Pedidos con pagos mixtos"),
            html.Dd(f"{number(stats['mixed_pct'], 2, ' %')} · {number(orders['mixed'].sum())} "
                    f"de {number(stats['method_orders'])} con medios conocidos"),
            html.Dt("Cuotas promedio en pedidos financiados"),
            html.Dd(f"{number(financed['installments'].mean(), 2)} · {number(len(financed))} pedidos"),
            html.Dt("Cuotas promedio en todos los pedidos con cuotas conocidas"),
            html.Dd(f"{number(stats['avg_installments'], 2)} · {number(stats['quota_orders'])} pedidos"),
        ]),
    ], className="payments-details"))
    evolution = evolucion_pagos(orders, daily)
    period_title = "diaria" if daily else "mensual"
    graphs = []
    for metric, title in (("amount", "Importe registrado"), ("ticket", "Ticket por pedido"),
                          ("orders", "Cantidad de pedidos")):
        fig = None
        if not evolution.empty:
            fig = px.line(evolution, x="period", y=metric, markers=True,
                          labels={**LABELS, "period": "Día de compra" if daily else "Mes de compra"})
            fig.update_traces(connectgaps=False)
            fig.update_xaxes(tickformat="%d/%m" if daily else "%m/%Y")
        graphs.append(_chart(fig, f"{title} · evolución {period_title}"))
    content.append(html.Div(graphs, className="business-charts"))
    content.append(html.P("Los huecos indican períodos sin observaciones; no se interpretan como cero. "
                          "El volumen de pedidos ayuda a distinguir cambios de actividad de cambios de ticket.",
                          className="business-note"))
    shares = participacion_pagos(payments)
    if not shares.empty and shares["share"].notna().any():
        leading = shares.iloc[0]
        content.append(html.P(
            f"Medio con mayor importe: {leading['method']} ({number(leading['share'], 2)} %). "
            "Cada registro se atribuye a su medio, incluso dentro de pedidos mixtos.",
            className="business-note"))
    return content


def _share_chart(shares):
    if shares.empty or not shares["share"].notna().any():
        return None
    fig = px.bar(shares, x="share", y="method", color="method", orientation="h",
                 color_discrete_map=METHOD_COLORS, labels=LABELS,
                 custom_data=["amount", "orders"], text="share")
    fig.update_traces(texttemplate="%{x:.2f}%", textposition="outside", cliponaxis=False,
                      hovertemplate="%{y}<br>Importe: R$ %{customdata[0]:,.2f}<br>"
                                    "Participación: %{x:.2f}%<br>Pedidos: %{customdata[1]:,.0f}<extra></extra>")
    fig.update_layout(showlegend=False)
    fig.update_yaxes(categoryorder="total ascending", title_text=None)
    fig.update_xaxes(range=[0, 115], ticksuffix="%")
    return fig


def _analitica(payments, orders):
    shares = participacion_pagos(payments)
    classified = participacion_por_tipo_pedido(payments, orders)
    quotas = resumen_cuotas(orders)
    present = quotas[quotas["orders"].gt(0)]
    quota_fig = None
    if not present.empty:
        quota_fig = px.bar(present, x="range", y="median", labels=LABELS,
                           custom_data=["orders", "p25", "p75"], color_discrete_sequence=["#003D7C"])
        quota_fig.update_traces(hovertemplate="%{x}<br>Mediana: R$ %{y:,.2f}<br>"
                               "Pedidos: %{customdata[0]:,.0f}<br>P25: R$ %{customdata[1]:,.2f}"
                               "<br>P75: R$ %{customdata[2]:,.2f}<extra></extra>")
        baseline = quotas.iloc[0]["median"]
        if pd.notna(baseline):
            quota_fig.add_hline(y=baseline, line_dash="dot", line_color="#B20D15")
    preferences = preferencias_segmento(orders)
    segment_fig = None
    if not preferences.empty:
        segment_fig = px.bar(preferences, x="gold_segment", y="share", color="method",
                             barmode="stack", color_discrete_map=METHOD_COLORS,
                             labels={**LABELS, "share": "Pedidos del segmento (%)"},
                             custom_data=["orders", "segment_orders"])
        segment_fig.update_yaxes(range=[0, 100], ticksuffix="%")
        segment_fig.update_traces(hovertemplate="%{x} · %{fullData.name}<br>%{y:.2f}%<br>"
                                 "%{customdata[0]:,.0f} de %{customdata[1]:,.0f} pedidos<extra></extra>")
    content = [html.Div([
        _chart(_share_chart(shares), "Importe por medio de pago",
               "Cada importe se asigna al medio que lo pagó. Un pedido puede aparecer en varios medios; sus conteos no se suman."),
        _chart(_share_chart(classified), "Importe por tipo de pedido",
               "Cada pedido se clasifica una vez. Todo el importe de pedidos con varios medios se agrupa en Pagos mixtos."),
        _chart(quota_fig, "Mediana por cuotas · crédito exclusivo",
               "Solo crédito exclusivo con cuotas conocidas. Línea punteada: mediana en una cuota, si existe. "
               "El detalle muestra pedidos y percentiles 25 y 75; la asociación no demuestra causalidad."),
        _chart(segment_fig, "Tipos de pago por segmento",
               "Se cuentan pedidos con medio y segmento conocidos, no clientes únicos. "
               "El segmento Gold es histórico y puede usar información posterior al período elegido."),
    ], className="business-charts")]
    columns = {"method": "Tipo de pago del pedido", "orders": "Pedidos", "amount": "Importe total (R$)",
               "share": "Participación del importe (%)", "ticket": "Ticket por pedido (R$)",
               "median": "Mediana del pedido (R$)"}
    content.append(table(classified[list(columns)], columns, "Resumen por tipo de pedido",
                         "Clasificación exclusiva: los pedidos y los importes se pueden sumar. "
                         "Con importe total cero no se calcula participación.",
                         table_id="payments-method-table"))
    content.append(html.Details([
        html.Summary("Ver muestras y dispersión por cuotas"),
        table(quotas, {"range": "Cuotas", "orders": "Pedidos", "median": "Mediana (R$)",
                       "p25": "Percentil 25 (R$)", "p75": "Percentil 75 (R$)"},
              "Distribución de importes", "Los rangos sin pedidos no tienen mediana ni percentiles.",
              table_id="payments-quota-table"),
    ], className="payments-details"))
    return content


def _decisiones(orders):
    comparisons = comparaciones_pago(orders)
    findings = sorted((row for row in comparisons if row["status"] == "Hallazgo"),
                      key=lambda row: (-row["gap"], row["group"]))
    evaluable = sum(row["gap"] is not None for row in comparisons)
    content = [html.P(
        f"{len(findings)} hallazgos en {evaluable} comparaciones evaluables. "
        f"Se requieren {MINIMUM_ORDERS} pedidos por grupo y referencia, y una diferencia positiva "
        f"de al menos {MINIMUM_DIFFERENCE} %. Son asociaciones, no efectos causales ni rentabilidad demostrada.",
        className="business-note")]
    if findings:
        display = pd.DataFrame([{
            "Grupo": row["group"], "Medida": row["metric"],
            "Pedidos del grupo": row["orders"], "Valor del grupo (R$)": row["value"],
            "Referencia": row["reference"], "Pedidos de referencia": row["reference_orders"],
            "Valor de referencia (R$)": row["reference_value"], "Diferencia (%)": row["gap"],
            "Magnitud": "Alta" if row["gap"] >= 40 else "Media",
            "Acción a evaluar": row["action"], "Seguimiento": row["followup"],
        } for row in findings])
        content.append(table(display, {col: col for col in display.columns}, "Hallazgos detectados",
                             "Magnitud alta desde 40 %; media desde 20 % hasta menos de 40 %. "
                             "El orden refleja la diferencia observada, no una prioridad comercial.",
                             table_id="business-payments-findings-table"))
    else:
        content.append(html.Div([
            html.H3("Sin hallazgos según estas reglas" if evaluable else "Sin comparaciones evaluables"),
            html.P("Revisá las muestras y referencias en el detalle. La ausencia de hallazgos "
                   "no demuestra ausencia de oportunidades."),
        ], className="business-empty"))
    diagnostic = pd.DataFrame(comparisons)[["group", "reference", "orders", "reference_orders", "status"]]
    content.append(html.Details([
        html.Summary("Ver reglas y comparaciones evaluadas"),
        html.P("Medios: ticket promedio frente al resto de pedidos con medios conocidos, incluidos mixtos. "
               "Los mixtos no generan una regla propia. Cuotas: mediana de crédito exclusivo en "
               "2–3, 4–6 o 7+ cuotas frente a crédito exclusivo en una cuota. Una referencia monetaria "
               "cero no permite calcular diferencias relativas. Los umbrales son exploratorios y fijos."),
        table(diagnostic, {"group": "Grupo", "reference": "Referencia", "orders": "Pedidos del grupo",
                           "reference_orders": "Pedidos de referencia", "status": "Resultado"},
              "Cobertura de las reglas", "Un pedido puede respaldar varias comparaciones; las muestras no se suman.",
              table_id="business-payments-rules-table"),
    ], className="payments-details"))
    return content


def payments_content(rows, view, reference, daily=False, period_label=None):
    payments, orders, quality = preparar_pagos(rows)
    content = [_context(rows, orders, quality, reference, period_label)]
    if orders.empty:
        content.append(html.Div("No hay pedidos con pagos válidos para estos filtros.",
                                className="business-empty"))
        return html.Div(content, className="payments-content")
    if view == "gerencial":
        content.extend(_gerencial(payments, orders, resumen_pagos(orders), daily))
    elif view == "analitica":
        content.extend(_analitica(payments, orders))
    else:
        content.extend(_decisiones(orders))
    content.append(html.Details([
        html.Summary("Cómo se calculan los pagos y las cuotas"),
        html.P("Los importes corresponden a los pagos registrados y "
        "no representan ingresos netos ni márgenes de ganancia."
        "Para evitar duplicaciones, cada pedido se contabiliza una sola vez. "
        "Los pedidos que utilizan distintos medios de pago se clasifican 
        "como pagos mixtos.La cantidad de cuotas se obtiene del máximo "
        "registrado para el pedido, "no de la suma de sus registros de pago." 
        "Se excluyen los pedidos con información monetaria o de cuotas inválida."
        "Período analizado: del 4 de septiembre de 2016 al 29 de agosto de 2018."),
    ], className="payments-details"))
    return html.Div(content, className="payments-content")
