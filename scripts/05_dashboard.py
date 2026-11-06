# -*- coding: utf-8 -*-
"""
05_dashboard.py —— Olist 巴西电商销售数据驾驶舱（浅色商务极简风 · 时间轴动画版）
==================================================================================
技术栈：Streamlit（布局 / 时间轴 / 播放） + Plotly（全部图表），纯 Python，无 BI 工具。

【本版新增】
1. 顶部改为「横向月份时间轴（select_slider） + ▶ 播放 / ⏸ 暂停 / ⏭ 单步 / ⟲ 重置 / 速度」，
   时间轴按 2016-10 → 2018-08 逐月推进，数据窗口为「起始月 → 当前游标月」的累计口径，
   游标每前进一步，KPI、速读、5 张图全部重算，实现「时间推进、数据生长」。
2. 播放定时器默认使用手写 time.sleep + st.rerun()（服务端强制逐帧刷新，
   不依赖任何第三方库、不受浏览器 iframe 定时器节流影响，实测可稳定逐月推进）；
   若已安装 streamlit-autorefresh，可把 PREFER_FRONTEND_TIMER 改为 True 切换为
   前端定时（更顺滑），未安装时会自动回退到手写定时器。
3. Session State 规范化：所有 widget key 在页面初始化时用 st.session_state.setdefault()
   统一声明；程序化推进游标只在 widget 实例化「之前」写 state；用户交互只走 on_change /
   on_click 回调；不再存在 st.date_input 与 Session State 冲突导致的黄色警告框。
4. 图表动效：polish() 统一注入 layout.transition（平滑过渡）；趋势图额外构造
   Plotly frames + animation_opts(frame.duration / transition.duration)，可点图内
   「▶ 生长」独立播放逐月生长动画；卡片与图表容器带轻量淡入动画。

视觉规范：页面 #F4F6F9、纯白卡片 + 微弱阴影 + 8px 圆角、主色 Teal #00A896、
辅助柔和蓝 #4299E1 / 红 #E53E3E / 黄 #F6C445，深灰文字 #2D3748；
Plotly 统一 template='plotly_white'、白底、只保留水平浅灰虚线网格、
底部 X 与左侧 Y 极细灰线 #E2E8F0、白色带边框的 hover 小方框、height≈350。

数据：只读 data/clean/ 下已经清洗好的 CSV（clean_order_agg.csv、
clean_order_items.csv、clean_customers_rfm.csv），并对文件缺失、编码异常、
列名缺失、日期解析失败、数值脏数据、空筛选区间等做逐层容错；
outputs/tables/cohort_retention.csv 仅作为同期群数据不可用时的兜底。

运行（零新增依赖，直接可跑）：
  D:/anaconda/python.exe -m streamlit run scripts/05_dashboard.py --server.port 8501
  # 浏览器打开 http://localhost:8501 → 点时间轴右侧「▶ 播放」
  # 可选：D:/anaconda/python.exe -m pip install streamlit-autorefresh
  #       装好后把 PREFER_FRONTEND_TIMER 改为 True 可用前端定时器

兼容 run_all.py 的静态导出（浅色风、单文件自包含、图内仍可播放生长动画）：
  D:/anaconda/python.exe scripts/05_dashboard.py --html
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from functools import lru_cache
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

try:                                             # 可选依赖：前端定时器
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except Exception:                                # 缺库时自动回退到手写定时器
    HAS_AUTOREFRESH = False

# 默认 False：服务端手写定时器逐帧强制刷新，任何浏览器 / 无头环境都能稳定播放。
# 改为 True 且已安装 streamlit-autorefresh 时，改用前端定时器（不阻塞服务端线程）。
PREFER_FRONTEND_TIMER = False

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
TABLES = ROOT / "outputs" / "tables"
OUT_HTML = ROOT / "index.html"

# ----------------------------- 配色与常量 -----------------------------
BG, CARD, INK, MUTED, LINE = "#F4F6F9", "#FFFFFF", "#2D3748", "#718096", "#E2E8F0"
TEAL, TEAL_LIGHT, BLUE = "#00A896", "#A8E6DF", "#4299E1"
RED, YELLOW, GREY = "#E53E3E", "#F6C445", "#CBD5E0"
GREEN_SCALE = [[0, "#EAF7F1"], [0.35, "#A8E6CF"], [0.7, "#48B99C"], [1, "#007F72"]]
H = 350
CHART_CFG = {"displayModeBar": False, "responsive": True}
ANIM_MS = 420                                    # Plotly 数据过渡时长

BASE_CSS = """
<style>
:root{--bg:#F4F6F9;--card:#FFFFFF;--ink:#2D3748;--muted:#718096;--line:#E2E8F0;--teal:#00A896;}
*{box-sizing:border-box;}
.dash-card{background:#FFFFFF;border:1px solid #EDF0F5;border-radius:8px;
  box-shadow:0 2px 8px rgba(16,24,40,.05);}
.kpi-card{padding:14px 16px 12px;min-height:104px;}
.kpi-name{font-size:12px;color:#718096;letter-spacing:.4px;font-weight:600;}
.kpi-value{font-size:27px;font-weight:700;color:#2D3748;line-height:1.25;margin-top:6px;white-space:nowrap;}
.kpi-unit{font-size:12px;color:#A0AEC0;font-weight:500;margin-left:5px;}
.kpi-tag{display:inline-block;font-size:11px;padding:2px 7px;border-radius:4px;margin-top:7px;font-weight:600;}
.up{color:#0B8F6E;background:#E6F7F2;}
.down{color:#E53E3E;background:#FDECEC;}
.flat{color:#718096;background:#F1F4F8;}
.brief-card{border-left:4px solid #00A896;padding:13px 18px;font-size:13.5px;
  color:#4A5568;line-height:1.9;}
.brief-card .hl{color:#00A896;font-weight:700;}
.brief-tag{display:inline-block;background:#E6F7F2;color:#0B8F6E;font-size:11px;
  font-weight:700;padding:2px 8px;border-radius:4px;margin-right:10px;}
.head-title{font-size:25px;font-weight:750;color:#2D3748;letter-spacing:.5px;line-height:1.25;}
.head-sub{font-size:12px;color:#A0AEC0;margin-top:6px;}
.teal-rule{height:3px;background:linear-gradient(90deg,#00A896 0%,#7FD8CE 62%,#E2E8F0 62%);
  border-radius:2px;margin:10px 0 4px;}
.foot-note{font-size:11px;color:#A0AEC0;line-height:1.8;margin-top:6px;}
/* ---- 时间轴卡片 ---- */
.tl-head{display:flex;align-items:center;gap:14px;flex-wrap:wrap;font-size:12px;color:#718096;}
.tl-label{font-size:11px;font-weight:700;letter-spacing:.6px;color:#A0AEC0;}
.tl-current{font-size:16px;font-weight:750;color:#00A896;}
.tl-progress{font-size:11px;color:#A0AEC0;}
.tl-bar{flex:1;min-width:120px;height:5px;background:#EDF2F5;border-radius:3px;overflow:hidden;}
.tl-bar i{display:block;height:100%;background:linear-gradient(90deg,#7FD8CE,#00A896);
  border-radius:3px;transition:width .38s cubic-bezier(.4,0,.2,1);}
.tl-state{font-size:11px;font-weight:700;color:#A0AEC0;white-space:nowrap;}
.tl-state.on{color:#00A896;}
/* ---- 轻量生长动画 ---- */
@keyframes cardGrow{0%{opacity:.42;transform:translateY(7px)}100%{opacity:1;transform:translateY(0)}}
.kpi-card,.brief-card,.tl-head{animation:cardGrow .34s ease-out both;}
</style>
"""

ST_CSS = BASE_CSS + """
<style>
html,body,[data-testid="stAppViewContainer"],.main,[data-testid="stApp"]{background-color:#F4F6F9 !important;}
[data-testid="stHeader"]{background:transparent !important;}
[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none;}
.block-container{padding-top:1.2rem;padding-bottom:2.2rem;max-width:1560px;}
[data-testid="stPlotlyChart"]{background:#FFFFFF !important;border:1px solid #EDF0F5;
  border-radius:8px;box-shadow:0 2px 8px rgba(16,24,40,.05);padding:6px 8px 2px;
  animation:cardGrow .4s ease-out both;}
/* 时间轴外层白卡：本页唯一的 border 容器 */
div[data-testid="stVerticalBlockBorderWrapper"]{background:#FFFFFF !important;
  border:1px solid #EDF0F5 !important;border-radius:8px !important;
  box-shadow:0 2px 8px rgba(16,24,40,.05) !important;
  padding:12px 18px 6px !important;margin:12px 0 12px;}
[data-testid="stSelectSlider"]{padding:4px 2px 0;}
[data-testid="stSelectSlider"] div[role="slider"]{background:#00A896 !important;
  box-shadow:0 0 0 4px rgba(0,168,150,.14) !important;}
div[data-testid="stButton"] > button{background:#FFFFFF;color:#00A896;border:1px solid #B8E6DF;
  border-radius:6px;font-weight:600;box-shadow:0 1px 4px rgba(16,24,40,.04);
  transition:all .18s ease;}
div[data-testid="stButton"] > button:hover{background:#E6F7F2;border-color:#00A896;
  transform:translateY(-1px);}
div[data-testid="stButton"] > button:active{transform:translateY(0);}
</style>
"""

STATIC_CSS = BASE_CSS + """
<style>
html,body{margin:0;background:#F4F6F9;color:#2D3748;
  font-family:"Microsoft YaHei","Segoe UI",Arial,sans-serif;}
.wrap{max-width:1560px;margin:0 auto;padding:20px 26px 34px;}
.head-row{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;}
.range-pill{background:#FFFFFF;border:1px solid #EDF0F5;border-radius:8px;padding:9px 16px;
  font-size:12px;color:#718096;box-shadow:0 2px 8px rgba(16,24,40,.05);}
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:14px;}
.brief{margin-top:12px;}
.grid-top{display:grid;grid-template-columns:2fr 1fr;gap:12px;margin-top:12px;}
.grid-bottom{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:12px;}
.chart{background:#FFFFFF;border:1px solid #EDF0F5;border-radius:8px;
  box-shadow:0 2px 8px rgba(16,24,40,.05);padding:6px 8px 2px;min-width:0;
  animation:cardGrow .4s ease-out both;}
.tl-static{margin-top:12px;padding:12px 18px;}
@media(max-width:1100px){.grid-top,.grid-bottom{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(2,1fr)}}
</style>
"""


# =====================================================================
# 1. 数据读取与清洗容错
# =====================================================================
def _read(fname: str, folder: Path = CLEAN) -> tuple[pd.DataFrame, list[str]]:
    """读 CSV：文件不存在 / UTF-8 失败 / GBK 失败 均有兜底，返回 (df, 问题清单)。"""
    path = folder / fname
    if not path.exists():
        return pd.DataFrame(), [f"缺少文件：{path}"]
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            df = pd.read_csv(path, low_memory=False, encoding=enc)
            df.columns = [str(c).strip() for c in df.columns]
            return df, []
        except UnicodeDecodeError:
            continue
        except Exception as exc:
            return pd.DataFrame(), [f"读取失败 {fname}：{exc}"]
    return pd.DataFrame(), [f"编码无法识别：{fname}"]


def _col(df: pd.DataFrame, *names: str) -> str | None:
    for n in names:
        if n in df.columns:
            return n
    return None


def _num(s) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def _ensure(df: pd.DataFrame, col: str, value) -> pd.DataFrame:
    if col not in df.columns:
        df[col] = value
    return df


def _add_month(df: pd.DataFrame, issues: list[str]) -> tuple[pd.DataFrame, bool]:
    """统一生成 _month(YYYY-MM) 与 _date。存在精确购买时间戳则按天筛选，否则按月筛选。"""
    if df.empty:
        _ensure(df, "_month", "")
        _ensure(df, "_date", pd.NaT)
        return df, False
    exact = _col(df, "order_purchase_timestamp", "purchase_timestamp", "order_purchase_date")
    month = _col(df, "purchase_month", "order_purchase_month")
    if exact:
        d = pd.to_datetime(df[exact], errors="coerce")
        df["_date"] = d
        df["_month"] = d.dt.to_period("M").astype(str).where(d.notna(), "")
        day_mode = True
    elif month:
        df["_month"] = df[month].astype(str).str[:7]
        df["_date"] = pd.to_datetime(df["_month"] + "-01", errors="coerce")
        day_mode = False
    else:
        df["_month"], df["_date"], day_mode = "", pd.NaT, False
        issues.append("缺少 purchase_month / 购买时间戳，时间筛选退化为不过滤")
    bad = df["_month"].eq("") | df["_month"].eq("NaT") | df["_month"].eq("nan")
    if bad.any():
        df = df.loc[~bad].copy()
    return df, day_mode


def _orders_from_items(items: pd.DataFrame) -> pd.DataFrame:
    """订单聚合表缺失时，用订单明细重建一份最小可用的订单表。"""
    g = items.groupby("order_id", as_index=False).agg(
        gmv=("price", "sum"), freight=("freight_value", "sum"))
    for c in ("customer_unique_id", "customer_state", "purchase_month", "order_status"):
        if c in items.columns:
            g[c] = items.groupby("order_id")[c].first().values
    return g


def load_all() -> dict:
    """返回 {orders, items, rfm, day_mode, months, issues}。全部来自 data/clean/。"""
    orders, i1 = _read("clean_order_agg.csv")
    items, i2 = _read("clean_order_items.csv")
    rfm, i3 = _read("clean_customers_rfm.csv")
    issues = i1 + i2 + i3

    if orders.empty and not items.empty:
        orders = _orders_from_items(items)
        issues.append("clean_order_agg.csv 不可用，已由订单明细重建订单聚合表")

    # --- 订单表字段兜底 ---
    if not orders.empty:
        if _col(orders, "order_id") is None:
            orders["order_id"] = np.arange(len(orders)).astype(str)
        _ensure(orders, "customer_unique_id", orders.get("customer_id", orders["order_id"]))
        _ensure(orders, "customer_state", "未知")
        _ensure(orders, "order_status", "")
        if _col(orders, "gmv") is None:
            alt = _col(orders, "order_payment_value", "payment_value")
            orders["gmv"] = _num(orders[alt]) if alt else 0.0
        _ensure(orders, "freight", 0.0)
        _ensure(orders, "review_score", np.nan)
        orders["gmv"] = _num(orders["gmv"])
        orders["freight"] = _num(orders["freight"])
        orders["review_score"] = pd.to_numeric(orders["review_score"], errors="coerce")
        orders["customer_state"] = orders["customer_state"].fillna("未知").astype(str)
        orders["order_status"] = orders["order_status"].fillna("").astype(str)
        orders, day_mode = _add_month(orders, issues)
    else:
        day_mode = False
        issues.append("订单数据为空，无法构建驾驶舱")

    # --- 明细表字段兜底 ---
    if not items.empty:
        for c, v in (("price", 0.0), ("freight_value", 0.0),
                     ("product_category_name_english", "unknown"),
                     ("customer_unique_id", ""), ("purchase_month", "")):
            _ensure(items, c, v)
        items["price"] = _num(items["price"])
        items["freight_value"] = _num(items["freight_value"])
        items["product_category_name_english"] = (
            items["product_category_name_english"].fillna("unknown").astype(str))
        items, _ = _add_month(items, issues)
    else:
        issues.append("clean_order_items.csv 不可用，品类结构图将显示占位提示")

    # --- 剔除不完整月份（如 2018-09 仅 1 单、2016 起步期个位数订单）---
    # 与论文 04_visuals.py 口径一致，避免趋势图上出现「假断崖」。
    if not orders.empty and "_month" in orders.columns:
        cnt = orders.groupby("_month")["order_id"].nunique()
        keep = set(cnt[cnt >= 50].index)
        dropped = sorted(set(cnt.index) - keep)
        if dropped and keep:
            orders = orders[orders["_month"].isin(keep)].copy()
            if not items.empty and "_month" in items.columns:
                items = items[items["_month"].isin(keep)].copy()
            issues.append("已剔除订单数不足 50 单的不完整月份：" + "、".join(dropped))

    if not rfm.empty and "cohort_month" in rfm.columns:
        rfm["cohort_month"] = rfm["cohort_month"].astype(str).str[:7]

    months = (sorted(m for m in orders["_month"].unique() if len(str(m)) == 7)
              if not orders.empty and "_month" in orders.columns else [])
    return {"orders": orders, "items": items, "rfm": rfm,
            "day_mode": day_mode, "months": months, "issues": issues}


@lru_cache(maxsize=1)
def load_all_cached() -> dict:
    """纯 Python 缓存：播放时每帧 rerun 都命中，避免重复读 10 万行 CSV。"""
    return load_all()


# =====================================================================
# 2. 时间轴切片、KPI 与业务速读
# =====================================================================
def slice_by_dates(df: pd.DataFrame, start: dt.date, end: dt.date,
                   day_mode: bool = False) -> pd.DataFrame:
    if df.empty or "_month" not in df.columns:
        return df
    s, e = start.strftime("%Y-%m"), end.strftime("%Y-%m")
    if s > e:
        s, e = e, s
    if day_mode and "_date" in df.columns and df["_date"].notna().any():
        mask = df["_date"].between(pd.Timestamp(start),
                                   pd.Timestamp(end) + pd.Timedelta(days=1)
                                   - pd.Timedelta(seconds=1))
    else:
        mask = df["_month"].between(s, e)
    return df.loc[mask].copy()


def slice_month(df: pd.DataFrame, month: str) -> pd.DataFrame:
    if df.empty or "_month" not in df.columns:
        return df
    return df.loc[df["_month"] == month].copy()


def date_bounds(data: dict) -> tuple[dt.date, dt.date]:
    months = data.get("months") or []
    if not months:
        return dt.date(2017, 1, 1), dt.date(2018, 9, 30)
    lo = pd.Timestamp(months[0] + "-01").date()
    hi = (pd.Timestamp(months[-1] + "-01") + pd.offsets.MonthEnd(1)).date()
    return lo, hi


def month_end(month: str) -> dt.date:
    """'2018-03' → 2018-03-31（时间轴游标对应的累计窗口右端点）。"""
    try:
        return (pd.Timestamp(str(month)[:7] + "-01") + pd.offsets.MonthEnd(1)).date()
    except Exception:
        return dt.date.today()


def month_delta(data: dict, end_month: str, fn, kind: str):
    """播放态专用：标签用「本月相对上月」的月环比，随时间轴逐月跳动。"""
    months = data.get("months") or []
    if end_month not in months:
        return None, "—"
    i = months.index(end_month)
    if i == 0:
        return None, "—"
    orders = data["orders"]
    cur = fn(slice_month(orders, end_month))
    prev = fn(slice_month(orders, months[i - 1]))
    if (cur is None or prev is None or (isinstance(cur, float) and np.isnan(cur))
            or (isinstance(prev, float) and (np.isnan(prev) or prev == 0))):
        return None, "—"
    if kind == "pct":
        return (cur - prev) / abs(prev) * 100, "月环比"
    return cur - prev, "月环比"


KPI_DEFS = [
    ("总 GMV", lambda f: f["gmv"].sum() / 1e4, "万雷亚尔", "{:,.1f}", "pct"),
    ("订单数", lambda f: f["order_id"].nunique(), "单", "{:,.0f}", "pct"),
    ("客户数", lambda f: f["customer_unique_id"].nunique(), "人", "{:,.0f}", "pct"),
    ("平均评分", lambda f: f["review_score"].mean(), "分", "{:.2f}", "abs"),
    ("交付率", lambda f: f["order_status"].eq("delivered").mean() * 100, "%", "{:.1f}", "pp"),
]


def kpi_cards(data: dict, start: dt.date, end: dt.date) -> tuple[list[str], dict]:
    """大数字＝起始月至游标月的累计值；角标＝游标月对上月的月环比。"""
    f = slice_by_dates(data["orders"], start, end, data["day_mode"])
    end_month = end.strftime("%Y-%m")
    cards, vals = [], {}
    for name, fn, unit, fmt, kind in KPI_DEFS:
        cur = fn(f) if not f.empty else 0
        cur = 0 if cur is None or (isinstance(cur, float) and np.isnan(cur)) else cur
        vals[name] = cur
        delta, label = month_delta(data, end_month, fn, kind)
        if delta is None:
            cls, tag = "flat", "— 无可比月份"
        else:
            cls = "up" if delta > 0 else ("down" if delta < 0 else "flat")
            suffix = "%" if kind == "pct" else (" 分" if kind == "abs" else " pp")
            digits = 1 if kind != "abs" else 2
            tag = f"{label} {delta:+.{digits}f}{suffix}"
        cards.append(
            f'<div class="dash-card kpi-card"><div class="kpi-name">{name}</div>'
            f'<div class="kpi-value">{fmt.format(cur)}<span class="kpi-unit">{unit}</span></div>'
            f'<span class="kpi-tag {cls}">{tag}</span></div>')
    return cards, vals


def brief_card(data: dict, f: pd.DataFrame, f_items: pd.DataFrame,
               vals: dict, cohort_m1: float, start: dt.date, end: dt.date) -> str:
    state = f.groupby("customer_state")["gmv"].sum() if not f.empty else pd.Series(dtype=float)
    top_state = state.idxmax() if not state.empty else "—"
    top_share = state.max() / state.sum() * 100 if not state.empty and state.sum() else 0
    cat = (f_items.groupby("product_category_name_english")["price"].sum()
           if not f_items.empty else pd.Series(dtype=float))
    top_cat = str(cat.idxmax()).replace("_", " ") if not cat.empty else "—"
    cat_share = cat.max() / cat.sum() * 100 if not cat.empty and cat.sum() else 0
    n_cat = int((cat > 0).sum())
    cur_m = end.strftime("%Y-%m")
    this_m = slice_month(f, cur_m)
    new_gmv = this_m["gmv"].sum() / 1e4 if not this_m.empty else 0.0
    new_orders = this_m["order_id"].nunique() if not this_m.empty else 0
    return (
        f'<div class="dash-card brief-card"><span class="brief-tag">'
        f'截至 {cur_m} 累计速读</span>'
        f'累计 GMV <span class="hl">{vals["总 GMV"]:,.1f} 万雷亚尔</span>，'
        f'成交 <span class="hl">{vals["订单数"]:,.0f} 单</span>、'
        f'覆盖 <span class="hl">{vals["客户数"]:,.0f} 位客户</span>，'
        f'交付率 <span class="hl">{vals["交付率"]:.1f}%</span>、平均评分 '
        f'<span class="hl">{vals["平均评分"]:.2f} 分</span>；'
        f'其中当月新增 <span class="hl">{new_gmv:,.1f} 万雷亚尔 / '
        f'{new_orders:,.0f} 单</span>。'
        f'区域上 <span class="hl">{top_state} 州贡献 {top_share:.1f}%</span>，'
        f'品类上 <span class="hl">{top_cat} 占 {cat_share:.1f}%</span>（{n_cat} 个在售品类），'
        f'主力首购群次月留存均值仅 <span class="hl">{cohort_m1:.1f}%</span>——'
        f'增长仍由新客与头部品类驱动，建议同步推进高价值客户召回与互补品类推荐。</div>')


# =====================================================================
# 3. Plotly 统一样式与 5 张图表（含动态生长）
# =====================================================================
def polish(fig: go.Figure, title: str, *, height: int = H, x_title: str = "",
           y_title: str = "", secondary: bool = False, legend: bool = True) -> go.Figure:
    fig.update_layout(
        template="plotly_white", paper_bgcolor=CARD, plot_bgcolor=CARD, height=height,
        margin=dict(l=10, r=10, t=58, b=10),
        font=dict(family="Microsoft YaHei, Segoe UI, Arial, sans-serif", size=11, color=INK),
        title=dict(text=title, x=0.02, y=0.97, xanchor="left",
                   font=dict(size=14, color=INK)),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=LINE, align="left",
                        font=dict(family="Microsoft YaHei, Arial", size=12, color=INK)),
        legend=(dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                     bgcolor="rgba(0,0,0,0)", font=dict(size=10, color=MUTED),
                     itemwidth=30) if legend else dict(visible=False)),
        # Plotly.react 更新数据时的平滑过渡（柱状/折线逐月生长不生硬切换）
        transition=dict(duration=ANIM_MS, easing="cubic-in-out"),
        bargap=0.35, hovermode="closest",
    )
    fig.update_xaxes(showline=True, linewidth=1, linecolor=LINE, mirror=False,
                     showgrid=False, zeroline=False, tickfont=dict(size=10, color=MUTED),
                     title=dict(text=x_title, font=dict(size=10, color=MUTED)) if x_title else None,
                     showspikes=False)
    fig.update_yaxes(showline=True, linewidth=1, linecolor=LINE, mirror=False,
                     showgrid=True, gridcolor=LINE, gridwidth=1, griddash="dash",
                     zeroline=False, tickfont=dict(size=10, color=MUTED),
                     title=dict(text=y_title, font=dict(size=10, color=MUTED)) if y_title else None,
                     showspikes=False)
    if secondary:
        fig.update_yaxes(showgrid=False, showline=True, linewidth=1, linecolor=LINE,
                         tickfont=dict(size=10, color=MUTED), secondary_y=True,
                         title=dict(text="订单量（单）", font=dict(size=10, color=MUTED)))
    return fig


def fig_trend(f: pd.DataFrame, with_frames: bool = True) -> go.Figure:
    """上左：月度 GMV 柱（浅青） + 订单量折线（黄色带圆点），双轴。

    with_frames=True 时构造逐月 frames（等价于 plotly.express 的 animation_frame），
    并在图内提供「▶ 生长 / ⏸」按钮：frame.duration 控制每帧时长，
    transition.duration 控制柱线生长的补间动画。
    """
    if f.empty or "_month" not in f.columns:
        return polish(go.Figure(), "月度 GMV 与订单量趋势", secondary=True)
    g = f.groupby("_month").agg(gmv=("gmv", "sum"), orders=("order_id", "nunique")).sort_index()
    x = list(g.index)
    gmv = (g["gmv"] / 1e4).round(1).values
    orders = g["orders"].values
    sg, so = gmv.sum() or 1, orders.sum() or 1
    cg = np.round(gmv / sg * 100, 1)
    co = np.round(orders / so * 100, 1)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=x, y=gmv, name="GMV（万雷亚尔）", marker=dict(color=TEAL_LIGHT, line=dict(width=0)),
        customdata=cg,
        hovertemplate="<b>%{x}</b><br>GMV：%{y:,.1f} 万雷亚尔<br>占本期：%{customdata:.1f}%<extra></extra>"),
        secondary_y=False)
    fig.add_trace(go.Scatter(
        x=x, y=orders, name="订单量（单）", mode="lines+markers",
        line=dict(color=YELLOW, width=3),
        marker=dict(color=YELLOW, size=8, line=dict(color="#FFFFFF", width=1.5)),
        customdata=co,
        hovertemplate="<b>%{x}</b><br>订单量：%{y:,.0f} 单<br>占本期：%{customdata:.1f}%<extra></extra>"),
        secondary_y=True)
    out = polish(fig, "月度 GMV 与订单量趋势", y_title="GMV（万雷亚尔）", secondary=True)
    out.update_xaxes(type="category", tickangle=-30, nticks=12)  # 防止 YYYY-MM 被识别成英文月份

    if with_frames and len(x) >= 2:
        # 每一帧＝「只显示到第 k 个月」，帧名即已生长的月数
        frames = [go.Frame(
            name=f"M{k}", traces=[0, 1],
            data=[go.Bar(x=x[:k], y=gmv[:k], customdata=cg[:k]),
                  go.Scatter(x=x[:k], y=orders[:k], customdata=co[:k])])
            for k in range(1, len(x) + 1)]
        out.frames = frames
        out.update_layout(
            margin=dict(l=10, r=10, t=72, b=10),
            updatemenus=[dict(
                type="buttons", direction="left", showactive=False,
                x=0.015, y=1.19, xanchor="left", yanchor="top",
                bgcolor="#FFFFFF", bordercolor=LINE, borderwidth=1, pad=dict(l=5, r=5, t=2, b=2),
                font=dict(size=10, color=TEAL),
                buttons=[
                    dict(label="▶ 生长", method="animate",
                         # frame_duration / transition 均在此生效
                         args=[None, dict(fromcurrent=True, mode="immediate",
                                          frame=dict(duration=340, redraw=False),
                                          transition=dict(duration=340,
                                                          easing="cubic-in-out"))]),
                    dict(label="⏸", method="animate",
                         args=[[None], dict(mode="immediate",
                                            frame=dict(duration=0, redraw=False),
                                            transition=dict(duration=0))]),
                ])])
    return out


def _top_colors(names: list[str], ranked_desc: list[str], n: int = 3) -> list[str]:
    top = set(ranked_desc[:n])
    return [TEAL if s in top else GREY for s in names]


def fig_state_gmv(f: pd.DataFrame, topn: int = 10) -> go.Figure:
    """上右：各州 GMV 水平条形图（降序，前 3 名 Teal）。"""
    if f.empty or "customer_state" not in f.columns:
        return polish(go.Figure(), "各州 GMV 对比", legend=False)
    g = f.groupby("customer_state")["gmv"].sum().sort_values(ascending=False)
    desc = list(g.index)
    g = g.head(topn).sort_values()               # 水平条：最大值在最上方
    names, vals = list(g.index), (g.values / 1e4).round(1)
    total = g.sum() or 1
    fig = go.Figure(go.Bar(
        x=vals, y=names, orientation="h",
        marker=dict(color=_top_colors(names, desc), line=dict(width=0)),
        customdata=np.round(g.values / total * 100, 1),
        text=[f"{v:,.1f}" for v in vals], textposition="outside",
        textfont=dict(size=9, color=MUTED), cliponaxis=False,
        hovertemplate="<b>%{y} 州</b><br>GMV：%{x:,.1f} 万雷亚尔"
                      "<br>占 Top 州合计：%{customdata:.1f}%<extra></extra>"))
    if len(vals):
        fig.update_xaxes(range=[0, float(np.max(vals)) * 1.18])
    return polish(fig, "各州 GMV 对比", x_title="万雷亚尔", legend=False)


def fig_category_structure(f_items: pd.DataFrame, topn: int = 8) -> go.Figure:
    """下左：各品类 GMV 结构（横向堆叠：商品金额 + 运费）。"""
    if f_items.empty or "product_category_name_english" not in f_items.columns:
        return polish(go.Figure(), "各品类 GMV 结构")
    g = (f_items.groupby("product_category_name_english")
         .agg(price=("price", "sum"), freight=("freight_value", "sum")))
    g["total"] = g["price"] + g["freight"]
    g = g[g["total"] > 0].sort_values("total").tail(topn)
    names = [str(i).replace("_", " ") for i in g.index]
    price, freight = (g["price"] / 1e4).round(1).values, (g["freight"] / 1e4).round(1).values
    total = (g["total"] / 1e4).values
    safe = np.where(total == 0, 1, total)
    p_pct, f_pct = np.round(price / safe * 100, 1), np.round(freight / safe * 100, 1)
    fig = go.Figure()
    for vals, pct, nm, color in ((price, p_pct, "商品金额", TEAL),
                                 (freight, f_pct, "运费", BLUE)):
        fig.add_trace(go.Bar(
            y=names, x=vals, orientation="h", name=nm,
            marker=dict(color=color, line=dict(width=0)), customdata=pct,
            hovertemplate="<b>%{y}</b><br>" + nm + "：%{x:,.1f} 万雷亚尔"
                          "<br>占该品类：%{customdata:.1f}%<extra></extra>"))
    fig.update_layout(barmode="stack")
    return polish(fig, "各品类 GMV 结构", x_title="万雷亚尔")


def cohort_matrix(data: dict, f: pd.DataFrame, start: dt.date, end: dt.date,
                  max_cohorts: int = 16, max_offset: int = 12):
    """按筛选结果实时重算留存：首购月取自全量客户，复购只统计筛选期内订单。"""
    orders, rfm = data["orders"], data["rfm"]
    if orders.empty or f.empty or "customer_unique_id" not in f.columns:
        return None
    if not rfm.empty and {"customer_unique_id", "cohort_month"}.issubset(rfm.columns):
        base = rfm.set_index("customer_unique_id")["cohort_month"].astype(str).str[:7]
    else:
        base = orders.groupby("customer_unique_id")["_month"].min()
    base = base[base.str.len() == 7]
    sizes = base.value_counts()
    d = f[["customer_unique_id", "_month"]].dropna().copy()
    d["cohort"] = d["customer_unique_id"].map(base)
    d = d[d["cohort"].notna() & (d["cohort"].str.len() == 7) & (d["_month"].str.len() == 7)]
    if d.empty:
        return None
    ym = d["_month"].str[:4].astype(int) * 12 + d["_month"].str[5:7].astype(int)
    yc = d["cohort"].str[:4].astype(int) * 12 + d["cohort"].str[5:7].astype(int)
    d["offset"] = ym - yc
    d = d[(d["offset"] >= 1) & (d["offset"] <= max_offset)]
    s0, s1 = start.strftime("%Y-%m"), end.strftime("%Y-%m")
    cohorts = sorted(c for c in base.unique() if s0 <= c <= s1)[-max_cohorts:]
    if not cohorts:
        return None
    grp = d.groupby(["cohort", "offset"])["customer_unique_id"].nunique()
    offsets = list(range(1, max_offset + 1))
    e_abs = int(s1[:4]) * 12 + int(s1[5:7])
    z, m1 = [], []
    for c in cohorts:
        c_abs = int(c[:4]) * 12 + int(c[5:7])
        row = []
        for k in offsets:
            if c_abs + k > e_abs:
                row.append(None)                  # 尚未进入观测期 → 留空
                continue
            v = float(grp.get((c, k), 0)) / max(float(sizes.get(c, 1)), 1) * 100
            row.append(round(v, 2))
            if k == 1:
                m1.append(v)
        z.append(row)
    # 兜底：筛选期内完全没有复购事件时，读取离线结果表，避免整块空白
    if not any(v for r in z for v in r if v is not None):
        fb, _ = _read("cohort_retention.csv", TABLES)
        if not fb.empty and "cohort_month" in fb.columns:
            fb = fb[(fb["cohort_month"].astype(str).str[:7] >= s0) &
                    (fb["cohort_month"].astype(str).str[:7] <= s1)].tail(max_cohorts)
            cohorts = [str(x)[:7] for x in fb["cohort_month"]]
            z = [[round(float(fb.iloc[i][str(k)]) * 100, 2)
                  if str(k) in fb.columns and pd.notna(fb.iloc[i][str(k)]) else None
                  for k in offsets] for i in range(len(fb))]
            m1 = [r[0] for r in z if r and r[0] is not None]
    return cohorts, offsets, z, (float(np.mean(m1)) if m1 else 0.0)


def fig_cohort(matrix) -> go.Figure:
    if matrix is None:
        return polish(go.Figure(), "同期群留存热力图", legend=False)
    cohorts, offsets, z, _ = matrix
    flat = [v for row in z for v in row if v is not None]
    zmax = max(2.0, min(10.0, max(flat) if flat else 2.0))
    avg = float(np.mean(flat)) if flat else 0.0
    diff = [[None if v is None else round(v - avg, 2) for v in row] for row in z]
    fig = go.Figure(go.Heatmap(
        z=z, x=[f"M{k}" for k in offsets], y=cohorts,
        colorscale=GREEN_SCALE, zmin=0, zmax=zmax, hoverongaps=False,
        customdata=np.array(diff, dtype=object),
        colorbar=dict(title=dict(text="留存%", font=dict(size=9, color=MUTED)),
                      thickness=8, len=0.8, outlinewidth=0,
                      tickfont=dict(size=9, color=MUTED)),
        hovertemplate="<b>%{y} 群 · %{x}</b><br>留存率：%{z:.2f}%"
                      "<br>较本期均值：%{customdata:+.2f} pp<extra></extra>"))
    out = polish(fig, "同期群留存热力图", x_title="首购后月数", legend=False)
    out.update_yaxes(type="category", showgrid=False, autorange="reversed",
                     tickfont=dict(size=9, color=MUTED))
    return out


def fig_delivery(f: pd.DataFrame, topn: int = 10) -> go.Figure:
    """下右：各州交付率水平条形图（前 3 名 Teal 高亮）。"""
    if f.empty or "customer_state" not in f.columns:
        return polish(go.Figure(), "各州交付率", legend=False)
    g = f.groupby("customer_state").agg(
        n=("order_id", "nunique"),
        ok=("order_status", lambda s: s.eq("delivered").sum()))
    big = g[g["n"] >= 100]                       # 过滤小样本州，避免 100% 假高
    if not big.empty:
        g = big
    g["rate"] = g["ok"] / g["n"].replace(0, np.nan) * 100
    g = g.dropna(subset=["rate"]).sort_values("rate", ascending=False)
    desc = list(g.index)
    g = g.head(topn).sort_values("rate")
    names, vals = list(g.index), g["rate"].round(1).values
    fig = go.Figure(go.Bar(
        x=vals, y=names, orientation="h",
        marker=dict(color=_top_colors(names, desc), line=dict(width=0)),
        customdata=np.stack([g["ok"].values, g["n"].values], axis=-1),
        text=[f"{v:.1f}%" for v in vals], textposition="outside",
        textfont=dict(size=9, color=MUTED), cliponaxis=False,
        hovertemplate="<b>%{y} 州</b><br>交付率：%{x:.1f}%<br>"
                      "已送达 / 订单：%{customdata[0]:,.0f} / %{customdata[1]:,.0f}"
                      "<extra></extra>"))
    if len(vals):
        fig.update_xaxes(range=[max(0, float(np.min(vals)) - 4), 101.5], ticksuffix="%")
    return polish(fig, "各州交付率", x_title="交付率", legend=False)


def build_figures(data: dict, start: dt.date, end: dt.date,
                  with_frames: bool = True):
    """with_frames=False 用于播放态：省略 21 帧生长序列，减小每帧 JSON 体积、加快刷新。"""
    f = slice_by_dates(data["orders"], start, end, data["day_mode"])
    fi = slice_by_dates(data["items"], start, end, data["day_mode"])
    matrix = cohort_matrix(data, f, start, end)
    m1 = matrix[3] if matrix else 0.0
    figs = [fig_trend(f, with_frames=with_frames), fig_state_gmv(f),
            fig_category_structure(fi), fig_cohort(matrix), fig_delivery(f)]
    return f, fi, figs, m1


# =====================================================================
# 4. Streamlit 交互大屏（时间轴 + 自动播放）
# =====================================================================
# 所有需要持久化的状态集中声明；按钮为瞬时组件，无需预置状态。
STATE_DEFAULTS = {
    "timeline": None,          # 时间轴游标（widget key，值为 'YYYY-MM'）
    "speed_ms": 500,           # 播放速度（widget key）
    "playing": False,          # 是否正在播放
    "run_id": 0,               # 播放会话编号，用于刷新前端定时器组件
    "restart": False,          # 从末月起播时先回到首月
    "step_requested": False,
    "reset_requested": False,
}


def _init_state():
    for k, v in STATE_DEFAULTS.items():
        st.session_state.setdefault(k, v)       # 规范化初始化，杜绝脏状态警告


def _toggle_play():
    st.session_state.playing = not st.session_state.playing
    st.session_state.run_id = int(st.session_state.run_id) + 1
    st.session_state.restart = bool(st.session_state.playing)


def _pause_on_drag():
    st.session_state.playing = False            # 手动拖动时间轴 → 自动暂停


def _request_step():
    st.session_state.playing = False
    st.session_state.step_requested = True
    st.session_state.run_id = int(st.session_state.run_id) + 1


def _request_reset():
    st.session_state.playing = False
    st.session_state.reset_requested = True
    st.session_state.run_id = int(st.session_state.run_id) + 1


def _advance_state(months: list[str]):
    """在「任何 widget 实例化之前」推进游标 —— 这是消除 Session State 警告的关键。"""
    cur = st.session_state.timeline
    if cur not in months:                       # 首屏：默认停在最新月份（全量视图）
        st.session_state.timeline = months[-1]
    if st.session_state.reset_requested:
        st.session_state.timeline = months[-1]
        st.session_state.reset_requested = False
        st.session_state.restart = False
    if st.session_state.step_requested:
        i = months.index(st.session_state.timeline)
        st.session_state.timeline = months[min(i + 1, len(months) - 1)]
        st.session_state.step_requested = False
    if st.session_state.playing:
        i = months.index(st.session_state.timeline)
        last = len(months) - 1
        if st.session_state.restart and i == last:
            st.session_state.timeline = months[0]   # 从末月重新播放：先回到起点
            st.session_state.restart = False
        elif i < last:
            st.session_state.timeline = months[i + 1]
            st.session_state.restart = False
        else:
            st.session_state.playing = False        # 跑到终点自动停表
            st.session_state.restart = False


def run_streamlit_app():
    st.set_page_config(page_title="Olist 巴西电商销售数据驾驶舱",
                       page_icon="📊", layout="wide",
                       initial_sidebar_state="collapsed")
    st.markdown(ST_CSS, unsafe_allow_html=True)
    _init_state()

    data = load_all_cached()
    if data["orders"].empty:
        st.error("未读取到可用的清洗数据，请确认 data/clean/clean_order_agg.csv 存在。")
        st.stop()

    months = list(data.get("months") or [])
    if not months:
        st.error("清洗数据缺少可识别的 purchase_month，无法构建时间轴。")
        st.stop()
    lo, hi = date_bounds(data)

    # ---------- 播放推进（widget 之前） ----------
    _advance_state(months)
    cursor = st.session_state.timeline
    cur_idx = months.index(cursor)
    playing = bool(st.session_state.playing)
    speed_ms = int(st.session_state.speed_ms)
    start_date, end_date = lo, month_end(cursor)

    # ---------- 第一行：标题 ----------
    with st.container():
        st.markdown(
            '<div class="head-title">Olist 巴西电商销售数据驾驶舱</div>'
            '<div class="head-sub">数据源：Kaggle · Olist Brazilian E-Commerce '
            '（CC BY-NC-SA 4.0）｜全 Python · Streamlit + Plotly｜统计口径：清洗后订单聚合表'
            '｜时间轴：截至当前月份的累计数据</div>'
            '<div class="teal-rule"></div>', unsafe_allow_html=True)

    # ---------- 第二行：横向时间轴 + 播放控制（白卡） ----------
    pct = (cur_idx + 1) / len(months) * 100
    state_txt = (f'<span class="tl-state on">● 自动播放中 · {speed_ms / 1000:g}s / 月</span>'
                 if playing else
                 '<span class="tl-state">● 已暂停 · 拖动时间轴或点「▶ 播放」</span>')
    with st.container(border=True):
        st.markdown(
            f'<div class="tl-head"><span class="tl-label">时间轴</span>'
            f'<span class="tl-current">截至 {cursor}</span>'
            f'<span class="tl-progress">第 {cur_idx + 1} / {len(months)} 月'
            f'（{months[0]} → {months[-1]}）</span>'
            f'<span class="tl-bar"><i style="width:{pct:.1f}%"></i></span>'
            f'{state_txt}</div>', unsafe_allow_html=True)

        def tick_label(m: str) -> str:
            """只标首尾 + 每年 1/7 月，避免 23 个刻度挤成一团。"""
            return m if (m in (months[0], months[-1])
                         or str(m).endswith(("-01", "-07"))) else ""

        c1, c2, c3, c4, c5 = st.columns([7.0, 1.2, 0.8, 0.8, 1.4], gap="small")
        with c1:
            st.select_slider("时间轴", options=months, format_func=tick_label,
                             key="timeline", on_change=_pause_on_drag,
                             label_visibility="collapsed")
        with c2:
            st.button("⏸ 暂停" if playing else "▶ 播放", on_click=_toggle_play,
                      use_container_width=True, key="play_btn",
                      help="逐月自动推进时间轴，KPI 与全部图表实时联动")
        with c3:
            st.button("⏭", on_click=_request_step, use_container_width=True,
                      key="step_btn", help="单步前进一个月")
        with c4:
            st.button("⟲", on_click=_request_reset, use_container_width=True,
                      key="reset_btn", help="回到最新月份并暂停")
        with c5:
            st.selectbox("播放速度", [250, 500, 1000], key="speed_ms",
                         format_func=lambda v: f"{v / 1000:g}s / 月",
                         label_visibility="collapsed")

    # ---------- 第三行：5 个 KPI 卡（累计值 + 当月环比） ----------
    cards, vals = kpi_cards(data, start_date, end_date)
    with st.container():
        cols = st.columns(5, gap="small")
        for col, html in zip(cols, cards):
            with col:
                st.markdown(html, unsafe_allow_html=True)

    # ---------- 第四行：一句话业务速读 ----------
    # 播放态不带 frames（时间轴本身已在驱动生长），暂停/静态版才显示图内「▶ 生长」
    f, fi, figs, m1 = build_figures(data, start_date, end_date,
                                    with_frames=not playing)
    with st.container():
        st.markdown(brief_card(data, f, fi, vals, m1, start_date, end_date),
                    unsafe_allow_html=True)

    # ---------- 第五行：图表矩阵（固定 key 便于 Plotly.react 平滑过渡） ----------
    chart_keys = ["chart_trend", "chart_state", "chart_category",
                  "chart_cohort", "chart_delivery"]
    with st.container():
        a, b = st.columns([2, 1], gap="small")
        with a:
            st.plotly_chart(figs[0], use_container_width=True,
                            config=CHART_CFG, key=chart_keys[0])
        with b:
            st.plotly_chart(figs[1], use_container_width=True,
                            config=CHART_CFG, key=chart_keys[1])
    with st.container():
        a, b, c = st.columns(3, gap="small")
        with a:
            st.plotly_chart(figs[2], use_container_width=True,
                            config=CHART_CFG, key=chart_keys[2])
        with b:
            st.plotly_chart(figs[3], use_container_width=True,
                            config=CHART_CFG, key=chart_keys[3])
        with c:
            st.plotly_chart(figs[4], use_container_width=True,
                            config=CHART_CFG, key=chart_keys[4])

    tips = ("数据提示：" + "；".join(data["issues"])) if data["issues"] else ""
    st.markdown(
        '<div class="foot-note">注：GMV = 订单明细 price 求和（不含运费），单位雷亚尔；'
        '时间轴为累计口径（起始月 → 游标月），KPI 角标为游标月对上月的月环比；'
        '交付率 = 已送达订单 / 全部订单；已剔除订单数不足 50 单的不完整月份，'
        '时间轴仅含有效月份（起步期 2016-11 / 2016-12 已跳过）；'
        '留存率按首购月队列等权平均，起步期小样本队列不计入展示，空白表示尚未进入观测期；'
        '品类结构按「商品金额 + 运费」堆叠。趋势图内「▶ 生长」可独立播放逐月生长动画。<br>' +
        escape(tips) + '</div>',
        unsafe_allow_html=True)

    # ---------- 定时器：驱动下一帧 ----------
    if playing:
        if HAS_AUTOREFRESH and PREFER_FRONTEND_TIMER:
            # 可选：前端定时器，按 speed_ms 触发一次全页 rerun → 游标 +1
            st_autorefresh(interval=speed_ms, debounce=False,
                           key=f"player_tick_{st.session_state.run_id}")
        else:
            # 默认且最可靠：本帧已渲染完毕 → 等待一个节拍 → 强制整页 rerun。
            # 下一次 rerun 开头 _advance_state() 会把游标推进一个月，
            # 从而让 KPI / 速读 / 5 张图全部重新计算，形成连续生长动画。
            time.sleep(max(0.1, speed_ms / 1000))
            st.rerun()


# =====================================================================
# 5. 静态导出（兼容 run_all.py 的 --html，风格与主屏一致）
# =====================================================================
def export_static_html():
    from plotly.offline import get_plotlyjs
    data = load_all()
    if data["orders"].empty:
        print("[WARN] 无可用数据，跳过静态导出")
        return
    lo, hi = date_bounds(data)
    months = data.get("months") or []
    f, fi, figs, m1 = build_figures(data, lo, hi)
    cards, vals = kpi_cards(data, lo, hi)
    charts = [x.to_html(full_html=False, include_plotlyjs=False,
                        config=CHART_CFG, div_id=f"chart{i}")
              for i, x in enumerate(figs)]
    pct = 100.0
    html = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Olist 巴西电商销售数据驾驶舱</title>{STATIC_CSS}
<script type="text/javascript">{get_plotlyjs()}</script></head><body><div class="wrap">
<div class="head-row"><div><div class="head-title">Olist 巴西电商销售数据驾驶舱</div>
<div class="head-sub">数据源：Kaggle · Olist Brazilian E-Commerce（CC BY-NC-SA 4.0）｜全 Python · Plotly</div>
<div class="teal-rule"></div></div>
<div class="range-pill">统计范围：{lo:%Y-%m} 至 {hi:%Y-%m}（静态导出版；交互时间轴请用 streamlit run）</div></div>
<div class="dash-card tl-static"><div class="tl-head"><span class="tl-label">时间轴</span>
<span class="tl-current">截至 {hi:%Y-%m}</span>
<span class="tl-progress">第 {len(months)} / {len(months)} 月（{lo:%Y-%m} → {hi:%Y-%m}）</span>
<span class="tl-bar"><i style="width:{pct:.1f}%"></i></span>
<span class="tl-state">● 静态快照 · 趋势图内「▶ 生长」可播放逐月动画</span></div></div>
<div class="kpis">{''.join(cards)}</div>
<div class="brief">{brief_card(data, f, fi, vals, m1, lo, hi)}</div>
<div class="grid-top"><div class="chart">{charts[0]}</div><div class="chart">{charts[1]}</div></div>
<div class="grid-bottom"><div class="chart">{charts[2]}</div><div class="chart">{charts[3]}</div>
<div class="chart">{charts[4]}</div></div>
<div class="foot-note">注：GMV = 订单明细 price 求和（不含运费）；交付率 = 已送达订单 / 全部订单；
已剔除订单数不足 50 单的不完整月份；同期群空白表示尚未进入观测期；品类结构按「商品金额 + 运费」堆叠。</div>
</div></body></html>"""
    for p in (OUT_HTML, ROOT / "outputs" / "index.html"):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html, encoding="utf-8")
        print("[OK] 静态大屏:", p)


if "--html" in sys.argv:
    export_static_html()
else:
    run_streamlit_app()
