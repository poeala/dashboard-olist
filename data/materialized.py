"""SQL contracts for the private materialized layer (schema version 1)."""
import os
from sqlalchemy import text

SCHEMA_VERSION = 1

LOGISTICS_SQL = """
    SELECT l.order_id, l.seller_id, l.customer_state, l.seller_state,
           l.estimated_distance_km AS distance_km,
           l.total_freight_value AS freight, l.total_product_value AS product_value,
           l.order_delivered_customer_date AS delivered_date,
           l.order_estimated_delivery_date AS estimated_date,
           l.delivery_time_days AS delivery_days, l.review_score, o.purchase_date
    FROM public.gld_order_logistics l
    JOIN dashboard_bi.mv_order_context o USING (order_id)
    WHERE o.order_status IS NULL OR o.order_status NOT IN ('canceled', 'unavailable')
    ORDER BY l.order_id, l.seller_id
"""

CUSTOMERS_SQL = """
    SELECT customer_id, order_id, purchase_date, product_value, items, review_score, gold_segment
    FROM dashboard_bi.mv_customer_orders
    ORDER BY purchase_date, order_id
"""

PAYMENTS_SQL = """
    SELECT o.order_id, o.payment_purchase_date AS purchase_date,
           o.payment_customer_id AS customer_id, c.customer_segment AS gold_segment,
           p.payment_sequential, p.payment_type, p.payment_value,
           p.payment_installments, (p.order_id IS NOT NULL) AS has_payment
    FROM dashboard_bi.mv_order_context o
    LEFT JOIN public.gld_payment_detail p ON p.order_id = o.order_id
    LEFT JOIN public.gld_customer_analytics c ON c.customer_unique_id = o.payment_customer_id
    WHERE o.valid_items > 0
    ORDER BY o.payment_purchase_date, o.order_id, p.payment_sequential
"""


def materialized_state(conn):
    mode = os.getenv('DASHBOARD_USE_MATERIALIZED', 'auto').lower()
    if mode not in {'auto', 'on', 'off'}:
        raise ValueError('DASHBOARD_USE_MATERIALIZED must be auto, on or off')
    if mode == 'off':
        return None
    # Inspect the catalog without resolving objects in a potentially absent
    # schema. Do not catch permission/connection errors as "not installed".
    exists = conn.execute(text("""
        SELECT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          WHERE n.nspname='dashboard_bi' AND c.relname='refresh_state' AND c.relkind='r')
    """)).scalar()
    if not exists:
        if mode == 'on':
            raise RuntimeError('The dashboard materialized layer is not installed')
        return None
    state = conn.execute(text('SELECT schema_version, cutoff, refreshed_at FROM dashboard_bi.refresh_state WHERE singleton')).mappings().one_or_none()
    if state is None or state['schema_version'] != SCHEMA_VERSION:
        raise RuntimeError('The dashboard materialized layer requires a compatible refresh')
    return state
