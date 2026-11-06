# -*- coding: utf-8 -*-
"""
04_visuals.py —— 《商业数据分析》期末大作业 · 深色科技风图表（完整版 22 张）
==========================================================================
全部图表使用 pyecharts / ECharts 生成，严格对照《Excel数据可视化——从图表到数据大屏》
模板风格与用户确认的 7 条视觉规范：

  ① 深色背景      InitOpts(bg_color="#101526", is_fill_bg_color=True)
  ② 双层标题      TitleOpts 主标题白/粗/24 + 副标题浅灰/20（副标题写真实业务洞察）
  ③ 坐标轴/网格   浅灰白轴文字 + 可见刻度 + #333333 虚线网格
  ④ 数值标签加框  LabelOpts(background_color="#2C3E50", border_radius=5, padding=[2,5])
  ⑤ 渐变/圆角柱   ItemStyleOpts(color={colorStops}, border_radius=[10,10,0,0])
  ⑥ 图例          图表内部、带边框、不置底
  ⑦ 左下角注脚    graphic 组件浅灰小字（必须显式 font_size，否则字体大小为 0 而隐形）

★ fig05 按用户确认的模板截图改为「交叠柱」：销售额为宽蓝柱在后、利润额为窄红柱在前，
  两柱共享基线、barGap="-100%" 完全重叠（NOT stack 堆叠），图例为右侧中部两个彩色边框方框。

数据：全部来自 data/clean/*.csv 与 outputs/tables/*.csv 的真实清洗/建模结果，无任何编造数值。
      Olist 不含成本字段，「利润额」= 销售额 − 运费（净收入口径），已在注脚声明。

输出：outputs/figures/figXX_*.html —— 全部用 chart.render() 输出，ECharts 与 liquidfill
      插件均内联进 HTML，单文件自包含、离线可开、可直接浏览器截图；不使用 make_snapshot。
PNG ：运行同目录 06_export_png.py 批量把 HTML 截成同名高清 PNG（供 make_docx.py 嵌入）。

运行： D:/anaconda/python.exe scripts/04_visuals.py
"""
from __future__ import annotations

import ast
import math
import os
import re
import shutil
import unicodedata

import numpy as np
import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Bar, Gauge, HeatMap, Line, Liquid, Pie, Scatter
from pyecharts.commons.utils import JsCode
from pyecharts.globals import CurrentConfig

# 独立解析路径，避免引入 matplotlib / config.py 的字体设置等无关依赖
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_CLEAN = os.path.join(PROJECT_ROOT, "data", "clean")
TBL_DIR = os.path.join(PROJECT_ROOT, "outputs", "tables")
FIG_DIR = os.path.join(PROJECT_ROOT, "outputs", "figures")
VENDOR = os.path.join(PROJECT_ROOT, "scripts", "vendor")
os.makedirs(FIG_DIR, exist_ok=True)

# ==================== 1. 全局视觉规范 ====================
BG = "#101526"
TITLE_C, SUB_C = "#FFFFFF", "#9AA8C0"
AXIS_TXT, AXIS_LINE, GRID_LINE = "#AAB6CC", "#5A6480", "#333333"
PANEL, FOOT_C = "#2C3E50", "#8892A6"
WHITE, GOLD_C, RED_C, GREEN_C = "#FFFFFF", "#FFC000", "#FF6B8A", "#2BE0A5"
W, H = "1280px", "720px"
RADIUS = [10, 10, 0, 0]
FONT = "Microsoft YaHei, SimHei, sans-serif"

# ---- 论文可读性字号（只调字号，配色/数据/图形一律不动） ----
FS_SUBTITLE = 20      # 标题下的副标题（原 16）
FS_FOOTNOTE = 18      # 左下角注脚（原 16，再放大一档）
FS_AXIS_NAME = 16     # 坐标轴名称（原 13）
FS_AXIS_LABEL = 15    # 坐标轴刻度文字（原 12）
FS_VALUE = 16         # 柱子上方/内部的数值标签（原 12）
FS_DENSE_VALUE = 14   # 密集图（多月/多柱/蝴蝶图）数值标签（原 11~13）
FS_ANNOTATION = 14    # 图上标注：均值线/峰谷/玫瑰标签/双轴刻度/色标（原 11~12）
FS_HEAT_VALUE = 13    # 热力图单元格数值（原 11，格高有限不宜过大）
NOTE_WRAP = 58        # 注脚单行最大等效全角字数，超出自动折行

FOOTNOTE = ("*注：数据来源于 Kaggle Olist 公开数据集（原公司销售系统交易明细，"
            "CC BY-NC-SA 4.0），统计截至 2018-10-31；Olist 不含成本字段，"
            "「利润额」按「销售额−运费」的净收入口径近似估算。")

DEFAULT_GRID = {"left": "8%", "right": "5%", "top": "24%", "bottom": "16%",
                "containLabel": True}


def _use_local_echarts() -> str:
    """render() 引用同目录 echarts.min.js，随后由 render() 内联成单文件。"""
    src = os.path.join(VENDOR, "echarts.min.js")
    dst = os.path.join(FIG_DIR, "echarts.min.js")
    if os.path.exists(src):
        if not os.path.exists(dst) or os.path.getsize(src) != os.path.getsize(dst):
            shutil.copyfile(src, dst)
        return "./"
    return "https://assets.pyecharts.org/assets/v6/"


CurrentConfig.ONLINE_HOST = _use_local_echarts()


def init():
    return opts.InitOpts(width=W, height=H, bg_color=BG, is_fill_bg_color=True,
                         page_title="Olist 商业数据分析 · 深色科技风图表")


def gradient(top: str, bottom: str) -> dict:
    """ECharts 原生线性渐变：offset=0 柱顶（亮），offset=1 柱底（深）。"""
    return {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
            "colorStops": [{"offset": 0, "color": top},
                           {"offset": 1, "color": bottom}],
            "global": False}


def area_gradient(top: str = "rgba(30,144,255,0.55)",
                  bottom: str = "rgba(30,144,255,0.02)") -> dict:
    return {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
            "colorStops": [{"offset": 0, "color": top},
                           {"offset": 1, "color": bottom}],
            "global": False}


BLUE = gradient("#1E90FF", "#00008B")
BLUE_LIGHT = gradient("#00D2FF", "#0A3A8C")
RED = gradient("#FF6B8A", "#8A174A")       # 模板珊瑚红
GOLD = gradient("#FFC000", "#B34700")
GREEN = gradient("#2BE0A5", "#0B6B4F")
PURPLE = gradient("#7B61FF", "#2B1B6B")
MULTI = [gradient(a, b) for a, b in [
    ("#00D2FF", "#0A3A8C"), ("#1E90FF", "#00008B"), ("#7B61FF", "#2B1B6B"),
    ("#C86BFF", "#4A1B7A"), ("#FF6BA8", "#8A174A"), ("#FF8A5B", "#8A2B00"),
    ("#FFC000", "#8A5A00"), ("#A8E05F", "#2F6B1B"), ("#2BE0A5", "#0B6B4F"),
    ("#22D3EE", "#0A5A73"), ("#6C8BFF", "#1B2A73"), ("#9FA8DA", "#283593"),
]]
MULTI_TOP = ["#00D2FF", "#1E90FF", "#7B61FF", "#C86BFF", "#FF6BA8", "#FF8A5B",
             "#FFC000", "#A8E05F", "#2BE0A5", "#22D3EE", "#6C8BFF", "#9FA8DA"]


# ------------------------- 通用样式组件 -------------------------
def title(main: str, insight: str):
    """② 双层标题：主标题白/粗/24，副标题浅灰/20（真实业务洞察，论文中更清晰）。"""
    return opts.TitleOpts(
        title=main, subtitle=insight, pos_left="5%", pos_top="4%", item_gap=12,
        title_textstyle_opts=opts.TextStyleOpts(
            color=TITLE_C, font_size=24, font_weight="bold", font_family=FONT),
        subtitle_textstyle_opts=opts.TextStyleOpts(
            color=SUB_C, font_size=FS_SUBTITLE, font_family=FONT),
    )


def label_box(position="top", formatter=None, size=FS_VALUE):
    """④ 白色数值 + #2C3E50 深色圆角底框（字号放大，论文中可读）。"""
    return opts.LabelOpts(
        is_show=True, position=position, color=WHITE, font_size=size,
        font_weight="bold", background_color=PANEL, border_color="#4A6079",
        border_width=1, border_radius=5, padding=[2, 5], formatter=formatter,
    )


def hidden_label():
    return opts.LabelOpts(is_show=False)


