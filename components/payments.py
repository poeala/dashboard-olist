"""Presentación de Pagos: contexto, exploración y acciones sin inferir causalidad."""
import pandas as pd
import plotly.express as px
from dash import html

from components.business import cards, chart, table, number, money
from data.payment_metrics import (
    preparar_pagos, resumen_pagos, participacion_pagos, agrupar_pedidos_pago,
    preferencias_segmento, oportunidades_pago,
)


def payments_content(rows, view, reference, minimum=30, uplift=20, preference=10):
    payments, orders, quality = preparar_pagos(rows)
    stats = resumen_pagos(orders)
    date = reference.strftime("%d/%m/%Y") if pd.notna(reference) else "sin fecha"
    content = [html.P(
        f"Corte histórico: {date}. Filtros por fecha de compra; se excluyen cancelados y no disponibles. "
        "Importes de pagos registrados: no equivalen a ingresos netos, margen ni dinero liquidado. "
        "Los pagos se consolidan por pedido antes de calcular el ticket.", className="business-note",
    ), html.P(
        f"Cobertura: {number(len(orders))} de {number(quality['source_orders'])} pedidos con pagos completos válidos. "
        f"Sin registros de pago: {number(quality['without_payment'])}; excluidos por importe o clave inválidos: "
        f"{number(quality['invalid_orders'])}. Entre los incluidos, {number(quality['unknown_installments'])} "
        f"tienen cuotas incompletas y {number(quality['unknown_method'])} un medio desconocido.",
        className="business-note",
    )]
    if orders.empty:
        content.append(html.Div("No hay pedidos con pagos válidos para estos filtros.", className="business-empty"))
        return html.Div(content)
    shares = participacion_pagos(payments)
    methods = agrupar_pedidos_pago(orders)
    labels = {"method": "Medio del pedido", "amount": "Importe de pagos (R$)",
              "ticket": "Ticket por pedido (R$)", "median": "Mediana del pedido (R$)",
              "share": "Participación del importe (%)", "orders": "Pedidos",
              "installments": "Cuotas máximas del pedido", "gold_segment": "Segmento histórico"}
    if view == "gerencial":
        leading = shares.iloc[0]
        content.append(cards([
            ("Importe total de pagos", money(stats["amount"]), ""),
            ("Ticket promedio por pedido", money(stats["ticket"]), ""),
            ("Pedidos en cuotas", number(stats["financed_pct"], 2, " %"), ""),
            ("Pedidos con pagos mixtos", number(stats["mixed_pct"], 2, " %"), ""),
        ]))
        content.append(html.P(
            f"Promedio de cuotas máximas por pedido: {number(stats['avg_installments'], 2)} "
            f"sobre {number(stats['quota_orders'])} pedidos con cuotas conocidas. "
            f"Medio con mayor importe: {leading['method']} "
            f"({number(leading['share'], 2)} % del importe). "
            f"Pagos mixtos: dos o más medios distintos, sobre {number(stats['method_orders'])} pedidos con medios conocidos.",
            className="business-note",
        ))
        monthly = orders.assign(period=orders["purchase_date"].dt.to_period("M").astype(str))
        monthly = monthly.groupby("period", as_index=False).agg(amount=("amount", "sum"), ticket=("amount", "mean"))
        content.append(html.Div([
            chart(px.line(monthly, x="period", y="amount", markers=True,
                          labels={**labels, "period": "Mes de compra"}), "Evolución del importe pagado"),
            chart(px.line(monthly, x="period", y="ticket", markers=True,
                          labels={**labels, "period": "Mes de compra"}), "Evolución del ticket por pedido"),
        ], className="business-charts"))
    elif view == "analitica":
        credit = orders[orders["method"].eq("Tarjeta de crédito") & orders["known_installments"]]
        quotas = agrupar_pedidos_pago(credit, "installments")
        preferences = preferencias_segmento(orders)
        content.append(html.Div([
            chart(px.bar(shares, x="share", y="method", orientation="h", labels=labels,
                         hover_data=["amount", "orders"]) if shares["share"].notna().any() else None,
                  "Participación monetaria por medio de pago"),
            chart(px.bar(methods, x="method", y="ticket", labels=labels, hover_data=["orders", "median"]),
                  "Ticket por medio del pedido · mixtos separados"),
            chart(px.line(quotas, x="installments", y="median", markers=True, labels=labels,
                          hover_data=["orders", "ticket"]) if not quotas.empty else None,
                  "Mediana por cuotas · solo crédito exclusivo"),
            chart(px.bar(preferences, x="gold_segment", y="share", color="method", barmode="stack",
                         labels={**labels, "share": "Pedidos del segmento (%)"}, hover_data=["orders"])
                  if not preferences.empty else None, "Medios utilizados por segmento histórico"),
        ], className="business-charts"))
        content.append(table(shares, {"method": "Medio", "amount": "Importe (R$)", "share": "Importe (%)",
                                     "records": "Registros de pago", "orders": "Pedidos asociados"},
                             "Participación por medio", "Los importes se reparten por registro; los pedidos asociados a medios diferentes no se suman."))
        content.append(table(methods, {"method": "Medio del pedido", "orders": "Pedidos", "amount": "Importe (R$)",
                                      "ticket": "Ticket (R$)", "median": "Mediana (R$)"}, "Valor de los pedidos por medio"))
        content.append(table(quotas, {"installments": "Cuotas máximas", "orders": "Pedidos", "ticket": "Ticket (R$)",
                                     "median": "Mediana (R$)"}, "Relación entre cuotas y valor de compra",
                             "Solo pedidos exclusivamente de crédito con cuotas válidas en todos sus registros."))
        content.append(html.P(
            "El segmento Gold es histórico y puede usar compras posteriores al período seleccionado. "
            "Las preferencias describen pedidos del segmento, no clientes únicos ni decisiones conocidas en ese momento. "
            "Los pedidos mixtos permanecen separados; no se asigna su importe completo a cada medio.", className="business-note"))
    else:
        findings = oportunidades_pago(orders, minimum, uplift, preference)
        content.append(html.P(
            f"Reglas exploratorias: mínimo {minimum} pedidos tanto en el grupo como en la comparación; "
            f"ticket de un medio ≥ {uplift:g} % sobre el resto; mediana por rango de cuotas ≥ {uplift:g} % "
            f"sobre crédito en una cuota; preferencia de un medio ≥ {preference:g} pp sobre el resto de segmentos. "
            "En preferencias se exige el mínimo también en la combinación medio–segmento. "
            "Los controles permiten evaluar cómo cambia la selección. Los umbrales no están validados como óptimos "
            "ni son pruebas de significación. Las propuestas se ordenan por cantidad de pedidos del grupo.",
            className="business-note",
        ))
        if findings:
            content.append(table(pd.DataFrame(findings), {
                "priority": "Prioridad", "finding": "Oportunidad", "orders": "Pedidos del grupo",
                "evidence": "Evidencia y comparación", "action": "Acción a evaluar", "followup": "Cómo evaluar el resultado",
            }, "Oportunidades comerciales para evaluar"))
        else:
            content.append(html.Div("Sin oportunidades que cumplan los umbrales y las muestras mínimas. "
                                    "Esto no demuestra ausencia de oportunidades.", className="business-empty"))
        content.append(html.P(
            "Una asociación entre más cuotas y mayor importe no demuestra que ofrecer cuotas aumente las ventas. "
            "No hay ajuste por categoría, perfil, época ni selección del comprador; tampoco se dispone aquí de costos "
            "financieros, margen o resultados de campañas. Un pedido puede respaldar varias reglas: no sumar sus conteos. "
            "La clasificación histórica Gold no se interpreta como información disponible en una fecha pasada.", className="business-note",
        ))
    content.append(html.P(
        "Cuotas por pedido = máximo de sus registros, nunca suma. Para el porcentaje en cuotas y el promedio "
        "se exige un entero ≥ 1 en todos los registros; cero, negativos y faltantes se consideran desconocidos. "
        "Un pedido está en cuotas si ese máximo supera 1. Varios registros del mismo medio no son pagos mixtos. "
        "Un pedido con algún importe faltante, negativo o no finito se excluye entero de importes y tickets.",
        className="business-note",
    ))
    return html.Div(content)
