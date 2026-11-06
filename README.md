# Olist巴西电商商业数据分析（期末大作业）

基于 Kaggle·Olist Brazilian E-Commerce Public Dataset 的商业数据分析项目：从数据合规获取 → 清洗治理 → 商业模型（RFM/同期群/帕累托/时间序列预测/关联规则） → 可视化模板复现（22张图） → 交互式大屏 → 论文，全部由 Python 技术栈完成。

**严禁爬虫、严禁 Power BI/Tableau、严禁 Excel 截图替代 Python 输出。**

## 一、数据来源与合规声明
- **数据源**：Kaggle · Olist Brazilian E-Commerce Public Dataset
- **获取方式**：Kaggle 官网下载 ZIP 文件（白名单方式，非爬虫）
- **获取日期**：2026-11-04
- **License**：CC BY-NC-SA 4.0
- **规模**：9 张表、约 9.9 万订单、11.3 万订单明细、9.5 万客户、3.3 万商品、3095 卖家

## 二、环境与依赖
- **Python 版本**：Python 3.9+（已在 Anaconda/PyCharm 环境验证）
- **依赖安装**：见 `requirements.txt`。主要依赖包括：`pandas`, `numpy`, `matplotlib`, `seaborn`, `scipy`, `statsmodels`, `mlxtend`, `pyecharts`, `plotly`, `openpyxl`, `streamlit`。

## 三、目录结构
    Olist-Business-Analysis/
    ├── data/
    │   ├── raw/                 # 原始数据（9个CSV，不上传仓库，需自行下载放入）
    │   └── clean/               # 清洗后数据（CSV/JSON/SQLite）
    ├── scripts/
    │   ├── config.py            # 全局配置与路径
    │   ├── load_data.py         # 数据加载
    │   ├── 02_clean.py          # 数据清洗治理
    │   ├── 03_analysis.py       # 5种商业模型计算
    │   ├── 04_visuals.py        # 22张图表生成
    │   └── 05_dashboard.py      # 交互大屏生成
    ├── outputs/
    │   ├── figures/             # 22张高清图表
    │   └── tables/              # 模型结果表 (CSV/JSON)
    ├── docs/                    # 期末大论文、数据来源合规声明
    ├── requirements.txt
    ├── run_all.py               # 一键复现入口
    └── README.md

## 四、一键复现
    # 1. 安装依赖
    pip install -r requirements.txt

    # 2. 一键运行全流程（清洗 -> 建模 -> 可视化 -> 导出独立大屏index.html）
    python run_all.py

## 五、分步执行
    python scripts/02_clean.py        # 清洗治理
    python scripts/03_analysis.py     # RFM/同期群/帕累托/预测/关联规则
    python scripts/04_visuals.py      # 生成 22 张图
    python scripts/05_dashboard.py --html   # 导出独立大屏
    python -m streamlit run scripts/05_dashboard.py  # 启动本地交互大屏

## 六、商业分析模型（5种）
1. **RFM八分类**：中位数切分（R≤中位、F/M严格>中位），2×2×2=8类，配气泡图/柱形图。
2. **同期群留存**：按首购月份分群，计算后续各月复购留存率，热力图呈现。
3. **帕累托ABC**：品类GMV降序累加，定位80%贡献阈值（约18个品类）。
4. **时间序列预测**：数据仅约22个完整月（<2个季节周期），SARIMA无法稳定初始化，故采用加性季节分解+OLS趋势外推，输出点预测+95%置信区间，回测MAPE≈18.1%。
5. **Apriori关联规则**：订单级购物篮98%为单品类，故将购物篮单元提升为“顾客跨订单品类集合”，挖掘支持度≥0.005、置信度≥0.1、lift>1的规则（内置纯 pandas 实现，亦可切换 mlxtend）。

## 七、可视化图表索引
- **模板复现（16种，对照《Excel数据可视化》30模板）**：fig01渐变柱形图、fig02带均值柱形图、fig03圆角柱形图、fig04标注柱形图、fig05层叠柱形图、fig06蝴蝶图、fig07平滑折线图、fig08对比折线图、fig09单值圆环图、fig10水球图、fig11南丁格尔玫瑰图、fig12仪表盘图、fig13柱形折线图、fig14子弹图、fig15滑珠图、fig16玉玦图。
- **业务模型图（6张）**：fig17 RFM气泡图、fig18 RFM八类柱形、fig19同期群留存热力图、fig20帕累托图、fig21预测+95%CI、fig22关联规则提升度热力图。
*(详见 `docs/期末大论文.docx` 附录C图表索引)*

## 八、交互式大屏
- **组件**：时间轴与播放控制器、KPI指标卡组、一句话智能业务速读、月度GMV与订单量趋势图、各州GMV对比图、各品类GMV结构图、同期群留存热力图、各州交付率、全局联动机制。
- **提供两种形态**：
  1. `streamlit run` 实时交互；
  2. `python scripts/05_dashboard.py --html` 导出自包含 `index.html`。

## 九、创新与商业洞察
1. 全 Python 工程化、零 BI 软件、自动化一键复现；
2. 针对数据缺陷（季节样本不足、单品类主导）做出透明、可解释的建模决策；
3. **关键洞察**：Olist 复购率偏低（次月留存约 5%）、GMV 由少数品类驱动（18个品类贡献 80%）、跨品类连带弱（需从互补推荐切入提升客单价）。

## 十、分工说明
本项目为个人独立完成。

## 十一、仓库
**公开仓库链接**：https://github.com/jxy466/BA
