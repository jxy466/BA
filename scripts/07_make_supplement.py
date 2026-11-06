# -*- coding: utf-8 -*-
"""
07_make_supplement.py —— 生成论文补充内容：
  4.2 参数与阈值设定依据
  4.3 模型计算与验证（预测类含置信区间与回测误差 MAPE/RMSE）
  22 张图的逐图文字解读

所有数字均取自本项目实际运行结果：
  data/clean/clean.json、clean_order_agg.csv、outputs/tables/*.csv、
  scripts/03_analysis.py 的回测复算，以及 scripts/04_visuals.py 各图 option 中的真实 series 数据。
不与任何图表、图片或既有论文做改动，只输出两份可复制的文本交付物：
  docs/论文补充_4.2-4.3与逐图解读.docx
  docs/论文补充_4.2-4.3与逐图解读.md

运行： D:/anaconda/python.exe scripts/07_make_supplement.py
"""
from __future__ import annotations
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
os.makedirs(DOCS, exist_ok=True)
BASE = "论文补充_4.2-4.3与逐图解读"

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"

STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:eastAsia="SimSun" w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="21"/></w:rPr></w:rPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:pPr><w:spacing w:after="80"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:pPr><w:jc w:val="center"/></w:pPr><w:rPr><w:b/><w:sz w:val="36"/><w:rFonts w:eastAsia="SimHei"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="240" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="30"/><w:rFonts w:eastAsia="SimHei"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="200" w:after="100"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="26"/><w:rFonts w:eastAsia="SimHei"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="140" w:after="60"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:sz w:val="22"/><w:rFonts w:eastAsia="SimHei"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Caption"><w:name w:val="Caption"/><w:basedOn w:val="Normal"/><w:pPr><w:jc w:val="center"/></w:pPr><w:rPr><w:i/><w:sz w:val="18"/><w:color w:val="595959"/></w:rPr></w:style>
</w:styles>'''


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Doc:
    def __init__(self):
        self.body = []

    def para(self, text, style=None, bold=False):
        ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
        runs = "".join(
            f'<w:r>{rpr}<w:t xml:space="preserve">{esc(part)}</w:t></w:r>'
            for part in str(text).split("\n"))
        self.body.append(f"<w:p>{ppr}{runs}</w:p>")

    def heading(self, text, level=1):
        self.para(text, style=f"Heading{level}")

    def table(self, headers, rows):
        n = len(headers)
        cw = int(9000 / n)
        grid = "".join(f'<w:gridCol w:w="{cw}"/>' for _ in headers)
        hcells = "".join(
            f'<w:tc><w:tcPr><w:tcW w:w="{cw}" w:type="dxa"/><w:shd w:val="clear" w:fill="DCE6F1"/></w:tcPr>'
            f'<w:p><w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{esc(h)}</w:t></w:r></w:p></w:tc>'
            for h in headers)
        trows = ""
        for row in rows:
            cells = "".join(
                f'<w:tc><w:tcPr><w:tcW w:w="{cw}" w:type="dxa"/></w:tcPr>'
                f'<w:p><w:r><w:t xml:space="preserve">{esc(c)}</w:t></w:r></w:p></w:tc>'
                for c in row)
            trows += f"<w:tr>{cells}</w:tr>"
        self.body.append(
            f'<w:tbl><w:tblPr><w:tblW w:w="9000" w:type="dxa"/><w:tblBorders>'
            f'<w:top w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
            f'<w:left w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
            f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
            f'<w:right w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
            f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
            f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
            f'</w:tblBorders></w:tblPr><w:tblGrid>{grid}</w:tblGrid>'
            f'<w:tr>{hcells}</w:tr>{trows}</w:tbl>')
        self.para("")

    def build(self):
        sect = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
                '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
                'w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>')
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<w:document xmlns:w="{W}" xmlns:r="{R}" xmlns:wp="{WP}" '
                f'xmlns:a="{A}" xmlns:pic="{PIC}"><w:body>'
                + "".join(self.body) + sect + '</w:body></w:document>')


# ==========================================================================
# 正文内容：所有数字来自项目真实输出，逐项与 22 张图的 option / 副标题核对
# ==========================================================================
B = []


def h1(t):
    B.append(("h1", t))


def h2(t):
    B.append(("h2", t))


def h3(t):
    B.append(("h3", t))


def p(t):
    B.append(("p", t))


def li(t):
    B.append(("li", t))


def table(headers, rows):
    B.append(("table", headers, rows))


h1("论文补充内容：4.2、4.3 与 22 张图文字解读")
p("使用说明：本文件为可直接复制进论文的补充内容。其中「4.2 参数与阈值设定依据」「4.3 模型计算与验证」对应论文第 4 章缺的两节；"
  "「逐图文字解读」按图号排列，可直接粘贴到第 5 章对应图注之后。全部数值取自本项目实际运行结果"
  "（data/clean/clean.json、data/clean/clean_order_agg.csv、outputs/tables/*.csv、scripts/03_analysis.py 与 scripts/04_visuals.py），"
  "与 outputs/figures/ 中 22 张 PNG 图上显示的数值、副标题及注脚逐一核对一致；未改动任何图表、图片或既有论文文件。"
  "表中金额单位除特别注明外为雷亚尔（BRL），图中为便于阅读统一换算为「万雷亚尔」。")

# ---------------------------------------------------------------- 4.2
h2("4.2　参数与阈值设定依据")
p("本节给出 5 种商业分析模型的参数、阈值以及 22 张图的展示阈值及其设定依据。所有参数均固化在 "
  "scripts/03_analysis.py、scripts/04_visuals.py 中，随机种子 RANDOM_SEED=42，结果由 run_all.py 一键复现并写入 "
  "outputs/tables/。阈值均由数据分布特征或业务口径确定，未使用人为设定的「好看数值」；"
  "凡因数据本身缺陷而做的裁剪，均在对应图注脚中公开声明。")

h3("4.2.1　数据口径与观测窗口")
li("观测窗口末日为 2018-10-31（clean.json 的 observation_date），数据实际覆盖 2016-09-04 至 2018-10-17。"
   "Recency 定义为末次购买距该末日的月数，越小表示越近期。")
li("清洗后用于统计与绘图的订单聚合表共 98,666 笔订单、95,420 名唯一客户、72 个商品品类，GMV 合计 13,591,643.70 雷亚尔"
   "（约 1,359.2 万）。clean.json 中记录的 99,441 笔为原始订单数，差额来自剔除无购买时间、无效明细等订单；"
   "所有图表均以清洗后的 clean_order_agg.csv 为准。")
li("GMV 口径为订单明细 price 求和（不含运费）；金额单位为雷亚尔，图中统一换算为万雷亚尔。"
   "Olist 原始数据不含成本字段，故 fig05 的「利润额」采用「销售额 − 运费」的净收入口径近似，已在图注脚声明。")
li("月度建模序列统一取 2017-01 至 2018-08 共 20 个完整自然月：剔除 2016 年平台起步期（月订单个位数、GMV 近零）"
   "与 2018-09 不完整月末（仅 1 单）。二者属于不完整观测而非真实业务变化，若不剔除会在趋势、同比与预测图上"
   "形成「假断崖」或「假高增长」。该规则在 fig04、fig07、fig08、fig13、figb05 中一致执行。")

h3("4.2.2　五种模型的参数与阈值及业务依据")
table(
    ["模型", "参数 / 阈值", "实际取值", "设定依据"],
    [
        ["RFM 八分类", "R、F、M 切分点", "中位数：R=9.0 月，F=1.0 次，M=89.90 雷亚尔",
         "三项均右偏长尾，中位数比均值稳健；R≤中位数记「高」（越近期越好），F、M 严格大于中位数记「高」。"],
        ["RFM 八分类", "F、M 采用严格大于（>）而非大于等于",
         "F>1 客户 2,913 人（3.1%）；M>89.90 客户 46,567 人（48.8%）；R≤9 客户 52,565 人（55.1%）",
         "频率中位数恰为 1，若用「≥」则全部客户 F 均为「高」，八分类塌缩为四类，模型失效。"],
        ["同期群留存", "分群键、偏移上限、观测截止", "首购月份 cohort_month；偏移 1—20 月；观测截止 2018-09",
         "观察窗约 25 个月，最长可观测 20 余期；空白单元格表示「尚未进入观测期」，与「真实 0 留存」严格区分，避免把缺测当流失。"],
        ["帕累托 / ABC", "累计 GMV 占比阈值", "80%；72 个品类中第 18 个（pet shop）累计首次达 81.2%",
         "经典 80/20 法则，用数据定位头部品类。若需 ABC 三级，可按 80% / 95% 划分（95% 对应第 34 个品类、累计 95.3%），本文仅采用 80% 单一阈值以免引入未验证的人为分级。"],
        ["时间序列预测", "预测步长 h、回测划分、置信水平", "h=6 月；训练 14 月（2017-01—2018-02）＋测试 6 月（2018-03—2018-08）；95%（α=0.05，t 分布，自由度 n−2）",
         "6 个月可覆盖一个完整年末旺季并留出 30% 样本回测；样本仅 20 个完整月、不足 2 个完整年周期（24 月），SARIMA / Holt-Winters 季节项初始化欠定，改用可解释且能给出解析预测区间的「加性季节分解＋OLS 趋势外推」。"],
        ["Apriori 关联规则", "购物篮单元、最小支持度、最小置信度、提升度、最大项集长度",
         "顾客跨订单品类集合（2,327 个含 ≥2 品类的购物篮）；support≥0.005；confidence≥0.1；lift>1；max_len=2",
         "订单级购物篮约 98% 为单品类，订单内共现极稀疏，提升到顾客层面才能捕捉真实的「买了又买」；0.005 在 2,327 个篮子中相当于至少约 12 位顾客共同购买，可过滤偶发组合；lift>1 保证只保留正相关规则。阈值筛选后得到 16 条规则（Lift 1.11—3.03）。"],
    ])
p("口径说明：03_analysis.py 注释中「支持度 0.005 约 500 名跨品类顾客」是以全部 95,420 名客户为基数的粗略估计；"
  "按实际参与挖掘的 2,327 个购物篮计算，最小支持计数约为 12，本节与结果表均以实际计算口径为准。"
  "两种口径下阈值都只保留具有一定共现规模的品类对，最终由 16 条有效规则验证。")

h3("4.2.3　图表展示阈值与裁剪规则")
table(
    ["图表参数 / 阈值", "取值", "设定依据"],
    [
        ["TopN 截取", "州 Top12、品类 Top10、帕累托 Top20、季度 2017Q1 起且订单数≥100",
         "在保留主要贡献与横轴可读性间平衡：Top12 州已覆盖 91.5% GMV，Top10 品类覆盖 63.6% 订单明细；剔除以个位数订单起步的季度，避免比率失真。"],
        ["RFM 气泡图抽样", "Monetary 截尾至 99 分位；每个分群分层抽样 320 人，共 2,412 点",
         "95,420 名客户全绘会严重过绘；截尾抑制极端消费额，分层抽样保证 8 类客群在图中均可见。"],
        ["滑珠图纵轴", "自 95% 起截断，上限 100%",
         "各州履约率均在 98% 以上，从 0 起会把不到 1 个百分点的州际差异压平；图注脚已声明截断，避免误读为巨大差异。"],
        ["热力图色标", "留存 0—2%；关联 Lift 1—3.03",
         "留存率绝大多数单元格低于 2%，压缩色标才能显出低复购区间层次；Lift 下限 1 即「正相关」，高于上限按最高色显示。"],
        ["交叠柱几何", "barGap=-100%，宽蓝柱 48px、窄红柱 34px，z 分层",
         "对照教材模板做「前后交叠」而非上下堆叠，两系列共享同一基线，直观比较销售额与净收入；Olist 无成本字段，净收入口径已在注脚声明。"],
        ["缺失月处理", "2018 年 9—12 月留空，不做插值",
         "2018-09 仅 1 单、其后无数据，任何插值都会虚构数值；留空是对数据边界的诚实表达。"],
        ["输出规格", "画布 1280×720，2 倍像素比 PNG，随机种子 42",
         "保证论文插图放大后仍清晰，且抽样与全部建模结果可复现。"],
    ])

# ---------------------------------------------------------------- 4.3
h2("4.3　模型计算与验证（预测类含置信区间与回测误差 MAPE/RMSE）")
p("本节先给出各模型的计算公式与指标定义，再汇报实际计算结果；预测类模型重点给出 95% 置信区间的构造方式、"
  "未来 6 个月的点预测与区间，以及留出法回测的 MAPE、RMSE 与区间命中情况。所有计算由 scripts/03_analysis.py 完成，"
  "结果保存在 outputs/tables/ 与 analysis_metrics.json 中，可由 run_all.py 一键复现。")

h3("4.3.1　指标定义与计算流程")
li("RFM 二值化与分群：R高 = I(R≤9)，F高 = I(F>1)，M高 = I(M>89.90)；三个 0/1 维度按映射表组合为 8 类客户，"
   "并统计各类的客户数、平均 R / F / M，输出 rfm_full.csv、rfm_segments.csv。")
li("同期群留存率：R(c,k) = N(c,k) / N(c,0)。其中 c 为首购月份，k 为首购后第 k 个自然月，"
   "k = (购买年 − 首购年)×12 + (购买月 − 首购月)，N 为去重客户数；按 c×k 透视得到 23×20 留存矩阵。")
li("帕累托累计占比：C(k) = Σ(i=1..k) GMV(i) / Σ(i=1..72) GMV(i)，GMV 按品类降序排列，"
   "首次满足 C(k)≥0.8 的 k 即头部品类数，输出 pareto_category.csv。")
li("关联规则：support(A→B) = |A∩B| / N，confidence(A→B) = |A∩B| / |A|，"
   "lift(A→B) = confidence(A→B) / support(B)。仅保留 support≥0.005、confidence≥0.1、lift>1 的二元规则。")
li("预测模型（加性分解＋OLS）：设 y(t) 为第 t 月 GMV，日历月 m 的加性季节指数 S(m) = mean(y | 月份=m) − mean(y)；"
   "去季节序列 d(t) = y(t) − S(m)；对 d(t) = β0 + β1·t + ε 做最小二乘，得到 β̂ = (X′X)⁻¹X′d；"
   "外推 ŷ(n+k) = β̂0 + β̂1·(n−1+k) + S(m(n+k))。")
li("95% 预测区间：ŷ(n+k) ± t(0.975, n−2) · s · √[1 + x0′(X′X)⁻¹x0]，其中 s² = Σε̂²/(n−2)，"
   "x0 = (1, n−1+k)。区间同时包含残差波动与回归系数估计的不确定性，并随预测步长 k 增大而变宽。")
li("回测误差：MAPE = (1/h)·Σ|y−ŷ|/|y|×100%，RMSE = √[(1/h)·Σ(y−ŷ)²]，h=6；"
   "采用「留出末 6 月」的时间序列回测，不使用随机打乱，避免未来信息泄漏。")

h3("4.3.2　五种模型的计算结果与交叉核对")
table(
    ["模型", "实际计算结果（来自结果表）", "核对结论"],
    [
        ["RFM 八分类", "95,420 名客户分入 8 类：一般发展 26,199 人、重要发展 24,622 人、一般挽留 22,162 人、重要挽留 19,524 人、重要价值 1,478 人、重要保持 943 人、一般价值 266 人、一般保持 226 人；一般发展＋重要发展合计占 53.3%",
         "8 类客户数合计恰等于唯一客户数 95,420，无遗漏、无重复；高价值（重要价值＋重要保持）共 2,421 人，与图 B1 的 2,356 人差异仅来自 99 分位截尾抽样。"],
        ["同期群留存", "23 个首购月队列、270 个已观测单元格；第 1 月平均留存 5.20%，第 3 月 0.254%，此后多数月份仅 0.2%—0.6%",
         "与热力图副标题一致；热力图中空白为尚未观测，不是 0 留存，消除旧版 NaN 与全浅黄问题。"],
        ["帕累托 / ABC", "72 个品类总 GMV 1,359.2 万；前 18 个累计 81.2%；第 1 名 health_beauty 125.9 万（9.3%）",
         "帕累托图前 20 根柱的累计占比折线与 pareto_category.csv 逐点一致，80% 阈值线在第 17 与第 18 根柱之间被穿越。"],
        ["时间序列预测", "趋势斜率 β̂1 = +37,624 雷亚尔/月；季节指数最高为 11 月 +442,413、最低为 4 月 −207,931；未来 6 月点预测 102.9—149.2 万",
         "11 月峰值与历史 2017-11 的 101 万 GMV 峰值方向一致，季节项具有业务可解释性（年末旺季）。"],
        ["Apriori 关联规则", "16 条规则，Lift 1.11—3.03；最强 home_confort→bed_bath_table（support 0.0244、confidence 0.740、lift 3.03），其次 construction_tools_lights→furniture_decor（lift 2.58）",
         "16 条规则全部落入 14×14 提升度矩阵，空白表示未产生满足阈值的规则而非 Lift=0；全部 lift>1 说明保留的是正相关关系。"],
    ])

h3("4.3.3　预测模型的 95% 置信区间与未来 6 月结果")
p("回测阶段用 14 个月训练，残差方差 s² = 1.6691×10¹⁰（残差标准差 s ≈ 129,195 雷亚尔），"
  "t(0.975, 12) = 2.1788，截距 β̂0 = 323,299、斜率 β̂1 = 37,624 雷亚尔/月。"
  "正式预测用全部 20 个完整月重新拟合，按同一公式给出 2018-09 至 2019-02 的点预测与 95% 预测区间"
  "（sarima_forecast.csv；下表换算为万雷亚尔，保留 1 位小数）。")
table(
    ["月份", "点预测", "95% 下界", "95% 上界", "区间宽度"],
    [
        ["2018-09", "102.9", "75.4", "130.4", "55.0"],
        ["2018-10", "110.8", "82.9", "138.6", "55.8"],
        ["2018-11", "149.2", "120.9", "177.5", "56.6"],
        ["2018-12", "126.4", "97.7", "155.2", "57.4"],
        ["2019-01", "109.4", "80.2", "138.6", "58.3"],
        ["2019-02", "114.3", "84.7", "144.0", "59.3"],
    ])
p("可见 2018-11 点预测最高（149.2 万），对应 11 月最强的正季节指数，与历史 2017-11 峰值相呼应；"
  "区间宽度由 55.0 万逐步扩大到 59.3 万，符合预测标准误随时域延长的统计规律。"
  "图 B5 中红色虚线为点预测、粉色阴影为 95% 预测区间，实际值折线止于 2018-08，二者不重叠、不混淆。")

h3("4.3.4　留出法回测与误差评估（MAPE / RMSE）")
p("以 2017-01 至 2018-02 共 14 个月训练，对 2018-03 至 2018-08 共 6 个月做样本外预测。"
  "下表单位万雷亚尔，APE 为单期绝对百分比误差。")
table(
    ["月份", "实际", "点预测", "95% 预测区间", "是否落入区间", "APE"],
    [
        ["2018-03", "98.3", "65.7", "33.3~98.0", "否（超出上界 0.35%）", "33.2%"],
        ["2018-04", "99.7", "68.0", "34.8~101.1", "是", "31.8%"],
        ["2018-05", "99.7", "86.4", "52.2~120.5", "是", "13.4%"],
        ["2018-06", "86.5", "82.8", "47.7~117.9", "是", "4.3%"],
        ["2018-07", "89.6", "93.1", "56.9~129.3", "是", "3.9%"],
        ["2018-08", "85.5", "104.4", "67.1~141.8", "是", "22.2%"],
    ])
p("汇总指标：MAPE = 18.13%，RMSE = 209,525 雷亚尔（约 21.0 万），95% 区间命中 5/6 期（83.3%），"
  "与 analysis_metrics.json 中的 backtest_mape = 18.1277、backtest_rmse = 209525.44 完全一致。"
  "误差结构可解释：2018 年 3—4 月被低估 32% 左右，原因是 GMV 从 2017 年爬坡期跃升至约 100 万的高位平台，"
  "14 个月的线性趋势难以及时捕捉这一结构变化；2018-08 高估 22.2%，源于趋势惯性叠加年末旺季前的季节指数；"
  "2018-03 实际 98.32 万仅比区间上界 97.98 万高 0.35%，属边界情形。"
  "在仅 20 个完整月、无促销/节假日等外生变量的条件下，MAPE 低于 20%、区间覆盖率 83%，"
  "说明模型可用于旺季备货、物流扩容与库存规划的方向性判断，但不宜作为精确财务预算依据。"
  "改进方向为延长样本至 2 个以上完整季节周期后改用 SARIMA / 状态空间模型，或引入促销日历等外生变量。")

h3("4.3.5　验证结论与可复现性")
p("五个模型的输出均与 charts 所引用的结果表逐项对齐：图 B1/B2 的客群规模来自 rfm_segments.csv，"
  "图 B3 的留存矩阵来自 cohort_retention.csv，图 B4 的柱与累计折线来自 pareto_category.csv，"
  "图 B5 的点预测与区间来自 sarima_forecast.csv、回测误差来自 analysis_metrics.json，"
  "图 B6 的 Lift 矩阵来自 association_rules.csv。抽样固定随机种子 42，OLS 与 Apriori 为确定性计算，"
  "因此重复运行 run_all.py 可得到完全相同的结果，满足可复现与可验证要求。")

# ---------------------------------------------------------------- 逐图解读
h1("5　22 张图的文字解读（可直接插入对应图注之后）")
p("以下每条解读均按图中实际显示的数值、副标题与注脚撰写，图名后括号内为 outputs/figures/ 中的文件名，"
  "便于与论文插图一一对应。")

h2("5.1　模板复现图（16 张）")

FIGURES = [
    ("图 1", "各州 GMV 贡献对比（fig01_gmv_by_state.png）",
     "图中按 GMV 降序展示 Top12 州：SP 520.3 万雷亚尔居首，占全国 38.3%；RJ 182.4 万、MG 158.5 万，"
     "Top3 合计 63.4%，第 4 名 RS 骤降至 75.0 万。柱体逐根采用不同渐变色与圆角顶，柱顶带框数字便于直接读数。"
     "该图说明 Olist 的销售高度集中于圣保罗、里约、米纳斯吉拉斯三州，区域市场结构呈明显长尾，"
     "物流仓网与区域营销预算应优先覆盖头部三州。"),
    ("图 2", "品类平均售价（fig02_sales_by_category_mean.png）",
     "Top12 高价品类中 computers 最贵（1,098.3 雷亚尔），其次为 small appliances home oven and coffee（624.3）、"
     "home appliances 2（476.1）；金色虚线为全站平均售价 121 雷亚尔，入选的 12 个品类均价全部高于该均值。"
     "高单价品类集中于耐用品与家电，与后文热销品类的销量榜单形成「价高量小、价低量大」的对照，"
     "提示可用高单价品类做客单价提升、用高频品类做流量入口。"),
    ("图 3", "热销品类 Top10 销量对比（fig03_top_category_bar.png）",
     "bed bath table 以 11,115 件居首，health beauty 9,670 件、sports leisure 8,641 件紧随其后，"
     "Top10 品类合计占全部订单明细的 63.6%。蓝色渐变圆角柱与带框数值标签突出头部集中度："
     "家居、美妆、运动休闲三类构成平台流量基本盘，长尾品类虽多但单品类销量有限，适合以组合推荐带动。"),
    ("图 4", "月度订单量（fig04_monthly_orders_labeled.png）",
     "展示 2017-01 至 2018-08 共 20 个完整自然月：2017-01 仅 789 单，2017-11 达峰值 7,451 单，"
     "期间月均 4,918 单；2018 年各月稳定在 6,160—7,220 单区间。11 月峰值对应巴西年末促销季，"
     "2018 年不再出现 2017 年那样的陡峭爬坡，说明平台已进入相对稳定运营期。图注脚已声明剔除 2016 起步期与 2018-09 不完整月末。"),
    ("图 5", "2017—2018 季度销售额与利润额（fig05_stacked_quarter.png）",
     "采用模板式「前后交叠柱」而非上下堆叠：宽蓝柱为季度销售额，窄红柱为利润额，两柱共基线、同位置叠放，"
     "右侧中部为两个彩色边框图例框。销售额由 2017Q1 的 74 万增至 2018Q2 峰值 286 万，利润额同期由 63 万增至 238 万；"
     "2018Q3 回落至 175 万 / 144 万（该季主要来自 7—8 月完整数据，9 月仅 1 单）。全期运费占销售额 16.6%、净收入率 83.4%，"
     "两柱间距直观反映物流成本对收入的侵蚀；Olist 无成本字段，利润额按「销售额−运费」净收入口径近似，已在注脚声明。"),
    ("图 6", "各州 GMV 蝴蝶图（fig06_butterfly_state.png）",
     "左侧为 2017 年全年、右侧为 2018 年 1—8 月各州 GMV（万雷亚尔），按两年合计降序取 Top10。"
     "SP 两年累计 519 万居首（2017 年 221 万、2018 年 298 万），MG 由 72 万增至 86 万，RJ 基本持平（91 万 / 91 万），"
     "2018 年 Top10 合计 655 万。需注意的是两侧时间口径不同（12 个月 vs 8 个月），"
     "因此该图用于比较各州的结构位次与增长方向，不宜直接把左右柱长当作同比增速。"),
    ("图 7", "月度 GMV 趋势（fig07_monthly_gmv_line.png）",
     "2017-01 的 12.0 万上升至 2017-11 峰值 101.0 万，副标题显示相对起点增长 610%；"
     "2017-12 回落至 74.4 万后，2018 年在 84.4—99.7 万的高位平台震荡，2018-08 为 85.5 万。"
     "蓝色平滑折线配渐变面积并标注峰值/谷值，直观呈现「快速爬坡—旺季冲高—高位企稳」三阶段，"
     "为预测模型采用线性趋势叠加季节项提供了图形依据。"),
    ("图 8", "月度 GMV 对比（fig08_compare_line.png）",
     "蓝线为 2017 年 12 个月、金线为 2018 年 1—8 月，8 个可比月份中 2018 年 GMV 合计较 2017 年同期增长 137.4%。"
     "差异主要来自 1—5 月（如 1 月 12.0 万→95.0 万、5 月 50.6 万→99.7 万），而 7—8 月两线已接近（49.8→89.6、57.4→85.5），"
     "说明高增长部分是 2017 年初低基数效应。2018 年 9—12 月因数据不完整留空且不做插值，注脚已声明。"),
    ("图 9", "订单完成率（fig09_donut_completion.png）",
     "圆环中心显示 97.8%，即 96,478 笔已送达订单占清洗后 98,666 笔订单的比例，其余 2.2%（2,188 笔）为在途、取消等状态。"
     "蓝色扇区代表已送达、顶部未填充蓝色的深灰扇区代表其他状态；「已送达」标签贴在蓝色圆环左侧、"
     "「其他状态」标签位于深灰扇区正上方，均与圆环靠近，避免标签与扇区错配。该图与图 12 仪表盘使用同一口径，可交叉验证。"),
    ("图 10", "用户满意度（fig10_waterball_satisfaction.png）",
     "水球液位为 82.1%，即平均评论评分 4.11 / 5 的达成率；副标题同时给出 4—5 分好评占比 77.0%。"
     "水球以波浪液位把单一比率转为直观的「充盈度」，蓝色渐变与描边增强层次。"
     "结合图 16 玉玦图可知：整体口碑良好，但仍有约 23% 的非好评订单，是履约与品控的改进空间。"),
    ("图 11", "各州 GMV 占比（fig11_nightingale_state.png）",
     "以极坐标花瓣面积表示 Top12 州 GMV：SP 占 38.3% 居首，Top12 州合计贡献 91.5% 的 GMV。"
     "与图 1 使用同一组 520.3、182.4、158.5 万等真实数值，但玫瑰图用半径与面积强化「一州独大」的视觉冲击，"
     "适合在论文中作为区域集中度的第二重佐证。"),
    ("图 12", "整体履约率（fig12_gauge_fulfillment.png）",
     "半圆仪表盘指针指向 97.8%，轴带按 60% / 85% 分段着色（红—金—绿），进度弧与白色指针共同强调当前落在绿色区间；"
     "副标题提示未送达 2,188 单需重点跟进。图注脚说明履约率以订单状态 delivered 口径统计，与图 9 数值一致。"
     "仪表盘适合表达「目标达成度」，但不宜用于州际比较，后者由图 15 承担。"),
    ("图 13", "月度订单量与同比（fig13_bar_line_gmv_yoy.png）",
     "蓝柱为 2018 年 1—8 月订单数（7,220、6,694、7,188、6,934、6,853、6,160、6,273、6,452 单），"
     "金色折线为对 2017 年同月的同比增速（右轴）：1 月高达 815.1%，随后回落至 8 月的 50.3%，期间平均 218.8%。"
     "这种前高后低的同比曲线主要源于 2017 年初仅 789 单的低基数，而非订单量在 2018 年内暴涨；"
     "2018 年 9—12 月因数据不完整不显示，注脚已声明。"),
    ("图 14", "品类 GMV 子弹图（fig14_bullet_category.png）",
     "宽灰底为全期累计商品金额，窄蓝条为 2018 年（截至 9 月）商品金额，二者均为真实统计值。"
     "health beauty 累计 125.9 万、2018 年 77.2 万，watches gifts 为 120.5 万 / 70.9 万，"
     "garden tools 仅 48.5 万 / 21.5 万；Top10 品类 2018 年贡献占其累计 GMV 的 54.8%。"
     "窄条占宽底的比例反映各品类近期销售动能，可用于判断哪些头部品类仍在加速。"),
    ("图 15", "各州履约率（fig15_lollipop_fulfillment.png）",
     "细杆加圆珠展示 Top12 州履约率：MS 最高 98.9%，AC 98.8%，最低 SC / TO 98.2%，Top12 平均 98.5%。"
     "纵轴自 95% 起截断以放大不到 1 个百分点的州际差异，注脚明确说明全州实际值均在 98% 以上，"
     "因此该图只用于识别相对落后的州，不能解读为州际履约水平悬殊。"),
    ("图 16", "好评率（fig16_jade_score.png）",
     "玉玦环显示 4—5 分好评占 77.0%，缺口为其余 23.0% 的非好评订单；中心数字与副标题给出平均评分 4.11 / 5。"
     "与图 10 水球图同源（满意度达成率 82.1% 来自同一评分均值），两图分别强调「评分水位」与「好评结构」，"
     "共同支撑「整体口碑良好但仍有约四分之一订单存在体验改进空间」的判断。"),
]
for num, cap, txt in FIGURES:
    h3(f"{num}　{cap}")
    p(txt)

h2("5.2　业务模型图（6 张，与第 4 章模型一一对应）")
BIZ_FIGURES = [
    ("图 B1", "RFM 客户价值气泡图（figb01_rfm_bubble.png）",
     "横轴为 Recency（月，越小越近期），纵轴为 Monetary（雷亚尔，截尾至 99 分位），气泡大小映射 Frequency，"
     "颜色区分八类客群。按分群分层抽样后共绘制 2,412 名客户，副标题注明截尾后的重要价值／保持类共 2,356 人"
     "（全量为 2,421 人，差额来自 99 分位截尾）。图中 R 小、M 大且气泡更大的点集中在「重要价值客户」，"
     "而绝大多数点分布在 M<100 雷亚尔的低消费带，并沿 R 轴分为近期（0—9 月）与沉默（10 月以上）两簇，"
     "直观印证平台复购少、客单价低的客群结构。"),
    ("图 B2", "RFM 八类客户规模（figb02_rfm_bar.png）",
     "横向渐变条按客户数升序排列：一般保持 226 人、一般价值 266 人、重要保持 943 人、重要价值 1,478 人、"
     "重要挽留 19,524 人、一般挽留 22,162 人、重要发展 24,622 人、一般发展 26,199 人；"
     "一般发展＋重要发展两类合计占 53.3%。该图把气泡图的分布转为可量化的分群规模，"
     "说明运营资源应分层投放：对 2,421 名高价值客户做留存维护，对近 5 万名「发展／挽留」客户做召回与二次转化。"),
    ("图 B3", "同期群留存热力图（figb03_cohort_heatmap.png）",
     "行是 23 个首购月份队列（2016-09 至 2018-08，缺 2016-11），列是首购后 1—20 个月，"
     "色标压缩在 0—2% 以显出低留存区间层次。首购后第 1 个月平均留存仅 5.2%，第 3 月 0.25%，"
     "此后多数月份仅 0.2%—0.6%。重建连续偏移列后，空白表示「该队列尚未进入观测期」而非 0 留存，"
     "真实 0 留存以低值色显示，消除了旧版 NaN 与全浅黄问题。结论是平台复购极弱、增长高度依赖新客获取。"),
    ("图 B4", "品类销售额帕累托图（figb04_pareto.png）",
     "Top20 品类的 GMV 柱从 health beauty 125.9 万递减至 small appliances 19.1 万，"
     "金色折线为累计占比（右轴）：第 17 个 computers 处为 79.6%，第 18 个 pet shop 达 81.2%，首次穿越 80% 阈值虚线，"
     "Top20 累计 84.0%。也就是说 72 个品类中约 25%（18 个）贡献了 80% 销售额，"
     "头部品类 health beauty 单一占比 9.3%，验证了「少数品类驱动多数营收」，为库存与营销资源倾斜提供依据。"),
    ("图 B5", "月度 GMV 预测（figb05_forecast.png）",
     "蓝色实线为 2017-01—2018-08 的 20 个实际值（12.0 万至 101.0 万），红色虚线为 2018-09—2019-02 的 6 个月点预测"
     "（102.9、110.8、149.2、126.4、109.4、114.3 万），粉色阴影为 95% 预测区间，"
     "宽度约 55—59 万并随步长递增。副标题注明采用加性季节分解＋OLS 趋势外推、回测 MAPE≈18.1%，"
     "11 月预测峰值与历史年末旺季一致。图中实际与预测以线型、颜色、区间带明确区分，避免把预测值误读为已发生业绩。"),
    ("图 B6", "关联规则提升度热力图（figb06_association_heatmap.png）",
     "14×14 的「前项 × 后项」品类矩阵完整容纳 16 条规则，单元格标注 Lift 数值，色标 1—3.03，"
     "空白表示该品类对未产生满足支持度／置信度阈值的规则（并非 Lift=0）。最强关联为 "
     "home_confort → bed_bath_table 及其反向（Lift 3.03），其次 construction_tools_lights → furniture_decor（2.58）、"
     "baby → cool_stuff（2.51）。规则成对出现且全部 Lift>1，说明家居／寝具、工具／家具、母婴／玩具等存在真实互补关系，"
     "可用于结算页「买了又买」推荐；矩阵整体稀疏也印证了跨品类连带偏弱的判断。"),
]
for num, cap, txt in BIZ_FIGURES:
    h3(f"{num}　{cap}")
    p(txt)

h2("5.3　引用一致性提示")
p("为免论文内部数字冲突，引用时建议以本补充文档与 22 张图的当前数值为准："
  "① 图 B1 的 2,356 人是 99 分位截尾后的高价值客户数，全量为 2,421 人；"
  "② 订单完成率／履约率按 clean_order_agg.csv 的 delivered 口径为 97.8%，"
  "与 clean.json 中按原始订单计算的 delivered_ratio（97.02%）口径不同；"
  "③ 当前图表由 pyecharts / ECharts 生成并以 2 倍像素比 PNG 导出，"
  "评分标准自检表中「Matplotlib 异型图、dpi=150、履约率约 92%」等为早期版本描述，若论文引用需同步更新。")

h1("附录：本文档数据来源")
p("data/clean/clean.json；data/clean/clean_order_agg.csv、clean_order_items.csv；"
  "outputs/tables/analysis_metrics.json、rfm_segments.csv、rfm_full.csv、cohort_retention.csv、"
  "pareto_category.csv、sarima_forecast.csv、association_rules.csv；"
  "scripts/03_analysis.py（模型与回测）、scripts/04_visuals.py（22 张图的数据与文案）、"
  "outputs/figures/fig*.png / fig*.html（图上实际数值与副标题）。")


# ==========================================================================
# 渲染：docx + markdown
# ==========================================================================
def render_docx(path):
    d = Doc()
    for item in B:
        kind = item[0]
        if kind == "h1":
            d.heading(item[1], 1)
        elif kind == "h2":
            d.heading(item[1], 2)
        elif kind == "h3":
            d.heading(item[1], 3)
        elif kind == "p":
            d.para(item[1])
        elif kind == "li":
            d.para("• " + item[1])
        elif kind == "table":
            d.table(item[1], item[2])

    document = d.build()
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{REL}"><Relationship Id="rId1" '
            f'Type="{R}/styles" Target="styles.xml"/></Relationships>')
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                     '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                     '</Types>')
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 f'<Relationships xmlns="{REL}"><Relationship Id="rId1" '
                 f'Type="{R}/officeDocument" Target="word/document.xml"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", STYLES)
        z.writestr("word/_rels/document.xml.rels", rels)


def render_md(path):
    lines = []
    for item in B:
        kind = item[0]
        if kind == "h1":
            lines += ["# " + item[1], ""]
        elif kind == "h2":
            lines += ["## " + item[1], ""]
        elif kind == "h3":
            lines += ["### " + item[1], ""]
        elif kind == "p":
            lines += [item[1], ""]
        elif kind == "li":
            lines += ["- " + item[1], ""]
        elif kind == "table":
            headers, rows = item[1], item[2]
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("|" + "|".join(["---"] * len(headers)) + "|")
            for row in rows:
                lines.append("| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |")
            lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    docx_path = os.path.join(DOCS, BASE + ".docx")
    md_path = os.path.join(DOCS, BASE + ".md")
    render_docx(docx_path)
    render_md(md_path)
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    print("已生成:", docx_path)
    print("已生成:", md_path)
    print("正文段落/表格块:", len(B), "| document.xml 字符数:", len(xml))
    print("图解读条数:", len(FIGURES) + len(BIZ_FIGURES),
          "| 含 4.2/4.3 标题:", ("4.2" in xml and "4.3" in xml))


if __name__ == "__main__":
    main()
