import pandas as pd


def logistics_fixture():
    rows = pd.DataFrame([
        ["a", "s1", "SP", "RJ", 90, 10, 100, "2018-01-10", "2018-01-09", 9, 2, "2018-01-01"],
        ["a", "s2", "SP", "RJ", 110, 20, 200, "2018-01-10", "2018-01-09", 9, 2, "2018-01-01"],
        ["b", "s1", "SP", "RJ", None, 5, 50, None, "2018-02-01", None, None, "2018-01-20"],
        ["c", "s3", "BA", "BA", 700, 15, 300, "2018-03-08", "2018-03-09", 7, 5, "2018-03-01"],
    ], columns=["order_id", "seller_id", "customer_state", "seller_state", "distance_km",
                "freight", "product_value", "delivered_date", "estimated_date",
                "delivery_days", "review_score", "purchase_date"])
    for c in ["delivered_date", "estimated_date", "purchase_date"]:
        rows[c] = pd.to_datetime(rows[c])
    rows.attrs["cutoff"] = pd.Timestamp("2018-03-31")
    return rows


def customers_fixture():
    orders = pd.DataFrame([
        ["u1", "a", "2018-01-01", 100, 1, 1, "Segmento original"],
        ["u1", "b", "2018-01-20", 100, 1, 3, "Segmento original"],
        ["u2", "c", "2018-03-01", 300, 1, 5, "Segmento original"],
    ], columns=["customer_id", "order_id", "purchase_date", "product_value",
                "items", "review_score", "gold_segment"])
    orders["purchase_date"] = pd.to_datetime(orders["purchase_date"])
    orders.attrs["cutoff"] = pd.Timestamp("2018-03-31")
    return orders
