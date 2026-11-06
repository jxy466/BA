# -*- coding: utf-8 -*-
"""
06_export_png.py —— 把 04_visuals.py 生成的自包含 HTML 批量截成同名高清 PNG
============================================================================
用途：Word 不支持嵌入交互式 HTML，make_docx.py 按 outputs/figures/figXX_*.png
      同名引用论文插图，因此本脚本负责把 22 个 HTML 渲染为 PNG。

原理：调用本机 Chrome / Edge 的无头截图（--headless --screenshot），
      **不需要 chromedriver / selenium / snapshot-selenium**，也不会卡死。
      每个 HTML 都是单文件自包含（ECharts 与 liquidfill 已内联），离线可渲染。

运行： D:/anaconda/python.exe scripts/06_export_png.py
可选： --only fig05_stacked_quarter,fig10_waterball_satisfaction  只截指定图
       --scale 2          设备像素比（默认 2，输出约 2600×1520，论文足够清晰）
       --budget 8000      虚拟时间预算 ms（水球/动画图建议 ≥6000）

输出： outputs/figures/figXX_*.png （同名覆盖，可直接跑 make_docx.py）
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG_DIR = os.path.join(PROJECT_ROOT, "outputs", "figures")

CHROME_CANDIDATES = [
    os.environ.get("CHROME_BIN"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def find_browser():
    for p in CHROME_CANDIDATES:
        if p and os.path.exists(p):
            return p
    for name in ("chrome", "google-chrome", "msedge", "chromium"):
        p = shutil.which(name)
        if p:
            return p
    return None


def main():
    ap = argparse.ArgumentParser(description="HTML 图表批量转 PNG（无头浏览器）")
    ap.add_argument("--only", default="", help="只截指定图名，逗号分隔")
    ap.add_argument("--scale", type=float, default=2.0, help="设备像素比，默认 2")
    ap.add_argument("--width", type=int, default=1300, help="视口宽，默认 1300")
    ap.add_argument("--height", type=int, default=760, help="视口高，默认 760")
    ap.add_argument("--budget", type=int, default=8000, help="虚拟时间预算 ms")
    args = ap.parse_args()

    browser = find_browser()
    if not browser:
        print("[ERROR] 未找到 Chrome / Edge，请设置环境变量 CHROME_BIN 指向浏览器 exe")
        sys.exit(2)
    print("浏览器:", browser)

    names = {n.strip() for n in args.only.split(",") if n.strip()}
    htmls = [p for p in sorted(glob.glob(os.path.join(FIG_DIR, "fig*.html")))
             if not os.path.basename(p).startswith("_")
             and (not names or os.path.splitext(os.path.basename(p))[0] in names)]
    if not htmls:
        print("[WARN] 没有找到待截图 HTML；请先运行 scripts/04_visuals.py")
        return

    def shoot(png, url, budget):
        cmd = [
            browser, "--headless", "--disable-gpu", "--no-sandbox",
            "--hide-scrollbars", "--disable-dev-shm-usage",
            f"--force-device-scale-factor={args.scale}",
            f"--screenshot={png}",
            f"--window-size={args.width},{args.height}",
            f"--virtual-time-budget={budget}",
            url,
        ]
        subprocess.run(cmd, capture_output=True, timeout=120)
        return os.path.getsize(png) if os.path.exists(png) else 0

    ok, bad = [], []
    for html in htmls:
        base = os.path.splitext(os.path.basename(html))[0]
        png = os.path.join(FIG_DIR, base + ".png")
        url = "file:///" + os.path.abspath(html).replace("\\", "/")
        try:
            try:
                size = shoot(png, url, args.budget)
            except subprocess.TimeoutExpired:
                # 多散点 + ECharts 持续动画的图，在较大的 virtual-time-budget 下偶尔会卡住；
                # 用小预算重截一次即可正常出图（静态截图不依赖动画时长）。
                print(f"[RETRY] {base} 降低虚拟时间预算重截")
                size = shoot(png, url, 1200)
            if size > 20_000:
                ok.append(base)
                print(f"[OK]   {base}.png  {size/1024:.0f} KB")
            else:
                bad.append((base, f"截图过小或缺失 ({size} B)"))
                print(f"[FAIL] {base}.png  截图过小或缺失 ({size} B)")
        except subprocess.TimeoutExpired:
            bad.append((base, "超时"))
            print(f"[FAIL] {base}.png  浏览器超时")
        except Exception as exc:
            bad.append((base, str(exc)))
            print(f"[FAIL] {base}.png  {type(exc).__name__}: {exc}")

    print(f"\n=== 完成：{len(ok)} / {len(htmls)} 张 PNG -> {FIG_DIR} ===")
    if bad:
        print("失败清单：")
        for n, e in bad:
            print("  -", n, e)
        sys.exit(1)
    print("下一步： D:/anaconda/python.exe scripts/make_docx.py  （重新生成期末大论文.docx）")


if __name__ == "__main__":
    main()
