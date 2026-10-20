# Funciones reutilizables para construir los gráficos del dashboard
import plotly.express as px
import pandas as pd

# Paleta del sitio oficial de UCASAL. Los colores semánticos explícitos
# de los gráficos de decisiones conservan su significado.
UCASAL_COLORS = ["#003D7C", "#E50019", "#628EB8", "#B20D15", "#8796A8", "#E98B96"]
px.defaults.color_discrete_sequence = UCASAL_COLORS


# Aplicar un estilo común a todos los gráficos.
def aplicar_estilo_grafico(fig, margen_inferior=28):
    fig.update_layout(
        title=dict(
            font=dict(size=14),
            x=0.03,
            xanchor="left",
            y=0.98,
            yanchor="top",
            pad=dict(t=0, b=0)
        ),
        font=dict(size=9, family="Arial, sans-serif", color="#334155"),
        colorway=UCASAL_COLORS,
        margin=dict(l=24, r=24, t=48, b=margen_inferior),
        template="plotly_white"
    )

    fig.update_xaxes(
        title_font=dict(size=10),
        tickfont=dict(size=9),
        automargin=True
    )
    fig.update_yaxes(
        title_font=dict(size=10),
        tickfont=dict(size=9),
        automargin=True
    )

    return fig


# 1. Gráfico de facturación mensual o diaria.
def crear_grafico_facturacion(datos, modo_fecha, anio_seleccionado, mes_seleccionado):

    if modo_fecha == "mensual":
        if anio_seleccionado == "__todos__":
            fig = px.line(
                title="Seleccioná un año para ver la facturación diaria"
            )
            return aplicar_estilo_grafico(fig, 32)

        ventas = (
            datos.groupby("order_purchase_date", as_index=False)["price"]
            .sum()
            .rename(columns={
                "order_purchase_date": "fecha",
                "price": "facturacion"
            })
        )

        columna_fecha = "fecha"
        titulo = "Facturación diaria"
        titulo_eje = "Día"

    else:
        ventas = (
            datos.groupby("mes", as_index=False)["price"]
            .sum()
            .rename(columns={"price": "facturacion"})
        )

        columna_fecha = "mes"
        titulo = "Facturación mensual"
        titulo_eje = "Mes"

    fig = px.line(
        ventas,
        x=columna_fecha,
        y="facturacion",
        markers=True,
        title=titulo
    )

    fig.update_layout(
        title=dict(
            text=titulo,
            font=dict(size=14),
            x=0.03,
            xanchor="left",
            y=0.98,
            yanchor="top",
            pad=dict(t=0, b=0)
        ),
        xaxis_title=dict(text=titulo_eje, font=dict(size=10)),
        yaxis_title=dict(text="Facturación", font=dict(size=10))
    )

    # Mostrar más marcas en ambos ejes.
# Agregar un pequeño margen para mostrar completos los puntos extremos
    fecha_min = ventas[columna_fecha].min()
    fecha_max = ventas[columna_fecha].max()

    if modo_fecha == "anual":
        margen = pd.Timedelta(days=10)
    else:
        margen = pd.Timedelta(days=1)

    fig.update_xaxes(
        range=[fecha_min - margen, fecha_max + margen],
        nticks=12,
        tickformat="%Y\n%b" if modo_fecha == "anual" else "%d %b",
        tickfont=dict(size=9),
        automargin=True
    )
    fig.update_yaxes(
        nticks=8,
        tickfont=dict(size=9),
        automargin=True,
        tickformat="~s"
    )

    # En el modo anual, cada marca del eje X representa un mes.
    if modo_fecha == "anual":
        fig.update_xaxes(
            dtick="M1",
            tickformat="%Y\n%b"
        )

    # En el modo mensual, mostrar marcas cada tres días.
    else:
        fig.update_xaxes(dtick="D3")

    return aplicar_estilo_grafico(fig, 32)


# 2. Top 5 categorías por facturación.
def crear_grafico_categorias(datos):

    top = (
        datos.groupby("product_category_name", as_index=False)["price"]
        .sum()
        .nlargest(5, "price")
        .sort_values("price", ascending=True)
    )

    fig = px.bar(
        top,
        x="price",
        y="product_category_name",
        orientation="h",
        title="Top 5 categorías de producto por facturación",
        labels={
            "price": "Facturación",
            "product_category_name": "Categoría"
        }
    )
    fig.update_traces(width=0.55)
    fig.update_layout(bargap=0.03)

    return aplicar_estilo_grafico(fig, 24)


# 3. Top 5 vendedores por facturación.
def crear_grafico_vendedores(datos):

    top = (
        datos.groupby(
            ["seller_id", "seller_label"],
            as_index=False
        )["price"]
        .sum()
        .nlargest(5, "price")
        .sort_values("price", ascending=True)
    )

    fig = px.bar(
        top,
        x="price",
        y="seller_label",
        orientation="h",
        title="Top 5 vendedores por facturación",
        labels={
            "price": "Facturación",
            "seller_label": "Vendedor"
        },
        hover_data={
            "seller_id": True,
            "seller_label": False
        }
    )
    fig.update_traces(width=0.55)
    fig.update_layout(bargap=0.03)

    return aplicar_estilo_grafico(fig, 24)
