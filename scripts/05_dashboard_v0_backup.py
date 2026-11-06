# -*- coding: utf-8 -*-
"""
05_dashboard.py —— 交互式可视化大屏
  - Streamlit 模式（默认）：python -m streamlit run scripts/05_dashboard.py
      组件≥6：KPI卡 / 趋势图 / 州地图 / 品类结构(下钻) / 同期群热力图 / 明细表
      联动：侧边栏「州筛选」联动趋势、地图、品类、明细；「州下钻」展示该州品类结构
  - 独立 HTML 模式：python scripts/05_dashboard.py --html  -> outputs/index.html
      将全部 Plotly 图与 KPI 卡片内联为一个可离线打开的大屏页面
"""
import os
import sys
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config import (DATA_CLEAN, TBL_DIR, FIG_DIR, PALETTE, PROJECT_ROOT,
                    setup_cn_font)
setup_cn_font()

ST_AVAILABLE = False
try:
    import streamlit as st
    ST_AVAILABLE = True
except ImportError:
    pass


def load():
    items = pd.read_csv(os.path.join(DATA_CLEAN, "clean_order_items.csv"))
    oa = pd.read_csv(os.path.join(DATA_CLEAN, "clean_order_agg.csv"))
    states = pd.read_csv(os.path.join(DATA_CLEAN, "clean_geolocation_state.csv"))
    cust = pd.read_csv(os.path.join(DATA_CLEAN, "clean_customers_rfm.csv"))
    return items, oa, states, cust


def fig_trend(oa):
    ts = oa.groupby("purchase_month")["gmv"].sum()
    ts = ts[ts.index >= "2016-12"]
    fig = px.line(x=ts.index, y=ts.values/1e4, markers=True,
                  title="月度 GMV 趋势", labels={"x": "月份", "y": "GMV（万雷亚尔）"})
    fig.update_traces(line=dict(width=3, color=PALETTE[0]))
    return fig


def fig_map(oa, states):
    g = oa.groupby("customer_state")["gmv"].sum().reset_index()
    g = g.merge(states, on="customer_state", how="left")
    fig = px.scatter(g.dropna(), x="lng", y="lat", size="gmv", color="gmv",
                     hover_name="customer_state", size_max=50,
                     title="各州 GMV 地理气泡图",
                     labels={"gmv": "GMV（雷亚尔）"})
    fig.update_yaxes(title="纬度"); fig.update_xaxes(title="经度")
    return fig


def fig_category(items_df, state=None):
    d = items_df if state is None else items_df[items_df["customer_state"] == state]
    g = d.groupby("product_category_name_english")["price"].sum().sort_values(
        ascending=False).head(12)
    fig = px.bar(x=g.values/1e4, y=g.index, orientation="h",
                 title=("各品类 GMV 结构" + (f"（{state} 下钻）" if state else "")),
                 labels={"x": "GMV（万雷亚尔）", "y": "品类"})
    return fig


def fig_cohort():
    cr = pd.read_csv(os.path.join(TBL_DIR, "cohort_retention.csv"), index_col=0)
    cr = cr.iloc[:, :12]
    fig = go.Figure(data=go.Heatmap(
        z=cr.values, x=[str(c) for c in cr.columns], y=cr.index,
        colorscale="YlGnBu", zmin=0, zmax=1))
    fig.update_layout(title="同期群留存热力图", xaxis_title="留存月数",
                      yaxis_title="首购月份", height=500)
    return fig


def fig_kpi_cards(oa):
    total_gmv = oa["gmv"].sum()/1e4
    n_orders = oa["order_id"].nunique()
    n_cust = oa["customer_unique_id"].nunique()
    avg_rev = oa["review_score"].mean()
    on_time = (oa["order_status"] == "delivered").mean()
    return [
        ("总 GMV", f"{total_gmv:,.0f} 万雷亚尔"),
        ("订单数", f"{n_orders:,}"),
        ("客户数", f"{n_cust:,}"),
        ("平均评分", f"{avg_rev:.2f} / 5"),
        ("交付率", f"{on_time*100:.1f}%"),
    ]


