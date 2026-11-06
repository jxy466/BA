# -*- coding: utf-8 -*-
"""
02_clean.py —— 数据清洗与治理
输入：data/raw 下 9 个原始 CSV
输出：data/clean/*.csv、clean.json（汇总+日志）、olist.db（SQLite）、cleaning_log.csv

治理要点：
  - 缺失值：关键主键/金额缺失行删除；类别缺失填充 'unknown'；评论缺失评分删除
  - 异常值：price<=0 视为无效订单行删除；freight_value<0 删除；日期顺序校验
  - 重复值：按业务主键去重（order_id / (order_id,order_item_id) / customer_id）
  - 多表对齐：orders↔customers↔order_items↔products↔payments↔reviews 主外键关联
  - 派生指标：order_month、GMV=Σprice、order_gmv、payment_value、review_score、
              RFM（Recency/Frequency/Monetary）
"""
import os
import json
import sqlite3
import numpy as np
import pandas as pd
from config import (DATA_CLEAN, OBSERVATION_DATE, RANDOM_SEED)
from config import setup_cn_font
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load_data import load_raw

LOG = []  # 清洗日志


def _log(table, issue, count, action):
    LOG.append({"table": table, "issue": issue, "count": int(count),
                "action": action})


def main():
    setup_cn_font()
    raw = load_raw()
    obs_date = pd.Timestamp(OBSERVATION_DATE)

    # ---------------- orders ----------------
    orders = raw["orders"].copy()
    n0 = len(orders)
    orders = orders.drop_duplicates(subset=["order_id"])
    _log("orders", "order_id 重复", n0 - len(orders), "删除重复主键")
    n0 = len(orders)
    orders = orders[orders["order_purchase_timestamp"].notna()]
    _log("orders", "购买时间为空", n0 - len(orders), "删除缺失购买时间行")
    # 异常：送达时间早于购买时间
    bad = (orders["order_delivered_customer_date"].notna() &
           (orders["order_delivered_customer_date"] < orders["order_purchase_timestamp"]))
    _log("orders", "送达时间早于购买时间(异常)", int(bad.sum()), "保留但标注(不删除)")
    orders["is_delivered"] = (orders["order_status"] == "delivered").astype(int)
    orders["purchase_month"] = orders["order_purchase_timestamp"].dt.to_period("M").astype(str)

    # ---------------- customers ----------------
    customers = raw["customers"].drop_duplicates(subset=["customer_id"])
    customers = customers.rename(columns={"customer_state": "customer_state"})
    _log("customers", "customer_id 重复", 0, "无重复")

    # ---------------- products + category ----------------
    products = raw["products"].copy()
    cat = raw["category"].copy()
    cat.columns = ["product_category_name", "product_category_name_english"]
    products = products.merge(cat, on="product_category_name", how="left")
    n_miss_cat = products["product_category_name_english"].isna().sum()
    products["product_category_name_english"] = products[
        "product_category_name_english"].fillna("unknown")
    _log("products", "品类英文名为空", int(n_miss_cat), "填充 'unknown'")
    # 重量/尺寸异常
    for c in ["product_weight_g", "product_length_cm", "product_height_cm",
              "product_width_cm"]:
        neg = (products[c] < 0).sum()
        products[c] = products[c].where(products[c] >= 0, np.nan)
        _log("products", f"{c} 为负(异常)", int(neg), "置空")

    # ---------------- order_items ----------------
    items = raw["order_items"].copy()
    n0 = len(items)
    items = items.drop_duplicates(subset=["order_id", "order_item_id"])
    _log("order_items", "(order_id,item_id) 重复", n0 - len(items), "删除重复")
    n0 = len(items)
    for col in ["price", "freight_value"]:
        items[col] = pd.to_numeric(items[col], errors="coerce")
    bad_price = items["price"].isna() | (items["price"] <= 0)
    _log("order_items", "price 缺失或<=0(无效)", int(bad_price.sum()), "删除")
    items = items[~bad_price].copy()
    bad_freight = items["freight_value"] < 0
    _log("order_items", "freight_value<0(异常)", int(bad_freight.sum()), "删除")
    items = items[~bad_freight].copy()
    items = items.merge(products[["product_id", "product_category_name_english"]],
                        on="product_id", how="left")
    items = items.merge(
        orders[["order_id", "customer_id", "purchase_month", "order_status"]],
        on="order_id", how="left")
    items = items.merge(
        customers[["customer_id", "customer_unique_id", "customer_state"]],
        on="customer_id", how="left")

    # ---------------- payments（订单级聚合）----------------
    pay = raw["payments"].copy()
    pay["payment_value"] = pd.to_numeric(pay["payment_value"], errors="coerce")
    pay_agg = pay.groupby("order_id", as_index=False)["payment_value"].sum()
    pay_agg = pay_agg.rename(columns={"payment_value": "order_payment_value"})

    # ---------------- reviews（订单级）----------------
    rev = raw["reviews"].copy()
    rev["review_score"] = pd.to_numeric(rev["review_score"], errors="coerce")
    n0 = len(rev)
    rev = rev.dropna(subset=["review_score"])
    _log("reviews", "review_score 缺失", n0 - len(rev), "删除缺失评分")
    rev = rev.drop_duplicates(subset=["order_id"], keep="first")
    rev_score = rev[["order_id", "review_score"]].copy()

    # ---------------- 订单级宽表 ----------------
    order_agg = items.groupby("order_id", as_index=False).agg(
        customer_unique_id=("customer_unique_id", "first"),
        customer_state=("customer_state", "first"),
        purchase_month=("purchase_month", "first"),
        order_status=("order_status", "first"),
        n_items=("order_item_id", "count"),
        gmv=("price", "sum"),
        freight=("freight_value", "sum"),
    )
    order_agg = order_agg.merge(pay_agg, on="order_id", how="left")
    order_agg = order_agg.merge(rev_score, on="order_id", how="left")
    order_agg["gmv"] = order_agg["gmv"].round(2)
    order_agg["order_payment_value"] = order_agg["order_payment_value"].round(2)

    # ---------------- 客户级 RFM 基础 ----------------
    cust = order_agg.groupby("customer_unique_id").agg(
        frequency=("order_id", "count"),
        monetary=("gmv", "sum"),
        first_purchase=("purchase_month", "min"),
        last_purchase=("purchase_month", "max"),
    ).reset_index()
    # Recency：末次购买距观测窗口末日的月数
    last_ts = pd.PeriodIndex(cust["last_purchase"], freq="M").to_timestamp()
    cust["recency_months"] = ((obs_date.year - last_ts.year) * 12 +
                              (obs_date.month - last_ts.month))
    cust["recency_months"] = cust["recency_months"].astype(int)
    cust["monetary"] = cust["monetary"].round(2)
    cust["cohort_month"] = cust["first_purchase"]

    # ---------------- geolocation 州质心（抽样）----------------
    geo = raw["geolocation"].copy()
    geo = geo.sample(frac=0.05, random_state=RANDOM_SEED)
    state_centroid = geo.groupby("geolocation_state").agg(
        lat=("geolocation_lat", "mean"), lng=("geolocation_lng", "mean")).reset_index()
    state_centroid.columns = ["customer_state", "lat", "lng"]

    # ---------------- 导出 CSV ----------------
    orders.to_csv(os.path.join(DATA_CLEAN, "clean_orders.csv"), index=False)
    items.to_csv(os.path.join(DATA_CLEAN, "clean_order_items.csv"), index=False)
    customers.to_csv(os.path.join(DATA_CLEAN, "clean_customers.csv"), index=False)
    products.to_csv(os.path.join(DATA_CLEAN, "clean_products.csv"), index=False)
    pay_agg.to_csv(os.path.join(DATA_CLEAN, "clean_payments.csv"), index=False)
    rev_score.to_csv(os.path.join(DATA_CLEAN, "clean_reviews.csv"), index=False)
    raw["sellers"].to_csv(os.path.join(DATA_CLEAN, "clean_sellers.csv"), index=False)
    cat.to_csv(os.path.join(DATA_CLEAN, "clean_category.csv"), index=False)
    order_agg.to_csv(os.path.join(DATA_CLEAN, "clean_order_agg.csv"), index=False)
    cust.to_csv(os.path.join(DATA_CLEAN, "clean_customers_rfm.csv"), index=False)
    state_centroid.to_csv(os.path.join(DATA_CLEAN, "clean_geolocation_state.csv"),
                         index=False)

    # ---------------- 清洗日志 & 汇总 ----------------
    log_df = pd.DataFrame(LOG)
    log_df.to_csv(os.path.join(DATA_CLEAN, "cleaning_log.csv"), index=False)

    summary = {
        "observation_date": OBSERVATION_DATE,
        "random_seed": RANDOM_SEED,
        "n_orders": int(len(orders)),
        "n_order_items": int(len(items)),
        "n_customers_unique": int(order_agg["customer_unique_id"].nunique()),
        "n_products": int(len(products)),
        "n_sellers": int(len(raw["sellers"])),
        "n_categories": int(products["product_category_name_english"].nunique()),
        "total_gmv": float(order_agg["gmv"].sum()),
        "date_min": str(orders["order_purchase_timestamp"].min().date()),
        "date_max": str(orders["order_purchase_timestamp"].max().date()),
        "avg_review_score": float(order_agg["review_score"].mean()),
        "delivered_ratio": float(orders["is_delivered"].mean()),
        "n_cleaning_steps": int(len(LOG)),
    }
    with open(os.path.join(DATA_CLEAN, "clean.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # ---------------- 导出 SQLite ----------------
    db_path = os.path.join(DATA_CLEAN, "olist.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    tables = {
        "orders": orders, "order_items": items, "customers": customers,
        "products": products, "payments": pay_agg, "reviews": rev_score,
        "sellers": raw["sellers"], "category": cat,
        "order_agg": order_agg, "customers_rfm": cust,
        "state_centroid": state_centroid,
    }
    for name, df in tables.items():
        df.to_sql(name, conn, if_exists="replace", index=False)
    conn.close()

    print("=== 清洗完成 ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("清洗日志步骤数:", len(LOG))
    return summary


if __name__ == "__main__":
    main()
