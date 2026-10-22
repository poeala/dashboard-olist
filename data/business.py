"""Snapshots de solo lectura. Se renuevan al reiniciar el proceso, como Ventas."""
from functools import lru_cache

import pandas as pd
from sqlalchemy import text

from data.database import engine
from data.definitions import PERIOD_CUTOFF_SQL


def _read_snapshot(query, dates, numeric):
    # Las dos consultas comparten una instantánea consistente y no escriben.
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            conn.execute(text("SET LOCAL statement_timeout = '60s'"))
            cutoff = conn.execute(text(PERIOD_CUTOFF_SQL)).scalar()
            df = pd.read_sql(text(query), conn, params={"cutoff": cutoff})
    for column in dates:
        df[column] = pd.to_datetime(df[column], errors="coerce")
    for column in numeric:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df.attrs["cutoff"] = (
        pd.Timestamp(cutoff).tz_localize(None).normalize() - pd.Timedelta(days=1) if cutoff else pd.NaT
    )
    return df


@lru_cache(maxsize=1)
def cargar_logistica():
    # Ventas se reduce primero a pedido: el JOIN no multiplica vendedores
    # por artículos. Logística conserva su grano pedido-vendedor.
    return _read_snapshot("""
        WITH orders AS (
            SELECT order_id, MIN(order_purchase_date) AS purchase_date,
                   MAX(LOWER(TRIM(order_status))) AS order_status
            FROM gld_sales_detail
            WHERE order_purchase_date < :cutoff
            GROUP BY order_id
        )
        SELECT l.order_id, l.seller_id, l.customer_state, l.seller_state,
               l.estimated_distance_km AS distance_km,
               l.total_freight_value AS freight,
               l.total_product_value AS product_value,
               l.order_delivered_customer_date AS delivered_date,
               l.order_estimated_delivery_date AS estimated_date,
               l.delivery_time_days AS delivery_days,
               l.review_score, o.purchase_date
        FROM gld_order_logistics l JOIN orders o USING (order_id)
        WHERE o.order_status IS NULL
           OR o.order_status NOT IN ('canceled', 'unavailable')
        ORDER BY l.order_id, l.seller_id
    """, ["purchase_date", "delivered_date", "estimated_date"],
        ["distance_km", "freight", "product_value", "delivery_days", "review_score"])


@lru_cache(maxsize=1)
def cargar_clientes():
    # Los importes y la frecuencia se recalculan desde artículos a pedidos.
    # El segmento Gold se usa solo como dimensión histórica explícita.
    return _read_snapshot("""
        WITH orders AS (
            SELECT customer_unique_id AS customer_id, order_id,
                   MIN(order_purchase_date) AS purchase_date,
                   SUM(price) AS product_value, COUNT(*) AS items,
                   MAX(review_score) AS review_score
            FROM gld_sales_detail
            WHERE order_purchase_date < :cutoff
              AND (order_status IS NULL OR LOWER(TRIM(order_status))
                   NOT IN ('canceled', 'unavailable'))
            GROUP BY customer_unique_id, order_id
        )
        SELECT o.*, c.customer_segment AS gold_segment
        FROM orders o
        LEFT JOIN gld_customer_analytics c
            ON c.customer_unique_id = o.customer_id
        ORDER BY o.purchase_date, o.order_id
    """, ["purchase_date"], ["product_value", "items", "review_score"])


@lru_cache(maxsize=1)
def cargar_clientes_gold():
    return _read_snapshot("""
        SELECT
            customer_unique_id AS customer_id,
            total_orders,
            total_items,
            total_spent,
            avg_order_value,
            avg_freight,
            avg_installments,
            preferred_payment_type,
            first_purchase_date,
            last_purchase_date,
            categories_count,
            sellers_count,
            avg_review_score,
            repeat_customer,
            customer_segment
        FROM gld_customer_analytics
        ORDER BY customer_unique_id
    """,
    ["first_purchase_date", "last_purchase_date"],
    [
        "total_orders",
        "total_items",
        "total_spent",
        "avg_order_value",
        "avg_freight",
        "avg_installments",
        "categories_count",
        "sellers_count",
        "avg_review_score",
    ])


@lru_cache(maxsize=1)
def cargar_pagos_bi():
    # Unir pagos contra pedidos ya consolidados, nunca contra artículos.
    # LEFT JOIN conserva pedidos sin pagos para informar cobertura.
    return _read_snapshot("""
        WITH orders AS (
            SELECT order_id, MIN(order_purchase_date) AS purchase_date,
                   MIN(customer_unique_id) AS customer_id
            FROM gld_sales_detail
            WHERE order_purchase_date < :cutoff
              AND (order_status IS NULL OR LOWER(TRIM(order_status))
                   NOT IN ('canceled', 'unavailable'))
            GROUP BY order_id
        ), customers AS (
            SELECT customer_unique_id, MIN(customer_segment) AS gold_segment
            FROM gld_customer_analytics
            GROUP BY customer_unique_id
        )
        SELECT o.order_id, o.purchase_date, o.customer_id, c.gold_segment,
               p.payment_sequential, p.payment_type, p.payment_value,
               p.payment_installments, (p.order_id IS NOT NULL) AS has_payment
        FROM orders o
        LEFT JOIN gld_payment_detail p ON p.order_id = o.order_id
        LEFT JOIN customers c ON c.customer_unique_id = o.customer_id
        ORDER BY o.purchase_date, o.order_id, p.payment_sequential
    """, ["purchase_date"], ["payment_value", "payment_installments"])
