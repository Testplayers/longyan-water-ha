#!/usr/bin/env python3
"""重新生成验证码字符模板（ocr.py 依赖）。

网厅验证码样式变了、或识别率下降时，重跑本脚本即可刷新模板：

    pip install pillow
    python tools/gen_captcha_templates.py

原理: 用系统无衬线字体渲染 0-9A-Z，每种字体 × 3 种字号 × 7 个旋转角
      = 每字符 63 个变体，生成归一化位图后写入 JSON，供集成做模板匹配。

输出: custom_components/longyan_water/captcha_templates.json（约 1.9 MB）

注意:
  - 只适用于「彩色字符 + 无干扰线」样式的验证码；
    如果网厅加了干扰线/扭曲，模板匹配会失效，需改用 ddddocr（见 docs/06）
  - 尽量用和网厅验证码接近的字体（默认用 Arial / Helvetica / DejaVu Sans）
"""
from __future__ import annotations

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
SIZE = (14, 20)          # 归一化尺寸 (w, h)，与 ocr.py 的 TMPL_SIZE 一致
FONT_SIZES = (18, 20, 22)
ANGLES = (0, -6, 6, -12, 12, -18, 18)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "custom_components",
                   "longyan_water", "captcha_templates.json")

# 候选字体：跨平台查找，找到几个用几个
CANDIDATES = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\ariblk.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def find_fonts() -> list[str]:
    found = [p for p in CANDIDATES if os.path.exists(p)]
    if not found:
        print("[!] 没找到候选字体，尝试用 PIL 内置位图字体（识别率会明显下降）")
    else:
        print(f"使用字体 {len(found)} 个:")
        for p in found:
            print("   ", p)
    return found


def render_char(ch: str, font_path: str | None, px: int) -> Image.Image:
    """渲染单个字符 → 裁剪笔画外框 → 归一化到 SIZE"""
    img = Image.new("L", (48, 48), 255)
    if font_path:
        font = ImageFont.truetype(font_path, px)
    else:
        font = ImageFont.load_default(size=px)
    ImageDraw.Draw(img).text((6, 6), ch, font=font, fill=0)
    bbox = img.point(lambda p: 255 if p < 128 else 0).getbbox()
    if not bbox:
        bbox = (0, 0, 1, 1)
    return img.crop(bbox).resize(SIZE)


def main() -> int:
    fonts = find_fonts()
    templates: dict[str, list[list[int]]] = {}

    for ch in CHARS:
        variants: list[list[int]] = []
        for fp in (fonts or [None]):
            for px in FONT_SIZES:
                base = render_char(ch, fp, px)
                for ang in ANGLES:
                    rot = base.rotate(ang, expand=True, fillcolor=255)
                    bbox = rot.point(lambda p: 255 if p < 128 else 0).getbbox()
                    if bbox:
                        rot = rot.crop(bbox)
                    rot = rot.resize(SIZE)
                    variants.append([1 if p < 128 else 0 for p in rot.getdata()])
        templates[ch] = variants

    data = {"size": list(SIZE), "templates": templates}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f)

    n_var = len(next(iter(templates.values())))
    print(f"\n✅ 已生成 {len(templates)} 个字符 × {n_var} 个变体")
    print(f"   输出: {OUT}  ({os.path.getsize(OUT) / 1024:.0f} KB)")
    print("\n下一步: python tools/deploy.py  然后重启/重载集成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