def cat_axis(name="", rotate=0, formatter=None):
    """③ 类目轴：浅灰白文字、可见刻度、无实心网格。"""
    return opts.AxisOpts(
        type_="category", name=name, name_location="middle", name_gap=38,
        name_textstyle_opts=opts.TextStyleOpts(color=AXIS_TXT,
                                               font_size=FS_AXIS_NAME),
        axislabel_opts=opts.LabelOpts(color=AXIS_TXT, font_size=FS_AXIS_LABEL,
                                      rotate=rotate, formatter=formatter),
        axisline_opts=opts.AxisLineOpts(
            linestyle_opts=opts.LineStyleOpts(color=AXIS_LINE)),
        axistick_opts=opts.AxisTickOpts(
            is_show=True, linestyle_opts=opts.LineStyleOpts(color=AXIS_LINE)),
        splitline_opts=opts.SplitLineOpts(is_show=False),
    )


def val_axis(name="", formatter=None, min_=None, max_=None,
             name_location="end", name_gap=None):
    """③ 数值轴：浅灰白文字 + #333333 虚线网格。
    横向图/散点图请传 name_location="middle"，避免轴名孤零零挂在右下角。"""
    kw = {"name_location": name_location}
    if name_gap is not None:
        kw["name_gap"] = name_gap
    if min_ is not None:
        kw["min_"] = min_
    if max_ is not None:
        kw["max_"] = max_
    return opts.AxisOpts(
        type_="value", name=name, **kw,
        name_textstyle_opts=opts.TextStyleOpts(color=AXIS_TXT,
                                               font_size=FS_AXIS_NAME),
        axislabel_opts=opts.LabelOpts(color=AXIS_TXT, font_size=FS_AXIS_LABEL,
                                      formatter=formatter),
        axisline_opts=opts.AxisLineOpts(
            is_show=True, linestyle_opts=opts.LineStyleOpts(color=AXIS_LINE)),
        axistick_opts=opts.AxisTickOpts(is_show=False),
        splitline_opts=opts.SplitLineOpts(
            is_show=True,
            linestyle_opts=opts.LineStyleOpts(color=GRID_LINE,
                                              type_="dashed", width=1)),
    )


def legend(show=True, right="4%", top="10%", vertical=False):
    """⑥ 图例在图表内部（默认右上角），带深色边框与半透明底。"""
    return opts.LegendOpts(
        is_show=show, pos_right=right, pos_top=top,
        orient="vertical" if vertical else "horizontal",
        textstyle_opts=opts.TextStyleOpts(color="#E6EBF5", font_size=12),
        background_color="rgba(20,28,46,0.88)" if show else "transparent",
        border_color="#3A4A66", border_width=1 if show else 0,
        border_radius=6, padding=[8, 12],
        item_width=16, item_height=10, item_gap=10 if vertical else 14,
    )


_BRACKET_PAT = re.compile(r"（[^（）]*）|\([^()]*\)")


def _strip_brackets(text: str) -> str:
    """按用户要求：去掉注脚中的括号以及括号内的全部文字，只保留括号外的内容。

    在 footnote() 统一处理，因此 16 种注脚一次生效，图表数据、配色与其它文案均不改动。
    """
    prev = None
    while prev != text:                     # 兼容嵌套括号：由内向外逐层删除
        prev = text
        text = _BRACKET_PAT.sub("", text)
    return text


def _wrap_note(text: str, limit: int = NOTE_WRAP) -> str:
    """注脚字号放大后自动折行：按等效全角宽度断行，优先在中文标点后断，文字内容不变。"""
    def cw(c):
        return 1.0 if unicodedata.east_asian_width(c) in "WF" else 0.55

    lines, cur, width = [], "", 0.0
    for ch in text:
        w = cw(ch)
        if width + w > limit and cur:
            cut = max(cur.rfind(p) for p in "；，。、）: ")
            if cut >= len(cur) * 0.55:
                lines.append(cur[:cut + 1])
                cur = cur[cut + 1:]
                width = sum(cw(c) for c in cur)
            else:
                lines.append(cur)
                cur, width = "", 0.0
        cur += ch
        width += w
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def footnote(text=FOOTNOTE):
    """⑦ 左下角浅灰小字 —— 官方 GraphicText（font_size 必须显式给，否则为 0）。

    本轮仅调整注脚：去掉括号内容、字号放大一档、整体位置上移（bottom 2% → 4%）。
    上移幅度取稳妥值，避免与圆环/仪表盘底部标签及热力图色标相撞。
    """
    return opts.GraphicText(
        graphic_item=opts.GraphicItem(left="5%", bottom="4%", z=100),
        graphic_textstyle_opts=opts.GraphicTextStyleOpts(
            text=_wrap_note(_strip_brackets(text)), font_size=FS_FOOTNOTE,
            font=f"{FS_FOOTNOTE}px " + FONT,
            graphic_basicstyle_opts=opts.GraphicBasicStyleOpts(fill=FOOT_C)),
    )


def graphic_text(text, left=None, top=None, right=None, bottom=None,
                 size=14, color=WHITE, weight="normal", z=100):
    """原生 graphic 文本元素（与 pyecharts 的 graphic_opts 同处 graphic.elements）。"""
    pos = {"z": z}
    for k, v in (("left", left), ("top", top), ("right", right), ("bottom", bottom)):
        if v is not None:
            pos[k] = v
    return {"type": "text", **pos,
            "style": {"text": text, "fill": color,
                      "font": f"{weight} {size}px {FONT}"}}


def graphic_rect(left, top, width, height, stroke, fill="rgba(16,21,38,0.88)",
                 radius=5, z=99):
    return {"type": "rect", "left": left, "top": top, "z": z,
            "shape": {"width": width, "height": height, "r": radius},
            "style": {"fill": fill, "stroke": stroke, "lineWidth": 1.6}}


def add_graphics(chart, elements):
    """把原生 graphic 元素追加到 set_global_opts(graphic_opts=...) 生成的结构中。"""
    g = chart.options.get("graphic")
    if g is None:
        chart.options["graphic"] = {"elements": list(elements)}
    elif isinstance(g, dict):
        g.setdefault("elements", []).extend(elements)
    elif isinstance(g, list):
        chart.options["graphic"] = {"elements": g + list(elements)}
    return chart


TOOLTIP = opts.TooltipOpts(
    trigger="axis", axis_pointer_type="shadow",
    background_color="rgba(16,21,38,0.94)", border_color="#3A4A66",
    textstyle_opts=opts.TextStyleOpts(color="#E6EBF5", font_size=13),
)
TOOLTIP_ITEM = opts.TooltipOpts(
    trigger="item", background_color="rgba(16,21,38,0.94)",
    border_color="#3A4A66",
    textstyle_opts=opts.TextStyleOpts(color="#E6EBF5", font_size=13),
)


def finish(chart, main, insight, xaxis=None, yaxis=None, *, leg=None,
           grid="auto", extra=None, tooltip=None, graphics=None, note=FOOTNOTE):
    """统一收口：标题 / 图例 / tooltip / 坐标轴 / 虚线网格 / 注脚 / graphic。"""
    kw = dict(title_opts=title(main, insight),
              legend_opts=leg or opts.LegendOpts(is_show=False),
              tooltip_opts=tooltip or TOOLTIP,
              graphic_opts=[footnote(note)])
    if xaxis is not None:
        kw["xaxis_opts"] = xaxis
    if yaxis is not None:
        kw["yaxis_opts"] = yaxis
    if extra:
        kw.update(extra)
    chart.set_global_opts(**kw)
    if grid:
        g = dict(DEFAULT_GRID if grid == "auto" else grid)
        # 注脚放大后会折成两行，原 bottom=16%/18% 的图需抬高绘图区，避免压住 x 轴名称。
        b = g.get("bottom")
        if isinstance(b, str) and b.endswith("%") and float(b[:-1]) < 20:
            g["bottom"] = "20%"
        chart.options["grid"] = g
    if graphics:
        add_graphics(chart, graphics)
    return chart


def render(chart, name, liquid=False):
    """chart.render() 输出网页；再把 ECharts（水球另加插件）内联，得到单文件自包含 HTML。"""
    path = os.path.join(FIG_DIR, name + ".html")
    chart.render(path)
    js_path = os.path.join(FIG_DIR, "echarts.min.js")
    tag = '<script type="text/javascript" src="./echarts.min.js"></script>'
    if os.path.exists(js_path):
        with open(path, encoding="utf-8") as f:
            html = f.read()
        if tag in html:
            with open(js_path, encoding="utf-8") as f:
                js = f.read()
            block = '<script type="text/javascript">\n' + js + '\n</script>'
            if liquid:
                plug_path = os.path.join(VENDOR, "echarts-liquidfill.min.js")
                with open(plug_path, encoding="utf-8") as f:
                    block += ('\n<script type="text/javascript">\n' + f.read()
                              + '\n</script>')
            html = html.replace(tag, block)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
    print("[OK]", os.path.basename(path))
    return path


