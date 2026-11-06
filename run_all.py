# -*- coding: utf-8 -*-
"""
run_all.py —— 一键复现入口
按 数据清洗 → 分析模型 → 可视化 → 大屏 的顺序执行全部脚本，
并导出独立 HTML 大屏。每个脚本均使用与当前解释器相同的 Python。
"""
import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(ROOT, "scripts")


def run(name, args=None):
    cmd = [sys.executable, os.path.join(SCRIPTS, name)] + (args or [])
    print("\n>>> 运行", name)
    subprocess.run(cmd, check=True, cwd=ROOT)


def main():
    run("02_clean.py")
    run("03_analysis.py")
    run("04_visuals.py")
    run("05_dashboard.py", ["--html"])
    print("\n=== 全流程完成：图表 outputs/figures/，结果表 outputs/tables/，大屏 index.html ===")


if __name__ == "__main__":
    main()
