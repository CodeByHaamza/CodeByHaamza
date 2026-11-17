#!/usr/bin/env python3
"""Prépare les images de la Flèche du Stand (à lancer en local, une fois).

Les images sources sont récupérées par tools/fetch_stands.py, sous <id de l'étape>.png ; on
peut aussi en déposer d'autres dans le même dossier, sous ce nom ou sous leur nom d'origine.
Ce script les recadre, les réduit et les compresse dans assets/stands/.

    pip install pillow
    python tools/build_stands.py .cache/stands

Il traite aussi les deux flèches (flèche du Stand, flèche Requiem) si on lui donne leurs
chemins avec --arrow et --requiem.
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "stands"
EXTS = (".png", ".webp", ".jpg", ".jpeg", ".PNG", ".JPG")


def compress(src: Path, dst: Path, box: tuple[int, int], colors: int = 160) -> int:
    im = Image.open(src).convert("RGBA")
    bbox = im.getchannel("A").point(lambda a: 255 if a > 12 else 0).getbbox()
    if bbox:
        im = im.crop(bbox)
    im.thumbnail(box, Image.LANCZOS)
    has_alpha = im.getchannel("A").getextrema()[0] < 250
    q = im.quantize(colors=colors, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE) if has_alpha \
        else im.convert("RGB").quantize(colors=colors, dither=Image.Dither.NONE)
    dst.parent.mkdir(parents=True, exist_ok=True)
    q.save(dst, optimize=True)
    return dst.stat().st_size


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path, help="dossier des images sources (tools/fetch_stands.py)")
    ap.add_argument("--arrow", type=Path, help="image de la flèche du Stand")
    ap.add_argument("--requiem", type=Path, help="image de la flèche Requiem")
    ap.add_argument("--extra", nargs="*", default=[], help="id=chemin pour une étape prise ailleurs (ex. d4c=D4c_sbr69.webp)")
    a = ap.parse_args()

    stages = [s for st in json.loads((ROOT / "data" / "stands.json").read_text(encoding="utf-8"))["stands"] for s in st["stages"]]
    extra = dict(e.split("=", 1) for e in a.extra)

    def norm(name: str) -> str:
        """« Star_platinium_Anime (1).png » et « Fichier:Star platinium Anime.png » → « star platinium anime »."""
        name = urllib.parse.unquote(name).rsplit(".", 1)[0]
        name = re.sub(r"\s*\(\d+\)$", "", name.replace("_", " ")).strip().lower()
        return name

    found = {}
    if a.folder.exists():
        for p in a.folder.iterdir():
            if p.suffix in EXTS:
                found.setdefault(norm(p.name), p)
    missing = []
    for s in stages:
        src = Path(extra[s["id"]]) if s["id"] in extra else (found.get(s["id"]) or found.get(norm(s.get("image", ""))))
        if not src or not src.exists():
            missing.append(f"{s['id']}  ←  {s.get('image', '(image à fournir avec --extra)')}")
            continue
        size = compress(src, OUT / f"{s['id']}.png", (300, 300))
        print(f"{s['id']:26} {size // 1024:4} Ko")
    if a.arrow:
        print("arrow-stand   ", compress(a.arrow, ROOT / "assets" / "arrow-stand.png", (420, 160), 128) // 1024, "Ko")
    if a.requiem:
        print("arrow-requiem ", compress(a.requiem, ROOT / "assets" / "arrow-requiem.png", (220, 220), 128) // 1024, "Ko")
    if missing:
        print(f"\n{len(missing)} image(s) manquante(s) (relancer tools/fetch_stands.py) :")
        print("\n".join("  " + m for m in missing))


if __name__ == "__main__":
    main()
