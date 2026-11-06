# -*- coding: utf-8 -*-
"""
03_analysis.py —— 商业分析模型（5 种）
 1) RFM 八分类（中位数切分）
 2) 同期群留存分析（留存热力图数据）
 3) 帕累托 / ABC 分类（80/20 阈值）
 4) SARIMA 月度 GMV 预测（95% 置信区间 + 回测 MAPE/RMSE）
 5) Apriori 关联规则（mlxtend 优先，纯 pandas 兜底）
输出：outputs/tables/*.csv 与 analysis_metrics.json
"""
import os
import json
import warnings
import numpy as np
import pandas as pd
from config import (DATA_CLEAN, TBL_DIR, FIG_DIR, RANDOM_SEED, setup_cn_font)
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load_data import DATA_RAW
warnings.filterwarnings("ignore")

np.random.seed(RANDOM_SEED)


# ----------------------------- 1. RFM -----------------------------
def rfm_analysis():
    cust = pd.read_csv(os.path.join(DATA_CLEAN, "clean_customers_rfm.csv"))
    r_med = cust["recency_months"].median()
    f_med = cust["frequency"].median()
    m_med = cust["monetary"].median()

    # 中位数切分：R 越低（越近期）越好记为“高”；F、M 越大越好记为“高”。
    # 注：频率中位数恰为 1，若用“>=中位数”会使 F 维度全部判为“高”而退化，
    # 故 F、M 采用“严格大于中位数”记“高”，以确保八分类有效且不遗漏类别。
    cust["R"] = np.where(cust["recency_months"] <= r_med, "高", "低")
    cust["F"] = np.where(cust["frequency"] > f_med, "高", "低")
    cust["M"] = np.where(cust["monetary"] > m_med, "高", "低")

    seg_map = {
        ("高", "高", "高"): "重要价值客户", ("低", "高", "高"): "重要保持客户",
        ("高", "低", "高"): "重要发展客户", ("低", "低", "高"): "重要挽留客户",
        ("高", "高", "低"): "一般价值客户", ("低", "高", "低"): "一般保持客户",
        ("高", "低", "低"): "一般发展客户", ("低", "低", "低"): "一般挽留客户",
    }
    cust["segment"] = cust.apply(
        lambda r: seg_map[(r["R"], r["F"], r["M"])], axis=1)

    seg_summary = cust.groupby("segment").agg(
        count=("customer_unique_id", "count"),
        avg_recency=("recency_months", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
    ).reset_index()
    seg_summary["avg_monetary"] = seg_summary["avg_monetary"].round(2)
    seg_summary = seg_summary.sort_values("count", ascending=False)

    # 客户级抽样（用于气泡图，避免 9.5w 点过密）
    if len(cust) > 3000:
        sample = cust.sample(3000, random_state=RANDOM_SEED)
    else:
        sample = cust
    sample[["customer_unique_id", "recency_months", "frequency",
            "monetary", "segment"]].to_csv(
        os.path.join(TBL_DIR, "rfm_sample.csv"), index=False)
    seg_summary.to_csv(os.path.join(TBL_DIR, "rfm_segments.csv"), index=False)
    cust[["customer_unique_id", "recency_months", "frequency", "monetary",
          "segment"]].to_csv(os.path.join(TBL_DIR, "rfm_full.csv"), index=False)

    metrics = {
        "rfm_median": {"recency": float(r_med), "frequency": float(f_med),
                       "monetary": float(m_med)},
        "rfm_segments": seg_summary.to_dict(orient="records"),
    }
    print("[RFM] 八分类完成，中位数 R/F/M =", r_med, f_med, round(m_med, 2))
    return metrics


# ----------------------------- 2. 同期群留存 -----------------------------
def cohort_analysis():
    oa = pd.read_csv(os.path.join(DATA_CLEAN, "clean_order_agg.csv"))
    cust = pd.read_csv(os.path.join(DATA_CLEAN, "clean_customers_rfm.csv"))
    cust = cust[["customer_unique_id", "cohort_month"]]
    df = oa[["customer_unique_id", "purchase_month"]].merge(
        cust, on="customer_unique_id", how="left")
    purch = pd.PeriodIndex(df["purchase_month"], freq="M")
    coh = pd.PeriodIndex(df["cohort_month"], freq="M")
    df["offset"] = ((purch.year - coh.year) * 12 +
                    (purch.month - coh.month))
    grp = df.groupby(["cohort_month", "offset"])["customer_unique_id"].nunique().reset_index()
    counts = grp.pivot(index="cohort_month", columns="offset", values="customer_unique_id")
    sizes = df.groupby("cohort_month")["customer_unique_id"].nunique()
    retention = counts.divide(sizes, axis=0)
    counts.to_csv(os.path.join(TBL_DIR, "cohort_counts.csv"))
    retention.to_csv(os.path.join(TBL_DIR, "cohort_retention.csv"))
    # 平均次月/第3月留存
    off1 = retention.get(1, pd.Series(dtype=float)).mean()
    off3 = retention.get(3, pd.Series(dtype=float)).mean()
    metrics = {"cohort_avg_retention_m1": float(np.nanmean(off1)),
               "cohort_avg_retention_m3": float(np.nanmean(off3)),
               "n_cohort_months": int(retention.shape[0])}
    print("[同期群] 留存矩阵", retention.shape, "次月留存均值=%.3f" % metrics["cohort_avg_retention_m1"])
    return metrics


# ----------------------------- 3. 帕累托 -----------------------------
def pareto_analysis():
    items = pd.read_csv(os.path.join(DATA_CLEAN, "clean_order_items.csv"))
    cat = items.groupby("product_category_name_english")["price"].sum().sort_values(ascending=False)
    cat_df = cat.reset_index()
    cat_df.columns = ["category", "gmv"]
    total = cat_df["gmv"].sum()
    cat_df["cum_pct"] = cat_df["gmv"].cumsum() / total
    cat_df["rank"] = range(1, len(cat_df) + 1)
    # 80% 阈值对应的品类数
    n80 = int((cat_df["cum_pct"] <= 0.8).sum()) + 1
    cat_df.to_csv(os.path.join(TBL_DIR, "pareto_category.csv"), index=False)
    metrics = {"pareto_total_categories": int(len(cat_df)),
               "pareto_n_for_80pct": n80,
               "pareto_top1_share": float(cat_df.iloc[0]["gmv"] / total),
               "pareto_top_category": str(cat_df.iloc[0]["category"])}
    print("[帕累托] %d 个品类中前 %d 个贡献 80%% GMV" % (len(cat_df), n80))
    return metrics


# ----------------------------- 4. 时间序列预测 -----------------------------
# 数据仅约 22 个完整月（< 2 个完整季节周期=24），SARIMA/Holt-Winters 季节模型欠定、
# 初始化失败。故采用“季节分解 + 线性趋势(OLS)”透明方法：先估计加性季节指数，
# 去季节化后做 OLS 趋势拟合并外推，再叠加季节指数还原，并基于回归标准误给出 95% 置信区间。
def _build_series():
    items = pd.read_csv(os.path.join(DATA_CLEAN, "clean_order_items.csv"))
    ts = items.groupby("purchase_month")["price"].sum().sort_index()
    ts.index = pd.PeriodIndex(ts.index, freq="M")
    ts = ts.asfreq("M").astype(float)
    # 数据治理：剔除首尾不完整/爬坡月（首 3 月与末 1 月样本量过低，GMV 近零），
    # 仅保留完整自然月用于建模，避免趋势/季节估计被极端值误导。
    y = ts.iloc[3:-1]  # 稳定完整月序列
    return y


def _mape_rmse(test, fc):
    test = np.asarray(test, float)
    fc = np.asarray(fc, float)
    mape = float(np.mean(np.abs((test - fc) / test)) * 100)
    rmse = float(np.sqrt(np.mean((test - fc) ** 2)))
    return mape, rmse


def _fit_decomp(ytr, cmtr):
    """加性季节指数 + OLS 趋势。返回系数、残差方差、季节指数。"""
    grand = ytr.mean()
    idx = np.array([(ytr[cmtr == m].mean() if (cmtr == m).any() else 0.0)
                    for m in range(1, 13)]) - grand
    ds = ytr - idx[cmtr - 1]
    n = len(ds)
    t = np.arange(n)
    A = np.vstack([np.ones(n), t]).T
    coef, _, _, _ = np.linalg.lstsq(A, ds, rcond=None)
    resid = ds - A @ coef
    s2 = float(resid @ resid / (n - 2))
    XtX_inv = np.linalg.inv(A.T @ A)
    return coef, s2, idx, XtX_inv, t


def sarima_analysis():
    from scipy import stats
    h = 6
    ys = _build_series()
    y = ys.values
    cm = np.array([p.month for p in ys.index])

    # ---- 回测：剔除末 6 月做测试集 ----
    tr_n = len(y) - h
    ytr, yte = y[:tr_n], y[tr_n:]
    cmtr = cm[:tr_n]
    coef, s2, idx, XtX_inv, ttr = _fit_decomp(ytr, cmtr)
    future_cm = []
    last_period = ys.index[tr_n - 1]
    for k in range(1, h + 1):
        future_cm.append((last_period.month + k - 1) % 12 + 1)
    fc_test, lo_test, hi_test = [], [], []
    for k in range(1, h + 1):
        tf = (tr_n - 1) + k
        x0 = np.array([1.0, float(tf)])
        ds_fc = coef[0] + coef[1] * tf
        se = np.sqrt(s2 * (1.0 + x0 @ XtX_inv @ x0))
        tcrit = stats.t.ppf(0.975, tr_n - 2)
        cm_m = future_cm[k - 1]
        yfc = ds_fc + idx[cm_m - 1]
        fc_test.append(yfc)
        lo_test.append(ds_fc - tcrit * se + idx[cm_m - 1])
        hi_test.append(ds_fc + tcrit * se + idx[cm_m - 1])
    bt_mape, bt_rmse = _mape_rmse(yte, fc_test)

    # ---- 全量重训并预测未来 6 月 ----
    coef2, s2b, idx2, XtX_inv2, t2 = _fit_decomp(y, cm)
    n2 = len(y)
    forecast, lower, upper = [], [], []
    future_periods = pd.period_range(ys.index[-1] + 1, periods=h, freq="M")
    fcm = [p.month for p in future_periods]
    for k in range(1, h + 1):
        tf = (n2 - 1) + k
        x0 = np.array([1.0, float(tf)])
        ds_fc = coef2[0] + coef2[1] * tf
        se = np.sqrt(s2b * (1.0 + x0 @ XtX_inv2 @ x0))
        tcrit = stats.t.ppf(0.975, n2 - 2)
        cm_m = fcm[k - 1]
        forecast.append(ds_fc + idx2[cm_m - 1])
        lower.append(ds_fc - tcrit * se + idx2[cm_m - 1])
        upper.append(ds_fc + tcrit * se + idx2[cm_m - 1])

    fc_df = pd.DataFrame({
        "month": [str(p) for p in ys.index] + [str(p) for p in future_periods],
        "type": ["actual"] * len(ys.index) + ["forecast"] * h,
        "value": np.concatenate([y, forecast]),
        "lower": np.concatenate([np.nan * np.ones(len(ys.index)), lower]),
        "upper": np.concatenate([np.nan * np.ones(len(ys.index)), upper]),
    })
    fc_df.to_csv(os.path.join(TBL_DIR, "sarima_forecast.csv"), index=False)

    metrics = {
        "forecast_engine": "SeasonalDecomp+TrendOLS",
        "note": "Olist 数据不足 2 个完整季节周期，SARIMA/HW 无法稳定初始化，"
                "改用加性季节分解+OLS 趋势外推，保留年季节性并给出 95% 预测区间。",
        "backtest_mape": bt_mape, "backtest_rmse": bt_rmse,
        "n_train_months": int(tr_n), "forecast_horizon": h,
        "forecast_next6": [float(x) for x in forecast],
    }
    print("[预测] 季节分解+趋势模型 | 回测 MAPE=%.2f%% RMSE=%.0f"
          % (bt_mape, bt_rmse))
    return metrics


# ----------------------------- 5. Apriori 关联规则 -----------------------------
def apriori_analysis():
    items = pd.read_csv(os.path.join(DATA_CLEAN, "clean_order_items.csv"))
    items = items[items["product_category_name_english"] != "unknown"]
    # 数据特性：Olist 订单级购物篮 98% 为单品类，订单内跨品类共现极稀疏，
    # 直接做订单级 Apriori 几乎无规则。故将购物篮单元提升为“顾客跨订单品类集合”
    # （同一顾客历史购买过的不同品类），以捕捉真实的跨品类连带关系。
    baskets = items.groupby("customer_unique_id")[
        "product_category_name_english"].apply(lambda s: list(set(s.unique())))
    transactions = [t for t in baskets if len(t) >= 2]

    rules_df = None
    used = "mlxtend"
    # 阈值业务依据：支持度 0.005（约 500 名跨品类顾客共同购买）、
    # 置信度 0.1、lift>1（正相关）过滤伪关联。
    MIN_SUP, MIN_CONF = 0.005, 0.1
    try:
        from mlxtend.preprocessing import TransactionEncoder
        from mlxtend.frequent_patterns import apriori, association_rules
        te = TransactionEncoder()
        te_ary = te.fit(transactions).transform(transactions)
        df = pd.DataFrame(te_ary, columns=te.columns_)
        freq = apriori(df, min_support=MIN_SUP, use_colnames=True, max_len=2)
        rules_df = association_rules(freq, metric="confidence", min_threshold=MIN_CONF)
        rules_df = rules_df[rules_df["lift"] > 1.0].copy()
        rules_df["antecedents"] = rules_df["antecedents"].apply(lambda x: tuple(sorted(x)))
        rules_df["consequents"] = rules_df["consequents"].apply(lambda x: tuple(sorted(x)))
        rules_df = rules_df[["antecedents", "consequents", "support",
                            "confidence", "lift"]].sort_values("lift", ascending=False)
    except ImportError:
        used = "builtin"
        from apriori_lib import apriori_rules
        _, rules_df = apriori_rules(transactions, min_support=MIN_SUP,
                                    min_confidence=MIN_CONF, min_lift=1.0, max_len=2)

    if rules_df is not None and not rules_df.empty:
        rules_df.to_csv(os.path.join(TBL_DIR, "association_rules.csv"), index=False)
    else:
        rules_df = pd.DataFrame(columns=["antecedents", "consequents",
                                         "support", "confidence", "lift"])
        rules_df.to_csv(os.path.join(TBL_DIR, "association_rules.csv"), index=False)

    metrics = {"apriori_engine": used,
               "apriori_unit": "customer_cross_order",
               "apriori_min_support": MIN_SUP,
               "apriori_min_confidence": MIN_CONF,
               "apriori_n_rules": int(len(rules_df)),
               "apriori_top": (rules_df.head(5).to_dict(orient="records")
                               if not rules_df.empty else [])}
    print("[Apriori] 引擎=%s，挖掘规则 %d 条" % (used, len(rules_df)))
    return metrics


def main():
    setup_cn_font()
    all_metrics = {}
    all_metrics.update(rfm_analysis())
    all_metrics.update(cohort_analysis())
    all_metrics.update(pareto_analysis())
    all_metrics.update(sarima_analysis())
    all_metrics.update(apriori_analysis())
    with open(os.path.join(TBL_DIR, "analysis_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, ensure_ascii=False, indent=2, default=str)
    print("=== 分析完成，指标已写入 analysis_metrics.json ===")
    return all_metrics


if __name__ == "__main__":
    main()
