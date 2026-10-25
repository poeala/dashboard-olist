-- Outside a transaction. Primary-key and purchase-date indexes already exist.
-- Supports seller drill-down by seller and purchase date without indexing
-- every Gold column or duplicating the existing join indexes.
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_gld_sales_seller_purchase
    ON public.gld_sales_detail (seller_id, order_purchase_date);