def run_streamlit():
    st.set_page_config(page_title="Olist 商业分析大屏", layout="wide")
    st.title("Olist 巴西电商 · 商业分析交互大屏")
    st.caption("数据：Kaggle Olist（CC BY-NC-SA 4.0）｜全 Python 实现（Pandas/Plotly/Streamlit）")
    items, oa, states, cust = load()

    st.sidebar.header("筛选器（联动控制）")
    all_states = sorted(oa["customer_state"].unique())
    sel_states = st.sidebar.multiselect("选择州（可多选）", all_states, default=all_states)
    drill_state = st.sidebar.selectbox("州下钻（查看该州品类结构）", ["全部"] + all_states)
    oa_f = oa[oa["customer_state"].isin(sel_states)]
    items_f = items[items["customer_state"].isin(sel_states)]

    kpis = fig_kpi_cards(oa_f)
    cols = st.columns(len(kpis))
    for c, (k, v) in zip(cols, kpis):
        c.metric(k, v)

    st.plotly_chart(fig_trend(oa_f), use_container_width=True)
    c1, c2 = st.columns([1, 1])
    c1.plotly_chart(fig_map(oa_f, states), use_container_width=True)
    c2.plotly_chart(fig_category(items_f, None if drill_state == "全部" else drill_state),
                    use_container_width=True)
    st.plotly_chart(fig_cohort(), use_container_width=True)

    st.subheader("订单明细（Top 50，按 GMV）")
    detail = oa_f.sort_values("gmv", ascending=False).head(50)[
        ["order_id", "customer_state", "purchase_month", "n_items", "gmv", "review_score"]]
    st.dataframe(detail, use_container_width=True)
    st.info("联动说明：左侧「州筛选」会同步刷新 KPI、趋势、地图、品类与明细；"
            "「州下钻」在下方的品类结构图中聚焦单一州的品类构成，实现维度下钻。")


def export_html():
    items, oa, states, cust = load()
    kpis = fig_kpi_cards(oa)
    figs = {
        "trend": fig_trend(oa),
        "map": fig_map(oa, states),
        "category": fig_category(items, None),
        "cohort": fig_cohort(),
    }
    parts = []
    parts.append("""<html><head><meta charset="utf-8">
<title>Olist 商业分析大屏</title>
<style>
 body{font-family:"Microsoft YaHei",SimHei,sans-serif;margin:0;background:#f4f6f9;color:#222}
 header{background:#4E79A7;color:#fff;padding:18px 28px}
 .kpis{display:flex;gap:14px;padding:18px 28px}
 .kpi{flex:1;background:#fff;border-radius:10px;padding:16px;box-shadow:0 2px 6px rgba(0,0,0,.08);text-align:center}
 .kpi .v{font-size:22px;font-weight:700;color:#4E79A7}
 .kpi .k{font-size:13px;color:#777;margin-top:4px}
 .row{display:flex;gap:18px;padding:0 28px 18px}
 .box{background:#fff;border-radius:10px;padding:10px;box-shadow:0 2px 6px rgba(0,0,0,.08);flex:1}
 h2{font-size:16px;margin:6px 0}
 .note{padding:0 28px 28px;color:#555;font-size:13px;line-height:1.7}
</style></head><body>""")
    parts.append("<header><h1>Olist 巴西电商 · 商业分析可视化大屏</h1>"
                "<div>数据源：Kaggle Olist（CC BY-NC-SA 4.0）｜全 Python 实现：Pandas / Plotly / Streamlit</div></header>")
    parts.append('<div class="kpis">')
    for k, v in kpis:
        parts.append(f'<div class="kpi"><div class="v">{v}</div><div class="k">{k}</div></div>')
    parts.append("</div>")
    parts.append('<div class="row"><div class="box"><h2>月度 GMV 趋势</h2>'
                + figs["trend"].to_html(full_html=False, include_plotlyjs="inline") + "</div></div>")
    parts.append('<div class="row"><div class="box"><h2>各州 GMV 地理气泡图</h2>'
                + figs["map"].to_html(full_html=False, include_plotlyjs=False) + "</div>"
                '<div class="box"><h2>各品类 GMV 结构</h2>'
                + figs["category"].to_html(full_html=False, include_plotlyjs=False) + "</div></div>")
    parts.append('<div class="row"><div class="box"><h2>同期群留存热力图</h2>'
                + figs["cohort"].to_html(full_html=False, include_plotlyjs=False) + "</div></div>")
    parts.append('<div class="note"><b>联动与下钻说明：</b>本静态页面为交互图表合集（可悬停、缩放、框选）。'
                '完整联动/下钻交互（左侧州筛选器同步刷新 KPI、趋势、地图、品类与明细；州下钻聚焦单一州品类结构）'
                '请运行 <code>python -m streamlit run scripts/05_dashboard.py</code> 启动实时大屏。</div>')
    parts.append("</body></html>")
    out = os.path.join(PROJECT_ROOT, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print("已生成独立大屏页面:", os.path.abspath(out))


def main():
    if "--html" in sys.argv or not ST_AVAILABLE:
        export_html()
    else:
        run_streamlit()


if __name__ == "__main__":
    main()
