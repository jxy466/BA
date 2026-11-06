# -*- coding: utf-8 -*-
"""
apriori_lib.py —— 从零实现的 Apriori 关联规则挖掘（纯 pandas / 标准库）。
不依赖 mlxtend，保证无外网环境也能运行；若环境中已安装 mlxtend 也可直接调用。
参考逻辑：频繁项集自底向上生成 + 先验剪枝；规则由频繁项集推导支持度/置信度/提升度。
"""
from itertools import combinations
import pandas as pd
import numpy as np


def _encode(transactions):
    """将事务列表（每项为可迭代对象）编码为整数集合列表，并建立索引。"""
    item_to_id = {}
    for t in transactions:
        for it in t:
            if it not in item_to_id:
                item_to_id[it] = len(item_to_id)
    id_to_item = {v: k for k, v in item_to_id.items()}
    enc = [frozenset(item_to_id[it] for it in t) for t in transactions]
    return enc, id_to_item


def frequent_itemsets(transactions, min_support, max_len=3):
    """返回 DataFrame: itemsets(元组), support(频率)。"""
    enc, id_to_item = _encode(transactions)
    n = len(enc)
    min_count = max(1, int(np.ceil(min_support * n)))

    # 1-项集
    from collections import Counter
    cnt = Counter()
    for t in enc:
        for it in t:
            cnt[it] += 1
    freq1 = {frozenset([k]): c for k, c in cnt.items() if c >= min_count}
    freq = dict(freq1)
    k = 1
    while k < max_len:
        k += 1
        # 候选生成：合并长度为 k-1 且前 k-2 个元素相同的频繁项集
        prev = [tuple(sorted(s)) for s in freq if len(s) == k - 1]
        if not prev:
            break
        candidates = set()
        for i in range(len(prev)):
            for j in range(i + 1, len(prev)):
                a, b = prev[i], prev[j]
                if a[:-1] == b[:-1]:
                    candidates.add(frozenset(a) | frozenset(b))
        # 先验剪枝：所有 k-1 子集必须频繁
        prev_freq = {frozenset(s) for s in prev}
        candidates = [c for c in candidates
                     if all((c - {x}) in prev_freq for x in c)]
        # 计数
        cand_cnt = Counter()
        for t in enc:
            for c in candidates:
                if c.issubset(t):
                    cand_cnt[c] += 1
        new_freq = {c: cand_cnt[c] for c in candidates if cand_cnt[c] >= min_count}
        if not new_freq:
            break
        freq.update(new_freq)

    rows = []
    for s, c in freq.items():
        rows.append({"itemsets": tuple(id_to_item[x] for x in sorted(s)),
                     "support": c / n})
    return pd.DataFrame(rows).sort_values("support", ascending=False).reset_index(drop=True)


def generate_rules(freq_df, min_confidence=0.3, min_lift=1.0):
    """由频繁项集生成规则，返回 DataFrame: antecedents, consequents, support, confidence, lift。"""
    rules = []
    itemsets = {frozenset(r["itemsets"]): r["support"] for _, r in freq_df.iterrows()}
    for itemset, supp in itemsets.items():
        if len(itemset) < 2:
            continue
        for r in range(1, len(itemset)):
            for ant in combinations(sorted(itemset), r):
                ante = frozenset(ant)
                cons = itemset - ante
                if not cons:
                    continue
                sa = itemsets.get(ante, 0.0)
                sc = itemsets.get(cons, 0.0)
                if sa <= 0:
                    continue
                conf = supp / sa
                if conf < min_confidence:
                    continue
                lift = conf / sc if sc > 0 else 0.0
                if lift < min_lift:
                    continue
                rules.append({
                    "antecedents": tuple(sorted(ante)),
                    "consequents": tuple(sorted(cons)),
                    "support": supp,
                    "confidence": conf,
                    "lift": lift,
                })
    df = pd.DataFrame(rules)
    if not df.empty:
        df = df.sort_values("lift", ascending=False).reset_index(drop=True)
    return df


def apriori_rules(transactions, min_support=0.01, min_confidence=0.3,
                 min_lift=1.0, max_len=3):
    """一站式：返回 (频繁项集 DataFrame, 规则 DataFrame)。"""
    freq = frequent_itemsets(transactions, min_support, max_len=max_len)
    rules = generate_rules(freq, min_confidence, min_lift)
    return freq, rules
