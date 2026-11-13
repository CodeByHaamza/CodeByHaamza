#!/usr/bin/env python3
"""Convertit la police Bangers (Google Fonts, licence OFL) en table de tracés JSON.

Le générateur du README (tools/gen_readme.py) lit data/comic-font.json avec la seule
bibliothèque standard : le workflow quotidien n'a pas besoin de fontTools. Ce script-ci
ne sert qu'à refaire la table, en local :

    pip install fonttools
    python tools/build_comic_font.py
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
URL = "https://github.com/google/fonts/raw/main/ofl/bangers/Bangers-Regular.ttf"
CACHE = ROOT / ".cache" / "Bangers-Regular.ttf"
OUT = ROOT / "data" / "comic-font.json"

# ASCII imprimable, plus les accents et signes dont les textes du README ont besoin.
CHARS = "".join(chr(c) for c in range(32, 127)) + "ÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŒàâäçéèêëîïôöùûüœ·×★…’—–«»"


def main() -> None:
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(URL, headers={"User-Agent": "codebyhaamza-readme"})
        CACHE.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    font = TTFont(str(CACHE))
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    table = {}
    for ch in CHARS:
        name = cmap.get(ord(ch))
        if name is None:
            continue
        pen = SVGPathPen(glyphs, ntos=lambda v: f"{v:.0f}")
        glyphs[name].draw(pen)
        table[ch] = {"d": pen.getCommands(), "adv": glyphs[name].width}
    hhea = font["hhea"]
    OUT.write_text(
        json.dumps(
            {
                "font": "Bangers (Vernon Adams, SIL Open Font License 1.1)",
                "unitsPerEm": font["head"].unitsPerEm,
                "ascender": hhea.ascent,
                "descender": hhea.descent,
                "glyphs": table,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    print(f"{OUT.relative_to(ROOT)} : {len(table)} glyphes, {OUT.stat().st_size // 1024} Ko")


if __name__ == "__main__":
    main()
