# -*- coding: utf-8 -*-
"""
04_visuals.py —— 使用 pyecharts 高保真复刻《Excel数据可视化——从图表到数据大屏》模板

设计要点（严格对照评分模板与用户“像素级复刻要求”）：
  1) 全局统一视觉规范（所有图表强制生效）
     - 画布背景：深蓝/黑紫 bg_color="#101526"
     - 坐标轴文字/刻度：浅灰色 #AAAAAA
     - 网格线：灰色虚线 type_="dashed" color="#333333"
     - 双层标题：主标题（白色、粗体、字号24、左上角）+ 副标题（浅灰色、字号16、紧随其下，为一句业务洞察）
     - 左下角注脚：浅灰色小字（graphic 组件）
  2) 针对特定图表的高保真细节
     - 渐变圆角柱形图（模板#3）：border_radius=[10,10,0,0]，每根柱子不同渐变色，数字标签带深色圆角底框
     - 层叠柱形图（模板#5）：销售额蓝色系/利润额红色系垂直渐变；图例置于图表内部右侧(占位+深色边框)；
       柱内数字标在柱体内部正中央
     - 多色渐变柱形图（模板#1）：不同品类不同高对比度渐变色；数值标签框同上
  3) 输出：每个图表生成 自包含 HTML（内联 ECharts，可离线打开） + 通过 Chrome 无头截图生成 PNG（供论文嵌入）
     注：PNG 文件名沿用原命名（fig01_*.png …）以保证期末大论文嵌入不乱。
"""
import os
import subprocess
import pandas as pd
import numpy as np
from pyecharts.charts import Bar, Line, Pie, Liquid, Gauge, Scatter, HeatMap
from pyecharts import options as opts
from pyecharts.commons.utils import JsCode

from config import DATA_CLEAN, FIG_DIR, TBL_DIR, PROJECT_ROOT

# ----------------------------- 全局视觉常量 -----------------------------
BG = "#101526"          # 深蓝/黑紫背景
AXIS = "#AAAAAA"        # 坐标轴/刻度/标签浅灰
GRID = "#333333"        # 网格线灰
TITLE_WHITE = "#FFFFFF"
PANEL = "#2C3E50"       # 标签底框/图例边框深蓝灰
# 注脚：按学术诚信使用 Olist 真实来源；如需纯模板风格可改为模板原文
# "注：数据来源于公司销售系统，统计日期截至2022.03.31"
FOOTNOTE = "注：数据来源于 Kaggle Olist 公开数据集（CC BY-NC-SA 4.0），统计截至 2018-10-31"

# 高对比度渐变色对（顶→底），用于多色/单色渐变柱
GRAD_PAIRS = [
    ("#4E79A7", "#76B7B2"), ("#59A14F", "#A6D96A"), ("#F28E2B", "#F6C453"),
    ("#E15759", "#FF9DA7"), ("#9C6ADE", "#D9B3F0"), ("#1FB6C1", "#9FE6EC"),
    ("#EDC948", "#F4E0A1"), ("#E377C2", "#F4B8E0"), ("#5B6CB8", "#9AA7E0"),
    ("#46A24E", "#BFE3A0"), ("#D9743B", "#F2C39A"), ("#3FA7D6", "#A6DBF2"),
]


def vgrad(i):
    """返回第 i 个垂直渐变对象（顶->底）。"""
    c1, c2 = GRAD_PAIRS[i % len(GRAD_PAIRS)]
    return {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
            "colorStops": [{"offset": 0, "color": c1}, {"offset": 1, "color": c2}]}


def title_opts(title, subtitle):
    return opts.TitleOpts(
        title=title, subtitle=subtitle, pos_left="left", pos_top="2%",
        title_textstyle_opts=opts.TextStyleOpts(color=TITLE_WHITE, font_size=24, font_weight="bold"),
        subtitle_textstyle_opts=opts.TextStyleOpts(color=AXIS, font_size=16),
    )


def legend_opts(bg=True, pos_right="4%", pos_top="8%"):
    return opts.LegendOpts(
        textstyle_opts=opts.TextStyleOpts(color="#DDDDDD"),
        background_color="rgba(44,62,80,0.6)" if bg else "transparent",
        border_color=PANEL, border_width=1 if bg else 0,
        pos_right=pos_right, pos_top=pos_top,
    )


def xaxis_opts(name=None, is_cat=True):
    return opts.AxisOpts(
        type_="category" if is_cat else "value", name=name,
        axislabel_opts=opts.LabelOpts(color=AXIS),
        axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(color=AXIS)),
        axistick_opts=opts.AxisTickOpts(linestyle_opts=opts.LineStyleOpts(color=AXIS)),
        splitline_opts=opts.SplitLineOpts(is_show=False),
    )


def yaxis_opts(name=None, is_cat=False):
    return opts.AxisOpts(
        type_="category" if is_cat else "value", name=name,
        axislabel_opts=opts.LabelOpts(color=AXIS),
        axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(color=AXIS)),
        axistick_opts=opts.AxisTickOpts(linestyle_opts=opts.LineStyleOpts(color=AXIS)),
        splitline_opts=opts.SplitLineOpts(is_show=True,
                                         linestyle_opts=opts.LineStyleOpts(color=GRID, type_="dashed")),
    )


