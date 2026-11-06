# -*- coding: utf-8 -*-
"""
05_dashboard.py —— Olist 商业分析交互大屏
=====================================================================
两种运行方式：
  1) 交互大屏（联动/筛选，推荐演示）
       D:/anaconda/python.exe -m streamlit run scripts/05_dashboard.py --server.port 8501
  2) 静态自包含页面
       D:/anaconda/python.exe scripts/05_dashboard.py --html
       -> index.html（同时复制一份到 outputs/index.html）

本次重写解决的三个问题：
  * 图表重叠：旧版把 to_html() 默认 height:100% 的 div 塞进无高度的 flex .box，
    容器高度塌陷导致多图叠在一起。现改为 12 列 CSS Grid + 每图唯一 div_id +
    明确像素高度（default_height="360px"），布局完全确定。
  * 热力图 NaN / 全浅黄：原表列缺 "18" 且上三角大量 NaN，直接送 go.Heatmap 后
    低值全落到 YlGnBu 的浅黄端。现重建 1..20 连续偏移列，按观测窗口区分
    「真实 0 留存」与「尚未进入观测期(None)」，并换用深色科技配色 + 合理 zmax。
  * 无交互：plotly.js 只内联一次到 <head>（get_plotlyjs，离线可用），
    所有图 include_plotlyjs=False 挂在同一个库上，悬停/缩放/图例全部生效。
"""
from __future__ import annotations

import os
import sys
import shutil

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_CLEAN = os.path.join(ROOT, "data", "clean")
TBL_DIR = os.path.join(ROOT, "outputs", "tables")

BG = "#101526"          # 页面/图表底色，与 04_visuals.py 统一
CARD = "#141C33"
BORDER = "#2A3550"
TXT = "#E6EBF5"
GRID_C = "#2A3550"
BLUE = "#1E90FF"
GOLD = "#FFC000"
LAST_PERIOD = pd.Period("2018-09", freq="M")   # 清洗数据最后一个完整月


# ==================== 数据 ====================
def load():
    oa = pd.read_csv(os.path.join(DATA_CLEAN, "clean_order_agg.csv"))
    items = pd.read_csv(os.path.join(DATA_CLEAN, "clean_order_items.csv"))
    states = pd.read_csv(os.path.join(DATA_CLEAN, "clean_geolocation_state.csv"))
    return oa, items, states


def kpi_cards(oa):
    return [
        ("总 GMV", f"{oa['gmv'].sum()/1e4:,.0f}", "万雷亚尔"),
        ("订单数", f"{oa['order_id'].nunique():,}", "笔"),
        ("客户数", f"{oa['customer_unique_id'].nunique():,}", "人"),
        ("平均评分", f"{oa['review_score'].mean():.2f}", "/ 5.00"),
        ("交付率", f"{(oa['order_status']=='delivered').mean()*100:.1f}", "%"),
    ]


def dark_layout(fig, title, height=360, legend=False):
    """统一深色主题：白字、深底、灰网格，所有图都带 hover。"""
    fig.update_layout(
        title=dict(text=title, font=dict(size=17, color="#FFFFFF"), x=0.02, y=0.96),
        paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(color=TXT, family="Microsoft YaHei, SimHei, sans-serif", size=12),
        margin=dict(l=64, r=24, t=62, b=52), height=height,
        hoverlabel=dict(bgcolor="#1B2540", bordercolor="#3A4A66",
                        font=dict(color="#FFFFFF", size=12)),
        xaxis=dict(gridcolor=GRID_C, zerolinecolor=GRID_C, linecolor=GRID_C,
                   tickfont=dict(color="#AAB6CC"), title_font=dict(color="#AAB6CC")),
        yaxis=dict(gridcolor=GRID_C, zerolinecolor=GRID_C, linecolor=GRID_C,
                   tickfont=dict(color="#AAB6CC"), title_font=dict(color="#AAB6CC")),
        showlegend=legend,
        legend=dict(bgcolor="rgba(20,28,46,0.85)", bordercolor=BORDER, borderwidth=1,
                    font=dict(color=TXT)) if legend else None,
    )
    return fig


