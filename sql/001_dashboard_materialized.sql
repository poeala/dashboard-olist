-- Private BI layer. Execute as the backend/maintenance role, never anon.
-- The runner owns the REPEATABLE READ transaction and validates before commit.
-- Deliberately do not copy the already-aggregated customer Gold or calendar.
CREATE SCHEMA IF NOT EXISTS dashboard_bi;
REVOKE ALL ON SCHEMA dashboard_bi FROM PUBLIC;

CREATE TABLE IF NOT EXISTS dashboard_bi.refresh_state (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    schema_version integer NOT NULL,
    cutoff date,
    refreshed_at timestamptz NOT NULL
);

CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard_bi.mv_order_context AS
WITH cutoff AS (
    SELECT CASE WHEN MAX(order_purchase_date) =
        (date_trunc('month', MAX(order_purchase_date)) + interval '1 month - 1 day')::date
        THEN (date_trunc('month', MAX(order_purchase_date)) + interval '1 month')::date
        ELSE date_trunc('month', MAX(order_purchase_date))::date END AS value
    FROM public.gld_sales_detail
), source AS (
    SELECT s.*, (s.order_status IS NULL OR lower(trim(s.order_status))
        NOT IN ('canceled','unavailable')) AS is_valid
    FROM public.gld_sales_detail s CROSS JOIN cutoff c
    WHERE s.order_purchase_date < c.value
)
SELECT order_id, MIN(order_purchase_date) AS purchase_date,
       MAX(lower(trim(order_status))) AS order_status,
       MIN(order_purchase_date) FILTER (WHERE is_valid) AS payment_purchase_date,
       MIN(customer_unique_id) FILTER (WHERE is_valid) AS payment_customer_id,
       COUNT(*) FILTER (WHERE is_valid) AS valid_items
FROM source GROUP BY order_id
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_order_context_order
    ON dashboard_bi.mv_order_context (order_id);
CREATE INDEX IF NOT EXISTS ix_mv_order_context_purchase
    ON dashboard_bi.mv_order_context (purchase_date);

CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard_bi.mv_customer_orders AS
WITH cutoff AS (
    SELECT CASE WHEN MAX(order_purchase_date) =
        (date_trunc('month', MAX(order_purchase_date)) + interval '1 month - 1 day')::date
        THEN (date_trunc('month', MAX(order_purchase_date)) + interval '1 month')::date
        ELSE date_trunc('month', MAX(order_purchase_date))::date END AS value
    FROM public.gld_sales_detail
), orders AS (
    SELECT s.customer_unique_id AS customer_id, s.order_id,
           MIN(s.order_purchase_date) AS purchase_date,
           SUM(s.price) AS product_value, COUNT(*) AS items,
           MAX(s.review_score) AS review_score
    FROM public.gld_sales_detail s CROSS JOIN cutoff c
    WHERE s.order_purchase_date < c.value
      AND (s.order_status IS NULL OR lower(trim(s.order_status)) NOT IN ('canceled','unavailable'))
    GROUP BY s.customer_unique_id, s.order_id
)
SELECT o.*, c.customer_segment AS gold_segment
FROM orders o LEFT JOIN public.gld_customer_analytics c ON c.customer_unique_id=o.customer_id
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_customer_orders_key
    ON dashboard_bi.mv_customer_orders (customer_id, order_id) NULLS NOT DISTINCT;
CREATE INDEX IF NOT EXISTS ix_mv_customer_orders_purchase
    ON dashboard_bi.mv_customer_orders (purchase_date);

REVOKE ALL ON ALL TABLES IN SCHEMA dashboard_bi FROM PUBLIC;
-- Supabase can have default grants to these roles. Do not expose the copies
-- of RLS-protected Gold tables through its public Data API.
DO $permissions$
DECLARE r text;
BEGIN
    FOREACH r IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname=r) THEN
            EXECUTE format('REVOKE ALL ON SCHEMA dashboard_bi FROM %I', r);
            EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA dashboard_bi FROM %I', r);
        END IF;
    END LOOP;
END
$permissions$;

COMMENT ON SCHEMA dashboard_bi IS 'Private Olist backend materializations; schema version 1; refresh using scripts/optimize_database.py';