# ------------------------- 数据加载 -------------------------
def load():
    oa = pd.read_csv(os.path.join(DATA_CLEAN, "clean_order_agg.csv"))
    items = pd.read_csv(os.path.join(DATA_CLEAN, "clean_order_items.csv"))
    rfm_full = pd.read_csv(os.path.join(TBL_DIR, "rfm_full.csv"))
    rfm_seg = pd.read_csv(os.path.join(TBL_DIR, "rfm_segments.csv"))
    cohort = pd.read_csv(os.path.join(TBL_DIR, "cohort_retention.csv"))
    pareto = pd.read_csv(os.path.join(TBL_DIR, "pareto_category.csv"))
    forecast = pd.read_csv(os.path.join(TBL_DIR, "sarima_forecast.csv"))
    rules = pd.read_csv(os.path.join(TBL_DIR, "association_rules.csv"))
    return dict(oa=oa, items=items, rfm_full=rfm_full, rfm_seg=rfm_seg,
                cohort=cohort, pareto=pareto, forecast=forecast, rules=rules)


# 系列标签：pyecharts 2.1.0 会把部分系列（Line/Scatter）的数据编码成 [x, y] 数组，
# 因此 formatter 必须同时兼容「纯数值」与「[x, y] 数组」两种 p.value 形态。
_NUM = "var v=(p.value instanceof Array)?p.value[p.value.length-1]:p.value;"
FMT_INT = JsCode("function(p){" + _NUM + "return Math.round(Number(v)).toLocaleString('en-US');}")
FMT_1 = JsCode("function(p){" + _NUM + "return Number(v).toFixed(1);}")
FMT_ABS = JsCode("function(p){" + _NUM + "return Math.abs(Number(v)).toFixed(0);}")
# 坐标轴刻度回调的第一个参数是「数值」而不是对象，必须单独写，否则会出现 NaN 刻度
AXIS_ABS = JsCode("function(v){return Math.abs(Number(v)).toFixed(0);}")


# ==========================================================================
# 第一部分：16 张模板复现图
# ==========================================================================
def fig01_gmv_by_state(D):
    """① 多色渐变柱形图：各州 GMV Top12，每柱一套渐变。"""
    oa = D["oa"]
    g = oa.groupby("customer_state")["gmv"].sum().sort_values(ascending=False).head(12)
    total = oa["gmv"].sum()
    states, vals = list(g.index), [round(v / 1e4, 1) for v in g.values]
    insight = (f"{states[0]} 州 GMV {vals[0]:,.1f} 万雷亚尔居首，占全国 "
               f"{g.iloc[0]/total*100:.1f}%；Top3 合计 {g.head(3).sum()/total*100:.1f}%")
    bars = [opts.BarItem(name=s, value=v, itemstyle_opts=opts.ItemStyleOpts(
        color=MULTI[i % len(MULTI)], border_radius=RADIUS,
        border_color="rgba(255,255,255,0.10)", border_width=0.5))
        for i, (s, v) in enumerate(zip(states, vals))]
    bar = (Bar(init_opts=init()).add_xaxis(states)
           .add_yaxis("GMV（万雷亚尔）", bars, bar_width="55%",
                      label_opts=label_box("top", FMT_1)))
    return finish(bar, "各州 GMV 贡献对比（Top12）", insight,
                  cat_axis("州"), val_axis("GMV（万雷亚尔）"))


def fig02_mean_bar(D):
    """② 带均值线柱形图：各品类平均售价 + 整体均价参考线。"""
    g = (D["items"].groupby("product_category_name_english")["price"]
         .mean().sort_values(ascending=False).head(12))
    cats = [c.replace("_", " ") for c in g.index]
    vals = [round(v, 1) for v in g.values]
    overall = float(D["items"]["price"].mean())
    above = int((g.values > overall).sum())
    insight = f"全站平均售价 {overall:.0f} 雷亚尔；Top12 中 {above} 个品类高于均值，{cats[0]} 最贵（{vals[0]:.0f}）"
    bar = (Bar(init_opts=init()).add_xaxis(cats)
           .add_yaxis("平均售价", vals, bar_width="56%",
                      itemstyle_opts=opts.ItemStyleOpts(
                          color=BLUE, border_radius=RADIUS),
                      label_opts=label_box("top", FMT_1),
                      markline_opts=opts.MarkLineOpts(
                          data=[opts.MarkLineItem(y=round(overall, 1), name="整体均价")],
                          linestyle_opts=opts.LineStyleOpts(
                              color=GOLD_C, width=2, type_="dashed"),
                          label_opts=opts.LabelOpts(
                              color=GOLD_C, font_size=FS_ANNOTATION,
                              position="insideStartTop",   # 字号放大后避免右端被裁切
                              formatter=JsCode("function(p){return '均值 '+p.value;}")))))
    return finish(bar, "品类平均售价（带均值线）", insight,
                  cat_axis("商品品类", rotate=22), val_axis("平均售价（雷亚尔）"),
                  grid={"left": "8%", "right": "5%", "top": "26%",
                        "bottom": "28%", "containLabel": True})


def fig03_top_category_bar(D):
    """③ 渐变圆角柱形图：Top10 热销品类，蓝渐变 + 圆角 + 带框数值标签。"""
    items = D["items"]
    g = (items.groupby("product_category_name_english").size()
         .sort_values(ascending=False).head(10))
    cats = [c.replace("_", " ") for c in g.index]
    vals = [int(v) for v in g.values]
    share = g.sum() / len(items) * 100
    insight = (f"{cats[0]} 销量最多，{vals[0]:,} 件；"
               f"Top10 品类合计占全部订单明细的 {share:.1f}%")
    bars = [opts.BarItem(name=c, value=v, itemstyle_opts=opts.ItemStyleOpts(
        color=BLUE, border_radius=RADIUS,
        border_color="rgba(255,255,255,0.12)", border_width=0.6))
        for c, v in zip(cats, vals)]
    bar = (Bar(init_opts=init()).add_xaxis(cats)
           .add_yaxis("销量（件）", bars, bar_width="52%",
                      label_opts=label_box("top", FMT_INT)))
    return finish(bar, "热销品类 Top10 销量对比", insight,
                  cat_axis("商品品类", rotate=18), val_axis("销量（件）"),
                  grid={"left": "8%", "right": "5%", "top": "26%",
                        "bottom": "26%", "containLabel": True})


def fig04_monthly_orders_labeled(D):
    """④ 标注柱形图：逐月订单量，柱顶带框标注数值。"""
    ts = D["oa"].groupby("purchase_month")["order_id"].nunique().sort_index()
    # 剔除 2016 起步期（月订单个位数）与 2018-09 不完整月末（仅 1 单，会形成假断崖）
    ts = ts[(ts.index >= "2017-01") & (ts.index <= "2018-08")]
    x, y = list(ts.index), [int(v) for v in ts.values]
    peak, low = ts.idxmax(), ts.idxmin()
    insight = (f"{peak} 订单量峰值 {ts.max():,} 单；{low} 最少 {ts.min():,} 单，"
               f"期间月均 {ts.mean():,.0f} 单")
    bar = (Bar(init_opts=init()).add_xaxis(x)
           .add_yaxis("订单数", y, bar_width="58%",
                      itemstyle_opts=opts.ItemStyleOpts(
                          color=BLUE_LIGHT, border_radius=RADIUS),
                      label_opts=label_box("top", FMT_INT, size=FS_DENSE_VALUE)))
    return finish(bar, "月度订单量（标注柱）", insight,
                  cat_axis("月份", rotate=38), val_axis("订单数（单）"),
                  grid={"left": "8%", "right": "5%", "top": "26%",
                        "bottom": "26%", "containLabel": True},
                  note="*注：数据来源于 Kaggle Olist 公开数据集（CC BY-NC-SA 4.0）；"
                       "剔除 2016 年平台起步期与 2018-09 不完整月末（仅 1 单），"
                       "展示 2017-01 至 2018-08 共 20 个完整自然月。")