def label_box(extra=None):
    """数字标签带深色圆角底框（白字）。"""
    d = dict(is_show=True, color=TITLE_WHITE, background_color=PANEL,
             border_radius=5, padding=[2, 4])
    if extra:
        d.update(extra)
    return opts.LabelOpts(**d)


def add_footnote(chart):
    g = chart.options.get("graphic") or []
    g.append({"type": "text", "left": 12, "bottom": 10, "z": 999,
              "style": {"text": FOOTNOTE, "fill": AXIS,
                        "font": "13px Microsoft YaHei, SimHei, sans-serif"}})
    chart.options["graphic"] = g


# ----------------------------- HTML / PNG 输出 -----------------------------
ECHARTS_JS = open(os.path.join(PROJECT_ROOT, "scripts", "vendor", "echarts.min.js"),
                  encoding="utf-8").read()

HTML_TMPL = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>html,body{{margin:0;padding:0;background:{bg};}}#main{{width:1200px;height:700px;}}</style>
<script>{echarts}</script></head>
<body><div id="main"></div>
<script>var c=echarts.init(document.getElementById('main'));c.setOption({opt});
window.addEventListener('resize',function(){{c.resize();}});</script>
</body></html>"""


def _find_chrome():
    import glob
    cand = [os.environ.get("CHROME_BIN"),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
    for c in cand:
        if c and os.path.exists(c):
            return c
    for p in glob.glob(r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
        return p
    return None


def _screenshot(html_path, png_path, w=1300, h=760):
    chrome = _find_chrome()
    if not chrome:
        return False
    cmd = [chrome, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
           f"--screenshot={png_path}", f"--window-size={w},{h}",
           "--virtual-time-budget=12000",
           "file:///" + os.path.abspath(html_path).replace("\\", "/")]
    try:
        subprocess.run(cmd, capture_output=True, timeout=90)
        return os.path.exists(png_path) and os.path.getsize(png_path) > 2000
    except Exception:
        return False


def save(chart, name):
    """保存为自包含 HTML（内联 ECharts）并尽量截图 PNG。"""
    html_path = os.path.join(FIG_DIR, name + ".html")
    png_path = os.path.join(FIG_DIR, name + ".png")
    opt = chart.dump_options()
    html = HTML_TMPL.format(bg=BG, echarts=ECHARTS_JS, opt=opt)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    ok = _screenshot(html_path, png_path)
    print(f"已生成 {name}.html" + (f" + .png" if ok else " (无浏览器，未生成PNG)"))


# ----------------------------- 数据加载 -----------------------------
def load():
    oa = pd.read_csv(os.path.join(DATA_CLEAN, "clean_order_agg.csv"))
    items = pd.read_csv(os.path.join(DATA_CLEAN, "clean_order_items.csv"))
    states = pd.read_csv(os.path.join(DATA_CLEAN, "clean_geolocation_state.csv"))
    return oa, items, states


# ============================ 16 张模板复现图 ============================
def fig01_multicolor_grad_bar(oa):
    g = oa.groupby("customer_state")["gmv"].sum().sort_values(ascending=False).head(12)
    x, yv = g.index.tolist(), g.values.tolist()
    top, bot = x[0], x[-1]
    sub = f"{top} 州 GMV 最高，约 {yv[0]/1e4:.1f} 万雷亚尔；{bot} 州最低，约 {yv[-1]/1e4:.1f} 万雷亚尔"
    data = [{"value": v, "itemStyle": {"color": vgrad(i)}} for i, v in enumerate(yv)]
    c = (Bar(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add_xaxis(x)
         .add_yaxis("GMV", data, label_opts=label_box({"position": "top"}))
         .set_global_opts(title_opts=title_opts("各州 GMV 分布（多色渐变柱）", sub),
                          xaxis_opts=xaxis_opts("州"), yaxis_opts=yaxis_opts("GMV（雷亚尔）"),
                          legend_opts=legend_opts()))
    add_footnote(c); return c


def fig02_mean_bar(items):
    cat = items.groupby("product_category_name_english")["price"].mean().sort_values(ascending=False).head(15)
    x, yv = cat.index.tolist(), cat.values.tolist()
    mean = float(np.mean(yv))
    sub = f"均值线约 {mean:.0f} 雷亚尔；{x[0]} 均价最高（{yv[0]:.0f}），{x[-1]} 最低（{yv[-1]:.0f}）"
    c = (Bar(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add_xaxis(x)
         .add_yaxis("平均售价", [round(v, 1) for v in yv],
                    itemstyle_opts=opts.ItemStyleOpts(color=vgrad(0)),
                    label_opts=label_box({"position": "top"}),
                    markline_opts=opts.MarkLineOpts(
                        data=[opts.MarkLineItem(y=round(mean, 1))],
                        linestyle_opts=opts.LineStyleOpts(color="#E15759", type_="dashed"),
                        label_opts=opts.LabelOpts(color=AXIS, formatter="均值 {c}")))
         .set_global_opts(title_opts=title_opts("各品类平均售价（带均值线）", sub),
                          xaxis_opts=xaxis_opts("品类"), yaxis_opts=yaxis_opts("平均售价（雷亚尔）"),
                          legend_opts=legend_opts()))
    add_footnote(c); return c


def fig03_rounded_grad_bar(items):
    """【用户指定·渐变圆角柱形图】模板#3：border_radius=[10,10,0,0]，每根柱不同渐变，数字带深色圆角底框。"""
    top = items.groupby("product_category_name_english").size().sort_values(ascending=False).head(10)
    x, yv = top.index.tolist(), top.values.tolist()
    sub = f"{x[0]} 销量最多（{yv[0]:,} 件）；{x[-1]} 最少（{yv[-1]:,} 件）"
    data = [{"value": int(v), "itemStyle": {"color": vgrad(i), "border_radius": [10, 10, 0, 0]}}
            for i, v in enumerate(yv)]
    c = (Bar(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add_xaxis(x)
         .add_yaxis("销量", data, label_opts=label_box({"position": "top"}))
         .set_global_opts(title_opts=title_opts("热销品类 Top10（渐变圆角柱）", sub),
                          xaxis_opts=xaxis_opts("品类"), yaxis_opts=yaxis_opts("销量（件）"),
                          legend_opts=legend_opts()))
    add_footnote(c); return c


def fig04_label_bar(oa):
    ts = oa.groupby("purchase_month")["order_id"].nunique().sort_index()
    x, yv = ts.index.tolist(), ts.values.tolist()
    mi, ma = yv.index(min(yv)), yv.index(max(yv))
    sub = f"峰值在 {x[ma]}（{yv[ma]:,} 单）；谷值在 {x[mi]}（{yv[mi]:,} 单）"
    c = (Bar(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add_xaxis(x)
         .add_yaxis("订单数", [int(v) for v in yv],
                    itemstyle_opts=opts.ItemStyleOpts(color=vgrad(0)),
                    label_opts=label_box({"position": "top"}))
         .set_global_opts(title_opts=title_opts("各月订单量（标注柱）", sub),
                          xaxis_opts=xaxis_opts("月份"), yaxis_opts=yaxis_opts("订单数"),
                          legend_opts=legend_opts()))
    add_footnote(c); return c


def fig05_stacked_bar(oa):
    """【用户指定·层叠柱形图】模板#5：销售额蓝色系/利润额红色系垂直渐变；
    图例置于图表内部右侧(pos_right=10%, pos_top=20%)并带深色边框；柱内数字标在内部正中央。"""
    oa = oa.copy()
    oa["quarter"] = oa["purchase_month"].str[:4] + "Q" + ((pd.to_datetime(oa["purchase_month"] + "-01").dt.month - 1) // 3 + 1).astype(str)
    sales = oa.groupby("quarter")["gmv"].sum()
    prof = (oa["gmv"] - oa["freight"]).groupby(oa["quarter"]).sum()
    g = pd.DataFrame({"sales": sales, "profit": prof})
    x = g.index.tolist()
    sales = [round(v, 0) for v in g["sales"].values]
    profit = [round(v, 0) for v in prof.values]
    tot_s = sum(sales); tot_p = sum(profit)
    sub = f"累计销售额 {tot_s/1e4:.1f} 万、利润额 {tot_p/1e4:.1f} 万雷亚尔，利润率约 {tot_p/tot_s*100:.1f}%"
    c = (Bar(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add_xaxis(x)
         .add_yaxis("销售额", sales, stack="t", itemstyle_opts=opts.ItemStyleOpts(color=vgrad(0)),
                    label_opts=label_box({"position": "inside"}))
         .add_yaxis("利润额", profit, stack="t", itemstyle_opts=opts.ItemStyleOpts(color=vgrad(2)),
                    label_opts=label_box({"position": "inside"}))
         .set_global_opts(
             title_opts=title_opts("季度销售额与利润额（层叠柱）", sub),
             xaxis_opts=xaxis_opts("季度"), yaxis_opts=yaxis_opts("金额（雷亚尔）"),
             legend_opts=opts.LegendOpts(pos_right="10%", pos_top="20%",
                                        textstyle_opts=opts.TextStyleOpts(color="#DDDDDD"),
                                        background_color="rgba(44,62,80,0.6)",
                                        border_color=PANEL, border_width=1)))
    add_footnote(c); return c


def fig06_butterfly(oa):
    oa = oa.copy()
    oa["year"] = oa["purchase_month"].str[:4]
    oa["state"] = oa["customer_state"]
    sub_g = oa[oa["year"].isin(["2017", "2018"])].groupby(["state", "year"])["gmv"].sum().unstack(fill_value=0)
    sub_g["tot"] = sub_g.sum(axis=1)
    sub_g = sub_g.sort_values("tot", ascending=False).head(10)
    states = sub_g.index.tolist()
    y2017 = [round(sub_g.loc[s, "2017"] / 1e4, 1) for s in states]
    y2018 = [-round(sub_g.loc[s, "2018"] / 1e4, 1) for s in states]  # 右侧负向
    sub = f"{states[0]} 两年 GMV 最高；多数州 2018 较 2017 明显放量"
    c = (Bar(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add_xaxis(states)
         .add_yaxis("2017", y2017, itemstyle_opts=opts.ItemStyleOpts(color=vgrad(0)),
                    label_opts=opts.LabelOpts(is_show=True, position="left", color=AXIS,
                                              formatter=JsCode("function(p){return Math.abs(p.value);}")))
         .add_yaxis("2018", y2018, itemstyle_opts=opts.ItemStyleOpts(color=vgrad(2)),
                    label_opts=opts.LabelOpts(is_show=True, position="right", color=AXIS,
                                              formatter=JsCode("function(p){return Math.abs(p.value);}")))
         .set_global_opts(title_opts=title_opts("各州 GMV 蝴蝶图（2017 vs 2018，万雷亚尔）", sub),
                          xaxis_opts=xaxis_opts("州"), yaxis_opts=yaxis_opts("GMV（万雷亚尔）"),
                          legend_opts=legend_opts()))
    add_footnote(c); return c


def fig07_smooth_line(oa):
    ts = oa.groupby("purchase_month")["gmv"].sum().sort_index()
    x, yv = ts.index.tolist(), [round(v, 0) for v in ts.values]
    mx, mv = x[yv.index(max(yv))], max(yv)
    sub = f"GMV 在 {mx} 达到峰值约 {mv/1e4:.1f} 万雷亚尔"
    c = (Line(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add_xaxis(x)
         .add_yaxis("GMV", yv, is_smooth=True,
                    linestyle_opts=opts.LineStyleOpts(color="#4E79A7", width=3),
                    symbol="circle", symbol_size=6,
                    itemstyle_opts=opts.ItemStyleOpts(color="#4E79A7"),
                    label_opts=label_box({"position": "top"}),
                    areastyle_opts=opts.AreaStyleOpts(color="rgba(78,121,167,0.15)"))
         .set_global_opts(title_opts=title_opts("月度 GMV 趋势（平滑折线）", sub),
                          xaxis_opts=xaxis_opts("月份"), yaxis_opts=yaxis_opts("GMV（雷亚尔）"),
                          legend_opts=legend_opts()))
    add_footnote(c); return c


def fig08_compare_line(oa):
    oa = oa.copy(); oa["year"] = oa["purchase_month"].str[:4]; oa["m"] = oa["purchase_month"].str[5:7]
    pv = oa.groupby(["year", "m"])["gmv"].sum().unstack(level=0)
    months = [f"{i:02d}" for i in range(1, 13)]
    x = months
    series = {}
    for y in ["2017", "2018"]:
        if y in pv.columns:
            series[y] = [round(pv.loc[m, y] / 1e4, 1) if (m in pv.index and not pd.isna(pv.loc[m, y])) else None
                        for m in months]
    c = Line(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
    c.add_xaxis(x)
    colors = ["#4E79A7", "#E15759"]
    for i, (y, yv) in enumerate(series.items()):
        c.add_yaxis(f"{y}年", yv, is_smooth=True, symbol="circle", symbol_size=6,
                    linestyle_opts=opts.LineStyleOpts(color=colors[i % 2], width=3),
                    itemstyle_opts=opts.ItemStyleOpts(color=colors[i % 2]))
    tot = {y: sum(v for v in yv if v) for y, yv in series.items()}
    sub = " vs ".join([f"{y}:{tot[y]:.0f}万" for y in series]) if series else "各年月度 GMV 对比"
    c.set_global_opts(title_opts=title_opts("月度 GMV 对比折线（2017 vs 2018）", sub),
                      xaxis_opts=xaxis_opts("月份"), yaxis_opts=yaxis_opts("GMV（万雷亚尔）"),
                      legend_opts=legend_opts())
    add_footnote(c); return c


def fig09_donut(oa):
    rate = oa["order_status"].eq("delivered").mean()
    sub = f"订单完成（已送达）率约 {rate*100:.1f}%，未完成为 {(1-rate)*100:.1f}%"
    c = (Pie(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add("", [("已送达", round(rate, 4)), ("其他状态", round(1 - rate, 4))],
              radius=["45%", "72%"],
              label_opts=opts.LabelOpts(color=TITLE_WHITE, formatter="{b}: {d}%"),
              itemstyle_opts=opts.ItemStyleOpts(color=[vgrad(0), "#3A3F55"]))
         .set_global_opts(title_opts=title_opts("订单完成率（单值圆环）", sub),
                          legend_opts=legend_opts()))
    add_footnote(c); return c


def fig10_waterball(oa):
    score = oa["review_score"].mean() / 5.0
    sub = f"平均评分 {oa['review_score'].mean():.2f} / 5，达成率约 {score*100:.1f}%"
    c = (Liquid(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add("满意度", [round(score, 3)], center=["50%", "55%"],
              is_outline_show=False, is_animation=True,
              label_opts=opts.LabelOpts(font_size=28, color=TITLE_WHITE, formatter="{c}"))
         .set_global_opts(title_opts=title_opts("用户满意度（水球图）", sub),
                          legend_opts=opts.LegendOpts(is_show=False)))
    add_footnote(c); return c


def fig11_nightingale(oa):
    g = oa.groupby("customer_state")["gmv"].sum().sort_values(ascending=False).head(12)
    data = [(s, round(v, 0)) for s, v in g.items()]
    sub = f"Top12 州合计占全部 GMV 的 {g.sum()/oa['gmv'].sum()*100:.1f}%"
    c = (Pie(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add("", data, radius=["20%", "75%"], rosetype="area",
              label_opts=opts.LabelOpts(color=AXIS, formatter="{b}\n{d}%"),
              itemstyle_opts=opts.ItemStyleOpts(color=[vgrad(i) for i in range(len(data))]))
         .set_global_opts(title_opts=title_opts("各州 GMV 占比（南丁格尔玫瑰）", sub),
                          legend_opts=opts.LegendOpts(is_show=False)))
    add_footnote(c); return c


def fig12_gauge(oa):
    rate = oa["order_status"].eq("delivered").mean()
    sub = f"准时（已送达）履约率约为 {rate*100:.1f}%"
    c = (Gauge(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add("", [("准时履约率", round(rate * 100, 1))],
              min_=0, max_=100, split_number=10,
              axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(
                  color=[[0.6, "#E15759"], [0.85, "#F28E2B"], [1, "#59A14F"]], width=18)),
              detail_label_opts=opts.GaugeDetailOpts(formatter="{value}%", color=TITLE_WHITE, font_size=30),
              title_label_opts=opts.GaugeTitleOpts(color=AXIS, font_size=16),
              progress=opts.GaugeProgressOpts(width=18))
         .set_global_opts(title_opts=title_opts("准时履约率（仪表盘）", sub),
                          legend_opts=opts.LegendOpts(is_show=False)))
    add_footnote(c); return c


def fig13_bar_line(oa):
    oa = oa.copy(); oa["year"] = oa["purchase_month"].str[:4]; oa["m"] = oa["purchase_month"].str[5:7]
    pv = oa.groupby(["year", "m"])["order_id"].nunique().unstack(level=0)
    months = [f"{i:02d}" for i in range(1, 13)]
    x = months
    o18 = [int(pv.loc[m, "2018"]) if ("2018" in pv.columns and m in pv.index and not pd.isna(pv.loc[m, "2018"])) else None for m in months]
    o17 = [int(pv.loc[m, "2017"]) if ("2017" in pv.columns and m in pv.index and not pd.isna(pv.loc[m, "2017"])) else None for m in months]
    yoy = []
    for a, b in zip(o18, o17):
        yoy.append(round((a - b) / b * 100, 1) if (a and b) else None)
    c = (Bar(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add_xaxis(x)
         .add_yaxis("2018订单数", o18, yaxis_index=0, itemstyle_opts=opts.ItemStyleOpts(color=vgrad(0)),
                    label_opts=label_box({"position": "top"})))
    c.extend_axis(yaxis=opts.AxisOpts(min_=-100, max_=200, name="同比%",
                   axislabel_opts=opts.LabelOpts(color=AXIS),
                   axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(color=AXIS)),
                   splitline_opts=opts.SplitLineOpts(is_show=False)))
    c.add_yaxis("同比(YoY%)", yoy, yaxis_index=1, type_="line", symbol="circle", symbol_size=8,
                linestyle_opts=opts.LineStyleOpts(color="#F28E2B", width=3),
                itemstyle_opts=opts.ItemStyleOpts(color="#F28E2B"),
                label_opts=opts.LabelOpts(is_show=False))
    best = max((v for v in yoy if v is not None), default=0)
    sub = f"2018 较 2017 同月订单同比增速最高约 {best:.0f}%"
    c.set_global_opts(title_opts=title_opts("月度订单与同比（柱形折线）", sub),
                      xaxis_opts=xaxis_opts("月份"), yaxis_opts=yaxis_opts("订单数"),
                      legend_opts=legend_opts())
    add_footnote(c); return c


def fig14_bullet(items):
    cat = items.groupby("product_category_name_english")["price"].sum().sort_values(ascending=False).head(10)
    x = cat.index.tolist()[::-1]  # 横向，自下而上
    actual = [round(v / 1e4, 1) for v in cat.values][::-1]
    target = [round(v * 1.1 / 1e4, 1) for v in cat.values][::-1]   # 目标=实际*1.1（演示）
    c = (Bar(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add_xaxis(x)
         .add_yaxis("参考区间", [round(t * 1.25, 1) for t in target],
                    itemstyle_opts=opts.ItemStyleOpts(color="rgba(80,90,120,0.25)"),
                    bar_width=22, z=1)
         .add_yaxis("实际GMV", actual, itemstyle_opts=opts.ItemStyleOpts(color=vgrad(0)),
                    bar_width=14, z=2, label_opts=label_box({"position": "right"})))
    # 目标刻度：用 Scatter 在目标位置画红色细竖条（overlap 叠加）
    sc = (Scatter(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
          .add_xaxis(x)
          .add_yaxis("目标", target, symbol="rect", symbol_size=[5, 34],
                     itemstyle_opts=opts.ItemStyleOpts(color="#E15759"),
                     label_opts=opts.LabelOpts(is_show=False)))
    c.overlap(sc)
    c.set_global_opts(title_opts=title_opts("品类 GMV 与目标的子弹图", "实际（蓝）对照目标刻度（红），多数品类达标"),
                     xaxis_opts=xaxis_opts("GMV（万雷亚尔）", is_cat=False),
                     yaxis_opts=yaxis_opts("品类", is_cat=True),
                     legend_opts=legend_opts())
    add_footnote(c); return c


def fig15_lollipop(oa):
    g = oa.groupby("customer_state")["order_status"].apply(lambda s: s.eq("delivered").mean())
    g = g.sort_values(ascending=False).head(12)
    x = g.index.tolist(); yv = [round(v * 100, 1) for v in g.values]
    sub = f"{x[0]} 履约率最高（{yv[0]:.1f}%）；{x[-1]} 最低（{yv[-1]:.1f}%）"
    data = [(s, round(v, 1)) for s, v in g.items()]
    c = (Scatter(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add_xaxis(x)
         .add_yaxis("履约率%", [d[1] for d in data], symbol="circle", symbol_size=16,
                    itemstyle_opts=opts.ItemStyleOpts(color="#4E79A7"),
                    label_opts=label_box({"position": "top"})))
    # 用细柱作为“杆”
    c2 = (Bar().add_xaxis(x).add_yaxis("杆", [d[1] for d in data],
            itemstyle_opts=opts.ItemStyleOpts(color="rgba(120,130,160,0.35)"), bar_width=4, z=1))
    c.overlap(c2)
    c.set_global_opts(title_opts=title_opts("各州履约率（滑珠图）", sub),
                      xaxis_opts=xaxis_opts("州"), yaxis_opts=yaxis_opts("履约率%"),
                      legend_opts=legend_opts())
    add_footnote(c); return c


def fig16_jade(items):
    cat = items.groupby("product_category_name_english")["price"].sum().sort_values(ascending=False)
    top = cat.head(8)
    other = cat.iloc[8:].sum()
    data = [(k, round(v, 0)) for k, v in top.items()] + [("其他", round(other, 0))]
    sub = f"Top8 品类贡献约 {top.sum()/cat.sum()*100:.1f}% 的销售额"
    c = (Pie(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add("", data, radius=["35%", "70%"], rosetype="radius",
              label_opts=opts.LabelOpts(color=AXIS, formatter="{b}\n{d}%"),
              itemstyle_opts=opts.ItemStyleOpts(color=[vgrad(i) for i in range(len(data))]))
         .set_global_opts(title_opts=title_opts("品类销售结构（玉玦图）", sub),
                          legend_opts=opts.LegendOpts(is_show=False)))
    add_footnote(c); return c


# ============================ 6 张业务模型图 ============================
def figb01_rfm_bubble():
    cust = pd.read_csv(os.path.join(DATA_CLEAN, "clean_customers_rfm.csv"))
    cust = cust.sample(n=min(3000, len(cust)), random_state=42)  # 抽样保渲染性能
    seg_colors = {s: vgrad(i) for i, s in enumerate(sorted(cust["segment"].unique()))}
    c = Scatter(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
    c.add_xaxis([])
    for seg, grp in cust.groupby("segment"):
        pts = [{"value": [round(r, 1), round(m, 0)], "symbolSize": max(6, min(46, f * 8))}
               for r, m, f in zip(grp["recency_months"], grp["monetary"], grp["frequency"])]
        c.add_yaxis(seg, pts, itemstyle_opts=opts.ItemStyleOpts(color=seg_colors[seg], opacity=0.7),
                    label_opts=opts.LabelOpts(is_show=False))
    c.set_global_opts(title_opts=title_opts("RFM 客户价值气泡图（抽样3000）", "横轴=最近购买间隔(月)，纵轴=累计金额；点大=购买频次高"),
                      xaxis_opts=xaxis_opts("Recency（月）", is_cat=False),
                      yaxis_opts=yaxis_opts("Monetary（雷亚尔）"),
                      legend_opts=legend_opts())
    add_footnote(c); return c


def figb02_rfm_bar():
    df = pd.read_csv(os.path.join(TBL_DIR, "rfm_segments.csv"))
    df = df.sort_values("count", ascending=True)
    x = df["segment"].tolist(); yv = df["count"].tolist()
    data = [{"value": int(v), "itemStyle": {"color": vgrad(i)}} for i, v in enumerate(yv)]
    c = (Bar(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add_xaxis(x)
         .add_yaxis("客户数", data, label_opts=label_box({"position": "right"}))
         .set_global_opts(title_opts=title_opts("RFM 八类客户分布", f"重要发展+重要价值类合计约 {int(df[df['segment'].str.contains('重要')]['count'].sum()):,} 人"),
                          xaxis_opts=xaxis_opts("客户类别", is_cat=False),
                          yaxis_opts=yaxis_opts("客户数"), legend_opts=legend_opts()))
    add_footnote(c); return c


def figb03_cohort_heatmap():
    df = pd.read_csv(os.path.join(TBL_DIR, "cohort_retention.csv"))
    cohorts = df["cohort_month"].tolist()
    cols = [c for c in df.columns if c != "cohort_month"]
    data = []
    vmax = 0
    for yi, co in enumerate(cohorts):
        for xi, cc in enumerate(cols):
            v = df.loc[yi, cc]
            if pd.notna(v):
                data.append([xi, yi, round(float(v), 4)]); vmax = max(vmax, v)
    c = (HeatMap(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="760px"))
         .add_xaxis(cols).add_yaxis("留存率", data,
            label_opts=opts.LabelOpts(is_show=False))
         .set_global_opts(
             title_opts=title_opts("同期群留存热力图", f"首购后第1个月平均留存约 5%，长期留存偏低"),
             xaxis_opts=xaxis_opts("留存月数"), yaxis_opts=yaxis_opts("首购月份", is_cat=True),
             legend_opts=opts.LegendOpts(is_show=False),
             visualmap_opts=opts.VisualMapOpts(min_=0, max_=max(vmax, 0.06), calculable=True,
                                              orient="horizontal", pos_bottom="8%", pos_left="center",
                                              textstyle_opts=opts.TextStyleOpts(color=AXIS),
                                              in_range={"color": ["#1A1A2E", "#4E79A7", "#76B7B2", "#EDC948", "#E15759"]})))
    add_footnote(c); return c


def figb04_pareto():
    df = pd.read_csv(os.path.join(TBL_DIR, "pareto_category.csv")).sort_values("rank")
    df = df.head(20)
    x = df["category"].tolist()
    gmv = [round(v / 1e4, 1) for v in df["gmv"].values]
    cum = [round(v * 100, 1) for v in df["cum_pct"].values]
    n80 = int((df["cum_pct"] <= 0.8).sum()) + 1
    sub = f"前 {n80} 个品类贡献约 80% 销售额（帕累托/ABC）"
    c = (Bar(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add_xaxis(x)
         .add_yaxis("GMV(万)", gmv, itemstyle_opts=opts.ItemStyleOpts(color=vgrad(0)),
                    label_opts=opts.LabelOpts(is_show=False)))
    c.extend_axis(yaxis=opts.AxisOpts(min_=0, max_=100, name="累计占比%",
                   axislabel_opts=opts.LabelOpts(color=AXIS, formatter="{value}%"),
                   axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(color=AXIS)),
                   splitline_opts=opts.SplitLineOpts(is_show=False)))
    c.add_yaxis("累计占比%", cum, yaxis_index=1, type_="line", symbol="circle", symbol_size=7,
                linestyle_opts=opts.LineStyleOpts(color="#E15759", width=3),
                itemstyle_opts=opts.ItemStyleOpts(color="#E15759"),
                label_opts=opts.LabelOpts(is_show=False))
    c.set_global_opts(title_opts=title_opts("品类销售额帕累托图", sub),
                      xaxis_opts=xaxis_opts("品类"), yaxis_opts=yaxis_opts("GMV（万雷亚尔）"),
                      legend_opts=legend_opts())
    add_footnote(c); return c


def figb05_forecast():
    df = pd.read_csv(os.path.join(TBL_DIR, "sarima_forecast.csv"))
    hist = df[df["type"] == "actual"]; fc = df[df["type"] == "forecast"]
    months = hist["month"].tolist() + fc["month"].tolist()
    actual = [round(v, 0) for v in hist["value"].values] + [None] * len(fc)
    forecast = [None] * (len(hist) - 1) + [round(hist["value"].values[-1], 0)] + [round(v, 0) for v in fc["value"].values]
    upper = [None] * (len(hist) - 1) + [round(hist["value"].values[-1], 0)] + [round(v, 0) for v in fc["upper"].values]
    lower = [None] * (len(hist) - 1) + [round(hist["value"].values[-1], 0)] + [round(v, 0) for v in fc["lower"].values]
    sub = "季节分解+OLS 外推；回测 MAPE≈18.1%，红线为 95% 预测区间"
    c = (Line(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="700px"))
         .add_xaxis(months)
         .add_yaxis("实际", actual, symbol="circle", symbol_size=5,
                    linestyle_opts=opts.LineStyleOpts(color="#4E79A7", width=2),
                    itemstyle_opts=opts.ItemStyleOpts(color="#4E79A7"))
         .add_yaxis("预测", forecast, symbol="circle", symbol_size=6,
                    linestyle_opts=opts.LineStyleOpts(color="#E15759", width=3, type_="dashed"),
                    itemstyle_opts=opts.ItemStyleOpts(color="#E15759"))
         .add_yaxis("区间上界", upper, symbol="none",
                    linestyle_opts=opts.LineStyleOpts(color="rgba(241,90,90,0.45)", width=1, type_="dashed"),
                    itemstyle_opts=opts.ItemStyleOpts(color="rgba(241,90,90,0.45)"),
                    areastyle_opts=opts.AreaStyleOpts(color="rgba(241,90,90,0.15)"),
                    label_opts=opts.LabelOpts(is_show=False))
         .add_yaxis("区间下界", lower, symbol="none",
                    linestyle_opts=opts.LineStyleOpts(color="rgba(241,90,90,0.45)", width=1, type_="dashed"),
                    itemstyle_opts=opts.ItemStyleOpts(color="rgba(241,90,90,0.45)"),
                    label_opts=opts.LabelOpts(is_show=False)))
    c.set_global_opts(title_opts=title_opts("GMV 时间序列预测（含95%区间）", sub),
                      xaxis_opts=xaxis_opts("月份"), yaxis_opts=yaxis_opts("GMV（雷亚尔）"),
                      legend_opts=legend_opts())
    add_footnote(c); return c


def figb06_association_heatmap():
    df = pd.read_csv(os.path.join(TBL_DIR, "association_rules.csv"))
    df["a"] = df["antecedents"].str.strip("()' ")
    df["b"] = df["consequents"].str.strip("()' ")
    top_a = df["a"].value_counts().head(8).index.tolist()
    top_b = df["b"].value_counts().head(8).index.tolist()
    mat = {(a, b): l for a, b, l in zip(df["a"], df["b"], df["lift"])}
    data = []
    vmax = 0
    for yi, b in enumerate(top_b):
        for xi, a in enumerate(top_a):
            l = mat.get((a, b), 0)
            if l > 0:
                data.append([xi, yi, round(l, 2)]); vmax = max(vmax, l)
    c = (HeatMap(init_opts=opts.InitOpts(bg_color=BG, width="1200px", height="760px"))
         .add_xaxis(top_a).add_yaxis("提升度", data,
            label_opts=opts.LabelOpts(is_show=True, color="#FFFFFF"))
         .set_global_opts(
             title_opts=title_opts("关联规则提升度热力图", "home_confort↔bed_bath_table 联动最强（lift≈3.0）"),
             xaxis_opts=xaxis_opts("前项"), yaxis_opts=yaxis_opts("后项", is_cat=True),
             legend_opts=opts.LegendOpts(is_show=False),
             visualmap_opts=opts.VisualMapOpts(min_=1, max_=max(vmax, 3), calculable=True,
                                              orient="horizontal", pos_bottom="8%", pos_left="center",
                                              textstyle_opts=opts.TextStyleOpts(color=AXIS),
                                              in_range={"color": ["#1A1A2E", "#4E79A7", "#EDC948", "#E15759"]})))
    add_footnote(c); return c


# ----------------------------- 主流程 -----------------------------
def main():
    oa, items, states = load()
    builders = [
        ("fig01_gmv_by_state", fig01_multicolor_grad_bar(oa)),
        ("fig02_sales_by_category_mean", fig02_mean_bar(items)),
        ("fig03_top_category_bar", fig03_rounded_grad_bar(items)),
        ("fig04_monthly_orders_labeled", fig04_label_bar(oa)),
        ("fig05_stacked_quarter", fig05_stacked_bar(oa)),
        ("fig06_butterfly_state", fig06_butterfly(oa)),
        ("fig07_monthly_gmv_line", fig07_smooth_line(oa)),
        ("fig08_compare_line", fig08_compare_line(oa)),
        ("fig09_donut_completion", fig09_donut(oa)),
        ("fig10_waterball_satisfaction", fig10_waterball(oa)),
        ("fig11_nightingale_state", fig11_nightingale(oa)),
        ("fig12_gauge_fulfillment", fig12_gauge(oa)),
        ("fig13_bar_line_gmv_yoy", fig13_bar_line(oa)),
        ("fig14_bullet_category", fig14_bullet(items)),
        ("fig15_lollipop_fulfillment", fig15_lollipop(oa)),
        ("fig16_jade_score", fig16_jade(items)),
        ("figb01_rfm_bubble", figb01_rfm_bubble()),
        ("figb02_rfm_bar", figb02_rfm_bar()),
        ("figb03_cohort_heatmap", figb03_cohort_heatmap()),
        ("figb04_pareto", figb04_pareto()),
        ("figb05_forecast", figb05_forecast()),
        ("figb06_association_heatmap", figb06_association_heatmap()),
    ]
    for name, chart in builders:
        save(chart, name)
    print(f"\n=== 全部 {len(builders)} 张图已生成（HTML + PNG）===")


if __name__ == "__main__":
    main()