# ==================== 5 个图表组件 ====================
def fig_trend(oa):
    ts = oa.groupby("purchase_month")["gmv"].sum().sort_index()
    ts = ts[ts.index >= "2016-12"]
    fig = go.Figure(go.Scatter(
        x=list(ts.index), y=(ts.values / 1e4).round(1), mode="lines+markers",
        line=dict(color=BLUE, width=3), marker=dict(size=7, color=GOLD,
                                                   line=dict(color="#FFF", width=1)),
        fill="tozeroy", fillcolor="rgba(30,144,255,0.14)",
        name="月度 GMV",
        hovertemplate="月份 %{x}<br>GMV %{y:,.1f} 万雷亚尔<extra></extra>"))
    dark_layout(fig, "月度 GMV 趋势", 360)
    fig.update_xaxes(title_text="月份", tickangle=-35)
    fig.update_yaxes(title_text="GMV（万雷亚尔）")
    return fig


def fig_map(oa, states):
    g = oa.groupby("customer_state")["gmv"].sum().reset_index()
    g = g.merge(states, on="customer_state", how="left").dropna(subset=["lat", "lng"])
    size = np.sqrt(g["gmv"] / g["gmv"].max()) * 46 + 6
    fig = go.Figure(go.Scatter(
        x=g["lng"], y=g["lat"], mode="markers",
        marker=dict(size=size, color=g["gmv"], colorscale="Blues",
                    showscale=True, line=dict(color="#8FD0FF", width=1),
                    colorbar=dict(title=dict(text="GMV", font=dict(color=TXT)),
                                  tickfont=dict(color=TXT), thickness=10)),
        text=g["customer_state"],
        customdata=np.stack([g["gmv"].values / 1e4], axis=-1),
        hovertemplate=("<b>%{text} 州</b><br>GMV %{customdata[0]:,.1f} 万雷亚尔"
                       "<br>经度 %{x:.2f} / 纬度 %{y:.2f}<extra></extra>")))
    dark_layout(fig, "各州 GMV 地理气泡", 360)
    fig.update_xaxes(title_text="经度")
    fig.update_yaxes(title_text="纬度")
    return fig


def fig_category(items, state=None, topn=12):
    d = items if state in (None, "全部") else items[items["customer_state"] == state]
    g = (d.groupby("product_category_name_english")["price"].sum()
          .sort_values(ascending=False).head(topn))
    labels = [s.replace("_", " ") for s in g.index][::-1]
    vals = (g.values / 1e4).round(1)[::-1]
    fig = go.Figure(go.Bar(
        x=vals, y=labels, orientation="h",
        marker=dict(color=vals, colorscale=[[0, "#16336B"], [1, BLUE]],
                    line=dict(color="rgba(255,255,255,0.12)", width=0.6)),
        text=[f"{v:,.1f}" for v in vals], textposition="outside",
        textfont=dict(color=TXT, size=11),
        hovertemplate="品类 %{y}<br>GMV %{x:,.1f} 万雷亚尔<extra></extra>"))
    suffix = "" if state in (None, "全部") else f"（{state} 州下钻）"
    dark_layout(fig, "各品类 GMV 结构" + suffix, 360)
    fig.update_xaxes(title_text="GMV（万雷亚尔）")
    return fig


def cohort_matrix():
    """重建完整留存矩阵：列 1..20 连续，区分「零留存」与「未观测」。

    返回 z(百分数)、text、hover 三份同形矩阵 + 行列标签。
    """
    ret = pd.read_csv(os.path.join(TBL_DIR, "cohort_retention.csv"), index_col=0)
    cnt = pd.read_csv(os.path.join(TBL_DIR, "cohort_counts.csv"), index_col=0)
    offsets = [str(i) for i in range(1, 21)]        # 补回原表缺失的 "18"
    ret = ret.reindex(columns=offsets)
    cnt = cnt.reindex(columns=offsets)
    z, text, hover = [], [], []
    for co in ret.index:
        p0 = pd.Period(str(co), freq="M")
        zr, tr, hr = [], [], []
        for off in offsets:
            k = int(off)
            if (p0 + k) > LAST_PERIOD:               # 未来月份：尚未发生，不算 0 留存
                zr.append(None)
                tr.append("—")
                hr.append(f"{co} 首购群 · 第 {k} 月<br>尚未进入观测期")
            else:
                v = ret.loc[co, off]
                val = 0.0 if pd.isna(v) else float(v)   # 观测期内无复购 = 真实 0
                n = cnt.loc[co, off]
                n = 0 if pd.isna(n) else int(n)
                zr.append(round(val * 100, 2))
                tr.append(f"{val*100:.1f}%")
                hr.append(f"{co} 首购群 · 第 {k} 月<br>留存率 {val*100:.2f}%"
                          f"<br>留存客户 {n} 人")
        z.append(zr); text.append(tr); hover.append(hr)
    return z, text, hover, [f"第{i}月" for i in range(1, 21)], list(ret.index)