def fig05_stacked_quarter(D):
    """⑤★ 交叠柱形图（按用户提供的模板截图重做，非堆叠）：
       宽蓝柱「销售额」在后、窄红柱「利润额」在前，同一基线、barGap=-100% 完全重叠；
       两根柱子顶部各自带框数字；右侧中部两个彩色边框图例框；x 轴首季显示年份。
    """
    d = D["oa"].copy()
    d["quarter"] = (d["purchase_month"].str[:4] + "Q" +
                    ((d["purchase_month"].str[5:7].astype(int) - 1) // 3 + 1).astype(str))
    q = d.groupby("quarter").agg(sales=("gmv", "sum"),
                                 freight=("freight", "sum"),
                                 orders=("order_id", "count"))
    q = q[(q.index >= "2017Q1") & (q["orders"] >= 100)]   # 剔除起步期/样本过小季度
    q["profit"] = q["sales"] - q["freight"]               # 净收入口径近似利润额
    sales = [int(round(v / 1e4)) for v in q["sales"]]
    profit = [int(round(v / 1e4)) for v in q["profit"]]
    peak = q["sales"].idxmax()
    insight = (f"{peak} 销售额最高（{q.loc[peak,'sales']/1e4:,.0f} 万雷亚尔）；"
               f"全期运费占销售额 {q['freight'].sum()/q['sales'].sum()*100:.1f}%，"
               f"净收入率 {(1-q['freight'].sum()/q['sales'].sum())*100:.1f}%")
    # 模板式 x 轴：每年首个季度写全年，其余只写 Qn
    labels = [f"{qi[:4]}{qi[4:]}" if qi.endswith("Q1") else qi[4:]
              for qi in q.index]
    fmt = JsCode("function(p){return Number(p.value).toLocaleString('en-US');}")
    # 模板右侧中部：两个独立的彩色边框图例方框（仍在图表内部、带边框、不置底）
    legend_graphics = [
        graphic_rect("78%", "39%", 112, 34, "#1E90FF"),
        graphic_text("销售额", left="79.3%", top="40.3%", size=14, color="#E6EBF5", z=101),
        graphic_rect("78%", "46%", 112, 34, "#FF6B8A"),
        graphic_text("利润额", left="79.3%", top="47.3%", size=14, color="#E6EBF5", z=101),
    ]
    bar = (Bar(init_opts=init())
           .add_xaxis(labels)
           .add_yaxis("销售额", sales, bar_width=48,
                      itemstyle_opts=opts.ItemStyleOpts(
                          color=BLUE, border_radius=RADIUS,
                          border_color="rgba(255,255,255,0.10)", border_width=0.6),
                      label_opts=label_box("top", fmt, size=15))
           .add_yaxis("利润额", profit, bar_width=34,
                      itemstyle_opts=opts.ItemStyleOpts(
                          color=RED, border_radius=RADIUS,
                          border_color="rgba(255,255,255,0.18)", border_width=0.8),
                      label_opts=label_box("top", fmt, size=15)))
    # 关键：两系列完全重叠（同一 x 位置）且红柱绘制在蓝柱之前
    series = bar.options["series"]
    for s in series:
        s["barGap"] = "-100%"          # 两系列共用同一类目位置 → 前后交叠（非 stack 堆叠）
    # 注：不要用像素数值 barGap 试图让窄柱居中，ECharts 会把整组柱推到相邻类目。
    # 改为「宽蓝柱 48 / 窄红柱 34」，红柱覆盖蓝柱约 70%，与模板的重叠比例一致。
    series[0]["z"], series[1]["z"] = 2, 4
    return finish(bar, "2017—2018 季度销售额(万)与利润额(万)", insight,
                  cat_axis("季度"), val_axis("金额（万雷亚尔）"),
                  leg=opts.LegendOpts(is_show=False),  # 模板式图例由 graphic 绘制
                  graphics=legend_graphics)


def fig06_butterfly(D):
    """⑥ 蝴蝶图：Top10 州 2017（左）/2018（右）GMV 背靠背横向条。"""
    oa = D["oa"].copy()
    oa["year"] = oa["purchase_month"].str[:4]
    p = oa[oa["year"].isin(["2017", "2018"])
           & (oa["purchase_month"] <= "2018-08")].groupby(
        ["customer_state", "year"])["gmv"].sum().unstack(fill_value=0)
    p["total"] = p.sum(axis=1)
    p = p.sort_values("total", ascending=False).head(10)
    states = list(p.index)[::-1]
    v17 = [-round(p.loc[s, "2017"] / 1e4) for s in states]
    v18 = [round(p.loc[s, "2018"] / 1e4) for s in states]
    r = p.loc[states[0]] if False else p.loc[p["total"].idxmax()]
    insight = (f"{p['total'].idxmax()} 两年累计 GMV 最高（{p['total'].max()/1e4:,.0f} 万）；"
               f"2018 年 Top10 合计 {p['2018'].sum()/1e4:,.0f} 万雷亚尔")
    bar = (Bar(init_opts=init()).add_xaxis(states)
           .add_yaxis("2017", v17, bar_width=15,
                      itemstyle_opts=opts.ItemStyleOpts(color=BLUE, border_radius=6),
                      label_opts=label_box("left", FMT_ABS, size=FS_DENSE_VALUE))
           .add_yaxis("2018", v18, bar_width=15,
                      itemstyle_opts=opts.ItemStyleOpts(color=RED, border_radius=6),
                      label_opts=label_box("right", FMT_ABS, size=FS_DENSE_VALUE))
           .reversal_axis())
    return finish(bar, "各州 GMV 蝴蝶图（2017 vs 2018）", insight,
                  val_axis("GMV（万雷亚尔）", formatter=AXIS_ABS,
                           name_location="middle", name_gap=32),
                  cat_axis("州"), leg=legend(show=True, top="10%"),
                  grid={"left": "12%", "right": "8%", "top": "24%",
                        "bottom": "16%", "containLabel": True},
                  note="*注：数据来源于 Kaggle Olist 公开数据集（CC BY-NC-SA 4.0）；"
                       "左侧为 2017 年、右侧为 2018 年各州 GMV（万雷亚尔），"
                       "2018 年取 1—8 月完整月（9 月仅 1 单已剔除）。")


def fig07_monthly_gmv_line(D):
    """⑦ 平滑折线图：月度 GMV + 渐变面积 + 峰值/谷值标注。"""
    ts = D["oa"].groupby("purchase_month")["gmv"].sum().sort_index()
    ts = ts[(ts.index >= "2017-01") & (ts.index <= "2018-08")]
    x = list(ts.index)
    y = [round(v / 1e4, 1) for v in ts.values]
    insight = (f"{ts.idxmax()} 达峰值 {ts.max()/1e4:,.0f} 万雷亚尔，"
               f"较 {x[0]} 增长 {(ts.iloc[-1]/ts.iloc[0]-1)*100:.0f}%")
    line = (Line(init_opts=init()).add_xaxis(x)
            .add_yaxis("GMV（万雷亚尔）", y, is_smooth=True,
                       symbol="circle", symbol_size=7,
                       linestyle_opts=opts.LineStyleOpts(color="#1E90FF", width=3),
                       itemstyle_opts=opts.ItemStyleOpts(
                           color="#1E90FF", border_color="#FFFFFF", border_width=1),
                       areastyle_opts=opts.AreaStyleOpts(color=area_gradient()),
                       label_opts=hidden_label(),
                       markpoint_opts=opts.MarkPointOpts(
                           data=[opts.MarkPointItem(type_="max", name="峰值"),
                                 opts.MarkPointItem(type_="min", name="谷值")],
                           label_opts=opts.LabelOpts(color=WHITE, font_size=FS_ANNOTATION))))
    return finish(line, "月度 GMV 趋势（平滑折线）", insight,
                  cat_axis("月份", rotate=38), val_axis("GMV（万雷亚尔）"),
                  grid={"left": "8%", "right": "5%", "top": "26%",
                        "bottom": "26%", "containLabel": True},
                  note="*注：数据来源于 Kaggle Olist 公开数据集（CC BY-NC-SA 4.0）；"
                       "剔除 2016 年起步期与 2018-09 不完整月末（仅 1 单），"
                       "展示 2017-01 至 2018-08 共 20 个完整自然月。")


def fig08_compare_line(D):
    """⑧ 对比折线图：2017 / 2018 各月 GMV 双线对照。"""
    oa = D["oa"].copy()
    oa["year"], oa["m"] = oa["purchase_month"].str[:4], oa["purchase_month"].str[5:7]
    pv = oa.groupby(["year", "m"])["gmv"].sum().unstack(level=0)
    months = [f"{i:02d}" for i in range(1, 13)]
    s17 = ([round(pv.loc[m, "2017"] / 1e4, 1)
            if (m in pv.index and not pd.isna(pv.loc[m, "2017"])) else None
            for m in months])
    s18 = ([round(pv.loc[m, "2018"] / 1e4, 1)
            if ("2018" in pv.columns and m in pv.index and m <= "08"
                and not pd.isna(pv.loc[m, "2018"]))
            else None for m in months])   # 2018-09 仅 1 单，剔除以免形成假断崖
    overlap_m = [m for m, a, b in zip(months, s17, s18) if a and b]
    growth = (sum(b - a for m, a, b in zip(months, s17, s18) if a and b)
              / sum(a for m, a, b in zip(months, s17, s18) if a and b) * 100)
    insight = f"{len(overlap_m)} 个可比月份中，2018 年 GMV 合计较 2017 年同期增长 {growth:.1f}%"
    line = (Line(init_opts=init()).add_xaxis(months)
            .add_yaxis("2017 年", s17, is_smooth=True, symbol="circle", symbol_size=6,
                       linestyle_opts=opts.LineStyleOpts(color="#1E90FF", width=3),
                       itemstyle_opts=opts.ItemStyleOpts(color="#1E90FF"),
                       label_opts=hidden_label())
            .add_yaxis("2018 年", s18, is_smooth=True, symbol="circle", symbol_size=6,
                       linestyle_opts=opts.LineStyleOpts(color=GOLD_C, width=3),
                       itemstyle_opts=opts.ItemStyleOpts(color=GOLD_C),
                       label_opts=hidden_label()))
    return finish(line, "月度 GMV 对比（2017 vs 2018）", insight,
                  cat_axis("月份"), val_axis("GMV（万雷亚尔）"),
                  leg=legend(show=True),
                  note="*注：数据来源于 Kaggle Olist 公开数据集（CC BY-NC-SA 4.0）；"
                       "2018-09 仅 1 单属不完整月末，已剔除，故 9—12 月留空，不做插值填补。")


def fig09_donut(D):
    """⑨ 单值圆环图：订单完成（已送达）率，中心大数字。"""
    rate = float(D["oa"]["order_status"].eq("delivered").mean())
    pct = round(rate * 100, 1)
    insight = f"已送达 {int(D['oa']['order_status'].eq('delivered').sum()):,} 单，占全部订单 {pct}%；其余为在途/取消等状态"
    pie = (Pie(init_opts=init())
           .add("", [opts.PieItem(name="已送达", value=pct,
                                  itemstyle_opts=opts.ItemStyleOpts(
                                      color=BLUE, border_color=BG, border_width=3)),
                     opts.PieItem(name="其他状态", value=round(100 - pct, 1),
                                  itemstyle_opts=opts.ItemStyleOpts(
                                      color="#243052", border_color=BG, border_width=3))],
                radius=["48%", "68%"], center=["50%", "56%"],
                label_opts=hidden_label()))
    gfx = [graphic_text(f"{pct}%", left="center", top="49%", size=48,
                        color=WHITE, weight="bold"),
           graphic_text("订单完成率（已送达）", left="center", top="61%",
                        size=15, color=SUB_C),
           # 标签位置按模板要求：蓝色环左侧贴近环、灰色缺口正上方贴近环顶
           graphic_text("已送达", left="27.5%", top="54%", size=13, color="#1E90FF"),
           graphic_text("其他状态", left="47%", top="17.5%", size=13, color=SUB_C)]
    return finish(pie, "订单完成率（单值圆环）", insight,
                  grid=None, tooltip=TOOLTIP_ITEM, graphics=gfx)


def fig10_waterball(D):
    """⑩ 水球图（pyecharts Liquid + echarts-liquidfill 插件内联）：平均评分达成率。"""
    score = float(D["oa"]["review_score"].mean())
    pct = score / 5.0
    good = float((D["oa"]["review_score"] >= 4).mean() * 100)
    insight = (f"平均评分 {score:.2f} / 5（达成率 {pct*100:.1f}%）；"
               f"4—5 分好评占 {good:.1f}%")
    lq = (Liquid(init_opts=init())
          .add("满意度", [round(pct, 3)], center=["50%", "57%"],
               color=["#1E90FF", "#0A3A8C", "#00D2FF"],
               is_outline_show=True, outline_border_distance=6,
               outline_itemstyle_opts=opts.ItemStyleOpts(
                   border_color="#4A7FD0", border_width=3),
               label_opts=opts.LabelOpts(
                   font_size=44, color=WHITE, font_weight="bold",
                   formatter=JsCode("function(p){return (p.value*100).toFixed(1)+'%';}"))))
    gfx = [graphic_text("平均评分 / 5 分制", left="center", top="88%",
                        size=14, color=SUB_C)]
    return finish(lq, "用户满意度（水球图）", insight,
                  grid=None, tooltip=TOOLTIP_ITEM, graphics=gfx,
                  note="*注：数据来源于 Kaggle Olist 公开数据集（CC BY-NC-SA 4.0）；"
                       "液位 = 平均评论评分 ÷ 5，已剔除评分缺失记录。")


def fig11_nightingale(D):
    """⑪ 南丁格尔玫瑰图：Top12 州 GMV 占比，逐扇区渐变。"""
    g = D["oa"].groupby("customer_state")["gmv"].sum().sort_values(ascending=False).head(12)
    total = D["oa"]["gmv"].sum()
    insight = (f"{g.index[0]} 州占比 {g.iloc[0]/total*100:.1f}% 居首；"
               f"Top12 州合计贡献 {g.sum()/total*100:.1f}% 的 GMV")
    data = [opts.PieItem(name=s, value=round(v / 1e4, 1),
                         itemstyle_opts=opts.ItemStyleOpts(
                             color=MULTI[i % len(MULTI)],
                             border_color=BG, border_width=2))
            for i, (s, v) in enumerate(g.items())]
    pie = (Pie(init_opts=init())
           .add("", data, radius=["12%", "64%"], center=["47%", "51%"],
                rosetype="area", is_clockwise=True,
                label_opts=opts.LabelOpts(color="#D6DEF0", font_size=FS_ANNOTATION,
                                          formatter="{b}  {d}%")))
    return finish(pie, "各州 GMV 占比（南丁格尔玫瑰）", insight,
                  grid=None, tooltip=TOOLTIP_ITEM)


def fig12_gauge(D):
    """⑫ 仪表盘：订单交付（已送达）履约率。"""
    rate = float(D["oa"]["order_status"].eq("delivered").mean() * 100)
    insight = (f"整体履约率 {rate:.1f}%；"
               f"未送达 {int((~D['oa']['order_status'].eq('delivered')).sum()):,} 单需重点跟进")
    gauge = (Gauge(init_opts=init())
             .add("", [("准时履约率", round(rate, 1))],
                  min_=0, max_=100, split_number=10, radius="76%",
                  center=["50%", "58%"], start_angle=225, end_angle=-45,
                  axisline_opts=opts.AxisLineOpts(
                      linestyle_opts=opts.LineStyleOpts(
                          color=[[0.6, "#FF6B6B"], [0.85, GOLD_C], [1, GREEN_C]],
                          width=22)),
                  progress=opts.GaugeProgressOpts(
                      is_show=True, width=22, is_round_cap=True,
                      itemstyle_opts=opts.ItemStyleOpts(color=BLUE_LIGHT)),
                  pointer=opts.GaugePointerOpts(
                      is_show=True, length="62%", width=6,
                      itemstyle_opts=opts.ItemStyleOpts(color=WHITE)),
                  axislabel_opts=opts.LabelOpts(color=AXIS_TXT, font_size=FS_ANNOTATION,
                                                distance=-42, formatter="{value}"),
                  axistick_opts=opts.AxisTickOpts(
                      is_show=True, length=8,
                      linestyle_opts=opts.LineStyleOpts(color=AXIS_LINE, width=1)),
                  detail_label_opts=opts.GaugeDetailOpts(
                      formatter="{value}%", color=WHITE, font_size=40,
                      font_weight="bold", offset_center=[0, "62%"]),
                  title_label_opts=opts.GaugeTitleOpts(
                      color=SUB_C, font_size=16, offset_center=[0, "88%"])))
    return finish(gauge, "整体履约率（仪表盘）", insight,
                  grid=None, tooltip=TOOLTIP_ITEM,
                  note="*注：数据来源于 Kaggle Olist 公开数据集（CC BY-NC-SA 4.0）；"
                       "履约率以订单状态 delivered（已送达）口径统计。")


def fig13_bar_line_yoy(D):
    """⑬ 柱形折线复合图：2018 月度订单柱 + 同比增长率折线（双轴）。"""
    oa = D["oa"].copy()
    oa["year"], oa["m"] = oa["purchase_month"].str[:4], oa["purchase_month"].str[5:7]
    pv = oa.groupby(["year", "m"])["order_id"].nunique().unstack(level=0)
    months = [f"{i:02d}" for i in range(1, 13)]
    get = lambda m, y: int(pv.loc[m, y]) if (y in pv.columns and m in pv.index
                                             and not pd.isna(pv.loc[m, y])) else None
    v18 = [get(m, "2018") if m <= "08" else None for m in months]
    v17 = [get(m, "2017") for m in months]
    yoy = [round((a - b) / b * 100, 1) if (a and b) else None
           for a, b in zip(v18, v17)]
    valid = [v for v in yoy if v is not None]
    insight = (f"2018 年 1—{len(valid):02d} 月订单同比平均增长 {np.mean(valid):.1f}%，"
               f"最高 {max(valid):.1f}%")
    bar = (Bar(init_opts=init()).add_xaxis(months)
           .add_yaxis("2018 订单数", v18, bar_width="52%",
                      itemstyle_opts=opts.ItemStyleOpts(
                          color=BLUE, border_radius=RADIUS),
                      label_opts=hidden_label()))
    bar.extend_axis(yaxis=opts.AxisOpts(
        type_="value", name="同比（%）", min_=-100, max_=300,
        name_textstyle_opts=opts.TextStyleOpts(color=AXIS_TXT,
                                               font_size=FS_AXIS_NAME),
        axislabel_opts=opts.LabelOpts(color=GOLD_C, font_size=FS_ANNOTATION,
                                      formatter="{value}%"),
        axisline_opts=opts.AxisLineOpts(
            linestyle_opts=opts.LineStyleOpts(color=AXIS_LINE)),
        splitline_opts=opts.SplitLineOpts(is_show=False)))
    line = (Line().add_xaxis(months)
            .add_yaxis("同比增长率", yoy, yaxis_index=1, is_smooth=True,
                       symbol="circle", symbol_size=8,
                       linestyle_opts=opts.LineStyleOpts(color=GOLD_C, width=3),
                       itemstyle_opts=opts.ItemStyleOpts(color=GOLD_C),
                       label_opts=hidden_label()))
    bar.overlap(line)
    return finish(bar, "月度订单量与同比（柱形折线）", insight,
                  cat_axis("月份"), val_axis("订单数（单）"),
                  leg=legend(show=True),
                  note="*注：数据来源于 Kaggle Olist 公开数据集（CC BY-NC-SA 4.0）；"
                       "柱=2018 年月订单数，线=对 2017 年同月同比增速（右轴）；"
                       "2018-09 仅 1 单属不完整月末，已剔除，故 9—12 月不显示。")


def fig14_bullet(D):
    """⑭ 子弹图：各品类「全期累计 GMV」（宽底）与「2018 年 GMV」（窄条）交叠对比。
       目标/实际均为真实统计值，不做任何人为放大。
    """
    items = D["items"]
    total = items.groupby("product_category_name_english")["price"].sum()
    y2018 = items[items["purchase_month"].str[:4] == "2018"].groupby(
        "product_category_name_english")["price"].sum()
    df = pd.DataFrame({"total": total, "y18": y2018}).fillna(0)
    df = df.sort_values("total", ascending=False).head(10)
    cats = [c.replace("_", " ") for c in df.index][::-1]
    base = [round(v / 1e4, 1) for v in df["total"].values][::-1]
    actual = [round(v / 1e4, 1) for v in df["y18"].values][::-1]
    share = df["y18"].sum() / df["total"].sum() * 100
    insight = (f"{df.index[0].replace('_',' ')} 累计 GMV 最高；"
               f"Top10 品类 2018 年贡献占其累计 GMV 的 {share:.1f}%")
    bar = (Bar(init_opts=init()).add_xaxis(cats)
           .add_yaxis("全期累计 GMV", base, bar_width=28,
                      itemstyle_opts=opts.ItemStyleOpts(
                          color="rgba(90,110,160,0.28)", border_radius=6),
                      label_opts=hidden_label())
           .add_yaxis("2018 年 GMV", actual, bar_width=13,
                      itemstyle_opts=opts.ItemStyleOpts(
                          color=BLUE_LIGHT, border_radius=6),
                      label_opts=label_box("right", FMT_1, size=FS_DENSE_VALUE))
           .reversal_axis())
    for s in bar.options["series"]:
        s["barGap"] = "-100%"          # 窄蓝条叠在宽灰底上，形成子弹图
    bar.options["series"][0]["z"] = 2
    bar.options["series"][1]["z"] = 4
    return finish(bar, "品类 GMV 子弹图（累计 vs 2018）", insight,
                  val_axis("GMV（万雷亚尔）", name_location="middle", name_gap=32),
                  cat_axis("商品品类"),
                  leg=legend(show=True),
                  grid={"left": "16%", "right": "10%", "top": "24%",
                        "bottom": "16%", "containLabel": True},
                  note="*注：数据来源于 Kaggle Olist 公开数据集（CC BY-NC-SA 4.0）；"
                       "宽底=全期累计商品金额，窄条=2018 年（截至 9 月）商品金额，均为真实统计值。")


def fig15_lollipop(D):
    """⑮ 滑珠图：各州订单完成率（细杆 + 圆珠）。"""
    oa = D["oa"]
    g = oa.groupby("customer_state")["order_status"].apply(
        lambda s: s.eq("delivered").mean() * 100)
    g = g.sort_values(ascending=False).head(12)
    states, vals = list(g.index), [round(v, 1) for v in g.values]
    insight = (f"{states[0]} 履约率最高 {vals[0]:.1f}%；Top12 平均 "
               f"{np.mean(vals):.1f}%，最低 {states[-1]} {vals[-1]:.1f}%")
    bar = (Bar(init_opts=init()).add_xaxis(states)
           .add_yaxis("履约率基线", vals, bar_width=4,
                      itemstyle_opts=opts.ItemStyleOpts(
                          color="rgba(120,150,210,0.35)"),
                      label_opts=hidden_label()))
    sc = (Scatter().add_xaxis(states)
          .add_yaxis("履约率", vals, symbol="circle", symbol_size=17,
                     itemstyle_opts=opts.ItemStyleOpts(
                         color=MULTI_TOP[0], border_color=WHITE, border_width=1.5,
                         opacity=0.95),
                     label_opts=label_box("top", FMT_1, size=FS_DENSE_VALUE)))
    bar.overlap(sc)
    return finish(bar, "各州履约率（滑珠图）", insight,
                  cat_axis("州"), val_axis("履约率（%）", min_=95, max_=100),
                  grid={"left": "8%", "right": "5%", "top": "26%",
                        "bottom": "18%", "containLabel": True},
                  note="*注：数据来源于 Kaggle Olist 公开数据集（CC BY-NC-SA 4.0）；"
                       "履约率 = 该州已送达订单数 ÷ 全部订单数，仅展示 Top12 州；"
                       "纵轴自 95% 起截断以放大州际差异（全州实际值均在 98% 以上）。")


def fig16_jade(D):
    """⑯ 玉玦图：好评率以环形进度（留缺口）呈现。"""
    good = float((D["oa"]["review_score"] >= 4).mean() * 100)
    good = round(good, 1)
    insight = (f"4—5 分好评占 {good}%；平均评分 "
               f"{D['oa']['review_score'].mean():.2f} / 5，整体口碑良好")
    pie = (Pie(init_opts=init())
           .add("", [opts.PieItem(name="好评（4—5 分）", value=good,
                                  itemstyle_opts=opts.ItemStyleOpts(
                                      color=GREEN, border_color=BG, border_width=3)),
                     opts.PieItem(name="其他评分", value=round(100 - good, 1),
                                  itemstyle_opts=opts.ItemStyleOpts(
                                      color="#243052", border_color=BG, border_width=3))],
                radius=["52%", "70%"], center=["50%", "56%"],
                start_angle=90, label_opts=hidden_label()))
    gfx = [graphic_text(f"{good}%", left="center", top="49%", size=44,
                        color=WHITE, weight="bold"),
           graphic_text("好评率（4—5 分）", left="center", top="61%",
                        size=15, color=SUB_C)]
    return finish(pie, "好评率（玉玦环形图）", insight,
                  grid=None, tooltip=TOOLTIP_ITEM, graphics=gfx,
                  note="*注：数据来源于 Kaggle Olist 公开数据集（CC BY-NC-SA 4.0）；"
                       "已剔除评分缺失记录，缺口部分表示非好评订单占比。")


# ==========================================================================
# 第二部分：6 张业务模型图（与第 4 章模型一一对应）
# ==========================================================================
def fig17_rfm_bubble(D):
    """B1 RFM 客户价值气泡图：R×M 散点，气泡大小=F，颜色=八类分群（分层抽样）。"""
    df = D["rfm_full"].copy()
    cap = df["monetary"].quantile(0.99)
    df = df[df["monetary"] <= cap]
    parts = []
    for seg, grp in df.groupby("segment"):
        parts.append(grp.sample(n=min(320, len(grp)), random_state=42))
    sample = pd.concat(parts)
    segs = sorted(sample["segment"].unique())
    colors = {s: MULTI_TOP[i % len(MULTI_TOP)] for i, s in enumerate(segs)}
    sc = Scatter(init_opts=init())
    sc.add_xaxis([0])                    # value 轴，add_xaxis 仅为占位
    for seg in segs:
        grp = sample[sample["segment"] == seg]
        pts = [{"value": [round(float(r), 1), round(float(m), 1)],
                "symbolSize": 7 + min(20, float(f) * 4)}
               for r, m, f in zip(grp["recency_months"], grp["monetary"],
                                  grp["frequency"])]
        sc.add_yaxis(seg, pts,
                     itemstyle_opts=opts.ItemStyleOpts(
                         color=colors[seg], opacity=0.68,
                         border_color=colors[seg], border_width=0.5),
                     label_opts=hidden_label())
    n_important = int((df["segment"].isin(["重要价值客户", "重要保持客户"])).sum())
    insight = (f"抽样 {len(sample):,} 名客户；高价值客户 "
               f"R 小、M 大、气泡更大，重要价值/保持类共 {n_important:,} 人")
    return finish(sc, "RFM 客户价值气泡图", insight,
                  xaxis=val_axis("Recency（月，越小越近期）", min_=0, max_=26,
                                 name_location="middle", name_gap=32),
                  yaxis=val_axis("Monetary（雷亚尔，截尾 99 分位）"),
                  leg=legend(show=True, right="2%", top="12%", vertical=True),
                  tooltip=opts.TooltipOpts(
                      trigger="item",
                      background_color="rgba(16,21,38,0.94)",
                      border_color="#3A4A66",
                      textstyle_opts=opts.TextStyleOpts(color="#E6EBF5", font_size=13),
                      formatter=JsCode(
                          "function(p){return p.seriesName+'<br/>R(月): '+p.value[0]"
                          "+'<br/>M(雷亚尔): '+p.value[1];}")),
                  grid={"left": "10%", "right": "16%", "top": "24%",
                        "bottom": "16%", "containLabel": True},
                  note="*注：数据来源于 Kaggle Olist 公开数据集（CC BY-NC-SA 4.0）；"
                       "按 RFM 八类分层抽样、Monetary 截尾至 99 分位以利展示，气泡大小映射购买频次 F。")


def fig18_rfm_bar(D):
    """B2 RFM 八类客户规模横向渐变条。"""
    df = D["rfm_seg"].sort_values("count", ascending=True)
    segs, vals = list(df["segment"]), [int(v) for v in df["count"]]
    insight = (f"{df['segment'].iloc[-1]} 最多（{vals[-1]:,} 人）；"
               f"一般发展+重要发展两类合计占 {df[df['segment'].str.contains('发展')]['count'].sum()/df['count'].sum()*100:.1f}%")
    bars = [opts.BarItem(name=s, value=v, itemstyle_opts=opts.ItemStyleOpts(
        color=MULTI[i % len(MULTI)], border_radius=[0, 8, 8, 0]))
        for i, (s, v) in enumerate(zip(segs, vals))]
    bar = (Bar(init_opts=init()).add_xaxis(segs)
           .add_yaxis("客户数", bars, bar_width=20,
                      label_opts=label_box("right", FMT_INT, size=15))
           .reversal_axis())
    return finish(bar, "RFM 八类客户规模", insight,
                  val_axis("客户数（人）", name_location="middle", name_gap=32),
                  cat_axis("客户分群"),
                  grid={"left": "16%", "right": "10%", "top": "24%",
                        "bottom": "16%", "containLabel": True},
                  note="*注：数据来源于 Kaggle Olist 公开数据集（CC BY-NC-SA 4.0）；"
                       "RFM 按中位数二值化，F 维采用严格大于中位数以避免八分类塌缩。")


def _cohort_matrix(df, last_month="2018-09"):
    """把同期群表重建为 1..20 连续偏移列：
       观测窗口内的 NaN = 真实 0 留存；窗口外 = None（尚未进入观测期）。
    """
    cohorts = list(df["cohort_month"])
    offsets = list(range(1, 21))
    end = pd.Period(last_month, freq="M")
    data, zmax = [], 0.0
    for yi, co in enumerate(cohorts):
        start = pd.Period(str(co)[:7], freq="M")
        observable = (end.year - start.year) * 12 + (end.month - start.month)
        for xi, off in enumerate(offsets):
            if off > observable:
                continue                              # 尚未观测 → 留空，不画 NaN
            col = str(off)
            v = float(df.loc[yi, col]) if (col in df.columns
                                           and not pd.isna(df.loc[yi, col])) else 0.0
            pct = round(v * 100, 3)
            data.append([xi, yi, pct])
            zmax = max(zmax, pct)
    return cohorts, [str(o) for o in offsets], data, zmax


def fig19_cohort_heatmap(D):
    """B3 同期群留存热力图（已修复 NaN / 全浅黄问题）。"""
    cohorts, cols, data, zmax = _cohort_matrix(D["cohort"])
    df = D["cohort"]
    m1 = df["1"].dropna().mean() * 100 if "1" in df.columns else 0
    insight = (f"首购后第 1 个月平均留存 {m1:.1f}%，此后多数月份仅 0.2%—0.6%；"
               f"复购是平台增长瓶颈")
    hm = (HeatMap(init_opts=init()).add_xaxis(cols)
          .add_yaxis("留存率", cohorts, data,
                     label_opts=opts.LabelOpts(is_show=False)))
    return finish(hm, "同期群留存热力图", insight,
                  xaxis=cat_axis("首购后月数", rotate=0),
                  yaxis=cat_axis(""),   # y 轴名称竖排会与月份刻度挤在一起，改由注脚说明
                  extra=dict(visualmap_opts=opts.VisualMapOpts(
                      min_=0, max_=2.0, orient="horizontal",
                      pos_left="center", pos_bottom="12%",
                      range_color=["#16203A", "#16336B", "#1E90FF", GOLD_C, "#FF4D4F"],
                      textstyle_opts=opts.TextStyleOpts(color=AXIS_TXT, font_size=FS_ANNOTATION))),
                  tooltip=opts.TooltipOpts(
                      trigger="item", background_color="rgba(16,21,38,0.94)",
                      border_color="#3A4A66",
                      textstyle_opts=opts.TextStyleOpts(color="#E6EBF5", font_size=13),
                      formatter=JsCode(
                          "function(p){return p.name+' 群 · 第 '+p.value[0].toString()"
                          "+' 月<br/>留存率: '+p.value[2].toFixed(2)+'%';}")),
                  grid={"left": "10%", "right": "5%", "top": "22%",
                        "bottom": "20%", "containLabel": True},
                  note="*注：数据来源于 Kaggle Olist 公开数据集（CC BY-NC-SA 4.0）；"
                       "行=首购月份、列=首购后月数；空白=该同期群尚未进入观测期（非 0 留存）；"
                       "色标 0—2%，高于 2% 显示最高色。")


def fig20_pareto(D):
    """B4 帕累托图：Top20 品类 GMV 柱 + 累计占比折线 + 80% 参考线。"""
    df = D["pareto"].sort_values("rank").head(20)
    x = [c.replace("_", " ") for c in df["category"]]
    gmv = [round(v / 1e4, 1) for v in df["gmv"]]
    cum = [round(v * 100, 1) for v in df["cum_pct"]]
    n80 = int((df["cum_pct"] <= 0.8).sum()) + 1
    total_n = len(D["pareto"])
    insight = (f"前 {n80} / {total_n} 个品类即贡献 80% 销售额；"
               f"头部品类 {x[0]} 单品占比 {df['gmv'].iloc[0]/D['pareto']['gmv'].sum()*100:.1f}%")
    bar = (Bar(init_opts=init()).add_xaxis(x)
           .add_yaxis("GMV（万雷亚尔）", gmv, bar_width="58%",
                      itemstyle_opts=opts.ItemStyleOpts(
                          color=BLUE, border_radius=RADIUS),
                      label_opts=hidden_label()))
    bar.extend_axis(yaxis=opts.AxisOpts(
        type_="value", name="累计占比（%）", min_=0, max_=100,
        name_textstyle_opts=opts.TextStyleOpts(color=AXIS_TXT,
                                               font_size=FS_AXIS_NAME),
        axislabel_opts=opts.LabelOpts(color=GOLD_C, font_size=FS_ANNOTATION,
                                      formatter="{value}%"),
        axisline_opts=opts.AxisLineOpts(
            linestyle_opts=opts.LineStyleOpts(color=AXIS_LINE)),
        splitline_opts=opts.SplitLineOpts(is_show=False)))
    line = (Line().add_xaxis(x)
            .add_yaxis("累计占比", cum, yaxis_index=1, symbol="circle", symbol_size=7,
                       linestyle_opts=opts.LineStyleOpts(color=GOLD_C, width=3),
                       itemstyle_opts=opts.ItemStyleOpts(color=GOLD_C),
                       label_opts=hidden_label(),
                       markline_opts=opts.MarkLineOpts(
                           data=[opts.MarkLineItem(y=80, name="80% 阈值")],
                           linestyle_opts=opts.LineStyleOpts(
                               color="#FF6B6B", type_="dashed", width=1.5),
                           label_opts=opts.LabelOpts(
                               color="#FF6B6B", font_size=FS_ANNOTATION,
                               position="insideMiddleTop",  # 避开右轴 80% 刻度与首根柱
                               formatter="80% 阈值"))))
    bar.overlap(line)
    return finish(bar, "品类销售额帕累托图（ABC）", insight,
                  cat_axis("商品品类", rotate=35), val_axis("GMV（万雷亚尔）"),
                  leg=legend(show=True),
                  grid={"left": "8%", "right": "7%", "top": "26%",
                        "bottom": "30%", "containLabel": True})


def fig21_forecast(D):
    """B5 时间序列预测：实际 + 预测 + 95% 置信带。"""
    df = D["forecast"]
    hist = df[df["type"] == "actual"]
    fc = df[df["type"] == "forecast"]
    months = list(hist["month"]) + list(fc["month"])
    n = len(hist)
    actual = [round(v / 1e4, 1) for v in hist["value"]] + [None] * len(fc)
    forecast = ([None] * (n - 1) + [round(hist["value"].iloc[-1] / 1e4, 1)]
                + [round(v / 1e4, 1) for v in fc["value"]])
    lower = ([None] * (n - 1) + [round(hist["value"].iloc[-1] / 1e4, 1)]
             + [round(v / 1e4, 1) for v in fc["lower"]])
    width = ([None] * (n - 1) + [0]
             + [round((u - l) / 1e4, 1) for u, l in zip(fc["upper"], fc["lower"])])
    try:
        import json
        with open(os.path.join(TBL_DIR, "analysis_metrics.json"), encoding="utf-8") as f:
            mape = json.load(f)["backtest_mape"]
    except Exception:
        mape = float("nan")
    insight = (f"加性季节分解 + OLS 趋势外推未来 {len(fc)} 个月；"
               f"回测 MAPE≈{mape:.1f}%，旺季（年末）GMV 仍呈上行")
    line = (Line(init_opts=init()).add_xaxis(months)
            .add_yaxis("实际 GMV", actual, is_smooth=False,
                       symbol="circle", symbol_size=5,
                       linestyle_opts=opts.LineStyleOpts(color="#1E90FF", width=3),
                       itemstyle_opts=opts.ItemStyleOpts(color="#1E90FF"),
                       label_opts=hidden_label())
            .add_yaxis("区间下界", lower, symbol="none", stack="ci",
                       linestyle_opts=opts.LineStyleOpts(opacity=0),
                       areastyle_opts=opts.AreaStyleOpts(opacity=0),
                       label_opts=hidden_label())
            .add_yaxis("95% 置信区间", width, symbol="none", stack="ci",
                       linestyle_opts=opts.LineStyleOpts(opacity=0),
                       # AreaStyleOpts 默认 opacity=0，不显式设为 1 会让区间带完全透明
                       areastyle_opts=opts.AreaStyleOpts(
                           opacity=1, color="rgba(255,107,138,0.22)"),
                       label_opts=hidden_label())
            .add_yaxis("预测 GMV", forecast, symbol="circle", symbol_size=7,
                       linestyle_opts=opts.LineStyleOpts(
                           color="#FF6B8A", width=3, type_="dashed"),
                       itemstyle_opts=opts.ItemStyleOpts(color="#FF6B8A"),
                       label_opts=hidden_label()))
    return finish(line, "月度 GMV 预测（含 95% 置信区间）", insight,
                  cat_axis("月份", rotate=42), val_axis("GMV（万雷亚尔）"),
                  leg=legend(show=True, top="17%"),   # 副标题放大后需给标题行让位
                  grid={"left": "8%", "right": "5%", "top": "26%",
                        "bottom": "28%", "containLabel": True},
                  note="*注：数据来源于 Kaggle Olist 公开数据集（CC BY-NC-SA 4.0）；"
                       "短样本（约 20 个完整月）采用季节分解+OLS 外推，阴影为 95% 预测区间。")


def _parse_item(s):
    try:
        v = ast.literal_eval(str(s))
        return v[0] if isinstance(v, (tuple, list)) and v else str(v)
    except Exception:
        return str(s).strip("()' ")


def fig22_association_heatmap(D):
    """B6 关联规则提升度热力图：前项 × 后项 Lift 矩阵。"""
    df = D["rules"].copy()
    df["a"] = df["antecedents"].map(_parse_item)
    df["b"] = df["consequents"].map(_parse_item)
    # 保留全部 14 个品类，确保 16 条规则全部落进矩阵（原先截断到 10 个会丢规则）
    names = sorted(set(df["a"]) | set(df["b"]))
    lut = {(a, b): float(l) for a, b, l in zip(df["a"], df["b"], df["lift"])}
    data = [[xi, yi, round(lut[(a, b)], 2)]
            for yi, b in enumerate(names) for xi, a in enumerate(names)
            if (a, b) in lut]
    best = df.loc[df["lift"].idxmax()]
    insight = (f"{_parse_item(best['antecedents'])} → {_parse_item(best['consequents'])} "
               f"提升度最高（Lift={best['lift']:.2f}），家居/寝具互补性最强")
    labels = [n.replace("_", " ") for n in names]
    hm = (HeatMap(init_opts=init()).add_xaxis(labels)
          .add_yaxis("Lift", labels, data,
                     label_opts=opts.LabelOpts(
                         is_show=True, color=WHITE, font_size=FS_HEAT_VALUE,
                         formatter=JsCode("function(p){return p.value[2].toFixed(2);}"))))
    return finish(hm, "关联规则提升度热力图", insight,
                  xaxis=cat_axis("前项品类", rotate=38),
                  yaxis=cat_axis(""),
                  extra=dict(visualmap_opts=opts.VisualMapOpts(
                      min_=1, max_=float(df["lift"].max()),
                      orient="horizontal", pos_left="center", pos_bottom="12%",
                      range_color=["#16203A", "#16336B", "#1E90FF", GOLD_C, "#FF4D4F"],
                      textstyle_opts=opts.TextStyleOpts(color=AXIS_TXT, font_size=FS_ANNOTATION))),
                  tooltip=opts.TooltipOpts(
                      trigger="item", background_color="rgba(16,21,38,0.94)",
                      border_color="#3A4A66",
                      textstyle_opts=opts.TextStyleOpts(color="#E6EBF5", font_size=13),
                      formatter=JsCode(
                          "function(p){return p.value[1]+' → '+p.value[0]"
                          "+'<br/>Lift: '+p.value[2].toFixed(2);}")),
                  grid={"left": "18%", "right": "6%", "top": "24%",
                        "bottom": "34%", "containLabel": True},
                  note="*注：数据来源于 Kaggle Olist 公开数据集（CC BY-NC-SA 4.0）；"
                       "列=规则前项、行=规则后项；空白=该品类对未产生满足支持度/置信度阈值的规则（非 Lift=0）。")


# ==========================================================================
# 主流程：22 张图全部输出 HTML
# ==========================================================================
BUILDERS = [
    ("fig01_gmv_by_state",           fig01_gmv_by_state),
    ("fig02_sales_by_category_mean", fig02_mean_bar),
    ("fig03_top_category_bar",       fig03_top_category_bar),
    ("fig04_monthly_orders_labeled", fig04_monthly_orders_labeled),
    ("fig05_stacked_quarter",        fig05_stacked_quarter),
    ("fig06_butterfly_state",        fig06_butterfly),
    ("fig07_monthly_gmv_line",       fig07_monthly_gmv_line),
    ("fig08_compare_line",           fig08_compare_line),
    ("fig09_donut_completion",       fig09_donut),
    ("fig10_waterball_satisfaction", fig10_waterball),
    ("fig11_nightingale_state",      fig11_nightingale),
    ("fig12_gauge_fulfillment",      fig12_gauge),
    ("fig13_bar_line_gmv_yoy",       fig13_bar_line_yoy),
    ("fig14_bullet_category",        fig14_bullet),
    ("fig15_lollipop_fulfillment",   fig15_lollipop),
    ("fig16_jade_score",             fig16_jade),
    ("fig17_rfm_bubble",            fig17_rfm_bubble),
    ("fig18_rfm_bar",               fig18_rfm_bar),
    ("fig19_cohort_heatmap",        fig19_cohort_heatmap),
    ("fig20_pareto",                fig20_pareto),
    ("fig21_forecast",              fig21_forecast),
    ("fig22_association_heatmap",   fig22_association_heatmap),
]


def main():
    D = load()
    ok, fail = [], []
    for name, builder in BUILDERS:
        try:
            chart = builder(D)
            render(chart, name, liquid=(name == "fig10_waterball_satisfaction"))
            ok.append(name)
        except Exception as exc:
            fail.append((name, f"{type(exc).__name__}: {exc}"))
            print("[FAIL]", name, type(exc).__name__, exc)
    print(f"\n=== 已生成 {len(ok)} / {len(BUILDERS)} 张自包含 HTML -> {FIG_DIR} ===")
    if fail:
        print("失败清单：")
        for n, e in fail:
            print("  -", n, e)
    print("下一步： D:/anaconda/python.exe scripts/06_export_png.py  （批量截成同名高清 PNG）")


if __name__ == "__main__":
    main()
