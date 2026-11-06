# -*- coding: utf-8 -*-
"""
config.py —— 项目全局配置
统一路径、随机种子、中文字体、配色方案。
所有脚本均通过本模块获取路径，保证从任意工作目录运行都能正确解析。
"""
import os
import numpy as np
import matplotlib

# ----------------------------- 路径配置 -----------------------------
# 项目根目录 = scripts 的上一级目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_CLEAN = os.path.join(PROJECT_ROOT, "data", "clean")
FIG_DIR = os.path.join(PROJECT_ROOT, "outputs", "figures")
TBL_DIR = os.path.join(PROJECT_ROOT, "outputs", "tables")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
NOTEBOOK_DIR = os.path.join(PROJECT_ROOT, "notebooks")

for _d in (DATA_CLEAN, FIG_DIR, TBL_DIR, DOCS_DIR, NOTEBOOK_DIR):
    os.makedirs(_d, exist_ok=True)

# ----------------------------- 实验参数 -----------------------------
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

# 观测窗口末日（用于 RFM 的 Recency 计算）—— Olist 数据最新购买日 2018-10
OBSERVATION_DATE = "2018-10-31"

# ----------------------------- 配色方案 -----------------------------
# 统一商务配色，所有图表共用，保证整体协调
PALETTE = ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2",
           "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7",
           "#9C755F", "#BAB0AC"]
PRIMARY = "#4E79A7"
ACCENT = "#E15759"
GOOD = "#59A14F"
BAD = "#E15759"

# ----------------------------- 中文字体 -----------------------------
def setup_cn_font():
    """
    配置 matplotlib 中文字体。
    优先检测系统中可用的中文字体（含 SimHei / 微软雅黑 / 文泉驿等），
    找不到时回退到 SimHei（多数 Windows 教学机自带），保证用户机器正常显示。
    """
    from matplotlib import font_manager
    candidates = ["SimHei", "Microsoft YaHei", "Microsoft YaHei UI",
                  "WenQuanYi Micro Hei", "WenQuanYi Zen Hei", "Heiti TC",
                  "PingFang SC", "Source Han Sans SC", "Noto Sans CJK SC"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    chosen = None
    for c in candidates:
        if c in available:
            chosen = c
            break
    if chosen is None:
        chosen = "SimHei"  # 回退（用户 Windows 机通常可用）
    matplotlib.rcParams["font.sans-serif"] = [chosen]
    matplotlib.rcParams["axes.unicode_minus"] = False
    matplotlib.rcParams["font.family"] = "sans-serif"
    return chosen

# 程序导入时即设置基础样式
matplotlib.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.autolayout": True,
})

if __name__ == "__main__":
    print("PROJECT_ROOT =", PROJECT_ROOT)
    print("字体:", setup_cn_font())