def fig_cohort(height=360):
    z, text, hover, cols, rows = cohort_matrix()
    fig = go.Figure(go.Heatmap(
        z=z, x=cols, y=rows, text=text, customdata=hover,
        texttemplate="%{text}", textfont=dict(size=9),
        xgap=2, ygap=2, zmin=0, zmax=5,          # 0~5% 留存率
        # 真实分布：第1月约5%，第2月起多为0.2%~0.6%，故把色标断点压在低值区间
        colorscale=[[0.00, "#16203A"], [0.05, "#16336B"], [0.10, "#1E90FF"],
                    [0.16, "#4ED8C0"], [0.30, GOLD], [0.60, "#FF7A45"],
                    [1.00, "#FF4D4F"]],
        colorbar=dict(title=dict(text="留存率%", font=dict(color=TXT)),
                      tickfont=dict(color=TXT), thickness=10),
        hovertemplate="%{customdata}<extra></extra>"))
    dark_layout(fig, "同期群留存热力图（首购后 1–20 月）", height)
    fig.update_xaxes(title_text="首购后月数", side="bottom", tickangle=0)
    fig.update_yaxes(title_text="首购月份", autorange="reversed", tickfont=dict(size=10))
    fig.update_layout(margin=dict(l=78, r=24, t=62, b=52))
    return fig


# ==================== 静态 HTML：CSS Grid 布局 ====================
CSS = """
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#0B1020;color:#E6EBF5;
  font-family:"Microsoft YaHei","PingFang SC",SimHei,sans-serif}
header{padding:22px 28px 16px;background:linear-gradient(90deg,#101526,#16224A);
  border-bottom:1px solid #2A3550}
header h1{margin:0;font-size:24px;font-weight:700;letter-spacing:.5px}
header p{margin:8px 0 0;color:#9AA8C0;font-size:13px}
.wrap{padding:18px 24px 30px}
.kpis{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;margin-bottom:16px}
.kpi{background:linear-gradient(145deg,#18213A,#111A31);border:1px solid #2A3550;
  border-radius:12px;padding:14px 16px}
.kpi .k{font-size:12px;color:#9AA8C0}
.kpi .v{font-size:24px;font-weight:700;color:#4EA8FF;margin:6px 0 2px}
.kpi .u{font-size:11px;color:#6E7C99}
.grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:16px}
.card{background:#141C33;border:1px solid #2A3550;border-radius:12px;
  padding:8px 10px;overflow:hidden;min-width:0}
.c-trend{grid-column:span 7}.c-map{grid-column:span 5}
.c-cat{grid-column:span 5}.c-cohort{grid-column:span 7}
.card .plotly-graph-div{width:100%!important;height:360px!important}
.note{margin-top:18px;padding:14px 18px;background:#141C33;border:1px solid #2A3550;
  border-radius:12px;color:#9AA8C0;font-size:12.5px;line-height:1.9}
.note code{color:#4EA8FF;background:#0E1730;padding:2px 6px;border-radius:4px}
@media(max-width:1180px){.c-trend,.c-map,.c-cat,.c-cohort{grid-column:span 12}
  .kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}
"""


def to_div(fig, div_id, height=360):
    """每个图独立 div_id + 明确像素高度 —— 消除高度塌陷造成的重叠。"""
    return fig.to_html(
        full_html=False, include_plotlyjs=False, div_id=div_id,
        default_width="100%", default_height=f"{height}px",
        config={"responsive": True, "displaylogo": False,
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]})


