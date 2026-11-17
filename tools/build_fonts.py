#!/usr/bin/env python3
"""Convertit les polices du profil (Google Fonts, licence OFL) en tables de tracés JSON.

Un SVG affiché via <img> ne charge aucune police : le texte des titres est donc dessiné
en tracés. Le générateur (tools/gen_readme.py) lit data/fonts/*.json avec la seule
bibliothèque standard, le workflow de nuit n'a pas besoin de fontTools. Ce script-ci
ne sert qu'à refaire les tables, en local, quand on change de police ou de jeu de
caractères :

    pip install fonttools
    python tools/build_fonts.py
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"
OUT = ROOT / "data" / "fonts"
GF = "https://github.com/google/fonts/raw/main/ofl/"

LATIN = ("".join(chr(c) for c in range(32, 127)) + "".join(chr(c) for c in range(160, 256))
         + "ŒœŸ’‘“”…—–·•★☆›‹→←↑↓™©®✦φ×≈°△○✕□▶◀")
# Seuls les caractères japonais réellement utilisés par la page manga : un kanji pèse ~2 Ko.
JAPANESE = ("コードバイハムザゴ・ー「」『』！？。、第三話目次破壊力スピード射程距離持続力精密動作性成長性"
            "黄金の回転長方形つづく機材技術作品休日人物紹介")

FONTS = {
    # nom          fichier                                   caractères
    "rounded-bold": ("mplusrounded1c/MPLUSRounded1c-Bold.ttf", LATIN),
    "rounded": ("mplusrounded1c/MPLUSRounded1c-Medium.ttf", LATIN),
    "dela": ("delagothicone/DelaGothicOne-Regular.ttf", LATIN + JAPANESE),
    "anton": ("anton/Anton-Regular.ttf", LATIN),
}


def build(name: str, path: str, chars: str) -> None:
    ttf = CACHE / Path(path).name
    if not ttf.exists():
        CACHE.mkdir(exist_ok=True)
        req = urllib.request.Request(GF + path, headers={"User-Agent": "codebyhaamza-readme"})
        ttf.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    font = TTFont(str(ttf))
    gs, cmap = font.getGlyphSet(), font.getBestCmap()
    table = {}
    for ch in dict.fromkeys(chars):
        g = cmap.get(ord(ch))
        if g is None:
            continue
        pen = SVGPathPen(gs, ntos=lambda v: f"{v:.0f}")
        gs[g].draw(pen)
        table[ch] = {"d": pen.getCommands(), "adv": gs[g].width}
    family = font["name"].getDebugName(1)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{name}.json"
    out.write_text(json.dumps({"font": f"{family} (SIL Open Font License 1.1)", "unitsPerEm": font["head"].unitsPerEm,
                               "glyphs": table}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    missing = "".join(c for c in dict.fromkeys(chars) if c not in table and c.strip())
    print(f"{out.relative_to(ROOT)} : {len(table)} glyphes, {out.stat().st_size // 1024} Ko"
          + (f"  (absents : {missing})" if missing else ""))


if __name__ == "__main__":
    for n, (p, c) in FONTS.items():
        build(n, p, c)
