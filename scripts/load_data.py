# -*- coding: utf-8 -*-
"""
01_load.py —— 原始数据加载（白名单：官方下载 CSV，严禁爬虫）。
返回各原始表的 DataFrame 字典，统一解析日期、处理 BOM。
"""
import os
import pandas as pd
from config import DATA_RAW

DATE_COLS = {
    "olist_orders_dataset.csv": [
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "olist_order_reviews_dataset.csv": [
        "review_creation_date", "review_answer_timestamp",
    ],
    "olist_order_items_dataset.csv": ["shipping_limit_date"],
}


def load_raw():
    """加载 data/raw 下的 9 个 Olist CSV，返回 {name: DataFrame}。"""
    files = {
        "orders": "olist_orders_dataset.csv",
        "order_items": "olist_order_items_dataset.csv",
        "payments": "olist_order_payments_dataset.csv",
        "reviews": "olist_order_reviews_dataset.csv",
        "customers": "olist_customers_dataset.csv",
        "products": "olist_products_dataset.csv",
        "sellers": "olist_sellers_dataset.csv",
        "geolocation": "olist_geolocation_dataset.csv",
        "category": "product_category_name_translation.csv",
    }
    out = {}
    for key, fname in files.items():
        path = os.path.join(DATA_RAW, fname)
        # 翻译表含 BOM，用 utf-8-sig；其余 utf-8
        enc = "utf-8-sig" if key == "category" else "utf-8"
        parse_dates = DATE_COLS.get(fname, [])
        # geolocation 仅保留绘图所需列，降低内存
        usecols = None
        if key == "geolocation":
            usecols = ["geolocation_zip_code_prefix", "geolocation_lat",
                       "geolocation_lng", "geolocation_state"]
        df = pd.read_csv(path, encoding=enc, parse_dates=parse_dates,
                         usecols=usecols, low_memory=False)
        out[key] = df
        print(f"[load] {key:12s} shape={df.shape}")
    return out


if __name__ == "__main__":
    data = load_raw()
    print("加载完成，共", len(data), "张表")