def export_html():
    oa, items, states = load()
    figs = [
        ("trend", fig_trend(oa), "c-trend"),
        ("map", fig_map(oa, states), "c-map"),
        ("category", fig_category(items), "c-cat"),
        ("cohort", fig_cohort(), "c-cohort"),
    ]
    p = [f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         '<title>Olist 商业分析可视化大屏</title>',
         f'<style>{CSS}</style>',
         # plotly.js 只内联一次：离线自包含 + 全部图表共享同一个库，悬停交互可用
         f'<script type="text/javascript">{get_plotlyjs()}</script>',
         '</head><body>',
         '<header><h1>Olist 巴西电商 · 商业分析可视化大屏</h1>',
         '<p>数据源：Kaggle Olist（CC BY-NC-SA 4.0）｜全 Python 实现：Pandas / Plotly / Streamlit｜'
         '所有图表支持鼠标悬停、缩放、图例筛选</p></header>',
         '<div class="wrap"><div class="kpis">']
    for k, v, u in kpi_cards(oa):
        p.append(f'<div class="kpi"><div class="k">{k}</div>'
                 f'<div class="v">{v}</div><div class="u">{u}</div></div>')
    p.append('</div><div class="grid">')
    for name, fig, cls in figs:
        p.append(f'<div class="card {cls}">{to_div(fig, "chart_" + name)}</div>')
    p.append('</div>')
    p.append('<div class="note"><b>热力图口径：</b>行=首购月份，列=首购后第 1–20 月；'
             '第 0 月恒为 100% 已略去。观测窗口内无复购记为真实 0%，'
             '尚未进入观测期的格子显示「—」并在悬停中说明，不再以 NaN 参与配色。'
             '配色按 0–5% 留存率映射，超过 5% 饱和显示。<br>'
             '<b>静态页面</b>为交互图表合集（悬停 / 缩放 / 图例开关）；'
             '<b>真正的联动与筛选</b>（州多选、州下钻、TopN 调整，'
             '同步刷新 KPI、趋势、气泡、品类与明细）请运行 '
             '<code>D:/anaconda/python.exe -m streamlit run scripts/05_dashboard.py --server.port 8501</code>'
             ' 后访问 <code>http://localhost:8501</code>。</div>')
    p.append('</div></body></html>')

    out = os.path.join(ROOT, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(p))
    mirror = os.path.join(ROOT, "outputs", "index.html")
    shutil.copyfile(out, mirror)
    print("已生成自包含大屏:", out)
    print("同步副本:", mirror)
    print("图表数:", len(figs), "| 文件大小: %.2f MB" % (os.path.getsize(out) / 1e6))


# ==================== Streamlit 交互大屏 ====================
def run_streamlit():
    import streamlit as st
    st.set_page_config(page_title="Olist 商业分析大屏", page_icon="📊", layout="wide")
    st.title("Olist 巴西电商 · 商业分析交互大屏")
    st.caption("数据：Kaggle Olist（CC BY-NC-SA 4.0）｜Pandas / Plotly / Streamlit 全 Python 实现")

    @st.cache_data(show_spinner=False)
    def _load():
        return load()

    oa, items, states = _load()
    all_states = sorted(oa["customer_state"].dropna().unique())

    st.sidebar.header("筛选器（全局联动）")
    sel = st.sidebar.multiselect("州（可多选）", all_states, default=all_states)
    drill = st.sidebar.selectbox("州下钻（品类结构）", ["全部"] + all_states)
    topn = st.sidebar.slider("品类展示数量", 5, 20, 12)
    months = st.sidebar.slider(
        "起始月份", 0, len(sorted(oa["purchase_month"].unique())) - 6, 0)

    month_list = sorted(oa["purchase_month"].unique())[months:]
    oa_f = oa[oa["customer_state"].isin(sel) & oa["purchase_month"].isin(month_list)]
    items_f = items[items["customer_state"].isin(sel) &
                    items["purchase_month"].isin(month_list)]
    if oa_f.empty:
        st.warning("当前筛选条件下没有数据，请放宽左侧筛选器。")
        return

    cols = st.columns(5)
    for c, (k, v, u) in zip(cols, kpi_cards(oa_f)):
        c.metric(k, f"{v} {u}")

    c1, c2 = st.columns([7, 5])
    c1.plotly_chart(fig_trend(oa_f), use_container_width=True)
    c2.plotly_chart(fig_map(oa_f, states), use_container_width=True)

    c3, c4 = st.columns([5, 7])
    c3.plotly_chart(fig_category(items_f, drill, topn), use_container_width=True)
    c4.plotly_chart(fig_cohort(420), use_container_width=True)

    st.subheader("订单明细（按 GMV 降序 Top 50）")
    st.dataframe(oa_f.sort_values("gmv", ascending=False).head(50)[
        ["order_id", "customer_state", "purchase_month", "n_items",
         "gmv", "review_score"]], use_container_width=True)
    st.info("联动：左侧「州 / 起始月份」同步刷新 KPI、趋势、气泡、品类与明细；"
            "「州下钻」聚焦单一州品类结构；「品类展示数量」控制条形数量。")


def _in_streamlit_runtime():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


def main():
    if "--html" in sys.argv:
        export_html()
    elif _in_streamlit_runtime():
        run_streamlit()
    else:
        # 直接 python scripts/05_dashboard.py 时安全降级为导出静态页
        print("未检测到 Streamlit 运行时，转为导出静态 index.html。")
        print("交互大屏请执行: D:/anaconda/python.exe -m streamlit run scripts/05_dashboard.py")
        export_html()


if __name__ == "__main__":
    main()
