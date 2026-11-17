#!/usr/bin/env python3
"""Récupère les images des Stands sur jojowiki.com (JoJo's Bizarre Encyclopedia), en local.

Lit data/stands.json (champ « image » de chaque étape), demande au wiki une miniature de
520 px de large et l'enregistre sous <id de l'étape>.<ext> dans le dossier donné. Ensuite,
tools/build_stands.py les recadre et les compresse dans assets/stands/.

    python tools/fetch_stands.py .cache/stands
    python tools/build_stands.py .cache/stands --extra d4c=<image de D4C>

Bibliothèque standard uniquement. Une pause entre chaque image, pour ménager le wiki.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://jojowiki.com/api.php"
UA = {"User-Agent": "CodeByHaamza-profile-builder/1.0 (personal GitHub profile)"}


def api(**p) -> dict:
    p.update(format="json", formatversion="2")
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(p), headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / ".cache" / "stands")
    out.mkdir(parents=True, exist_ok=True)
    stages = [s for st in json.loads((ROOT / "data" / "stands.json").read_text(encoding="utf-8"))["stands"]
              for s in st["stages"] if s.get("image")]
    urls: dict[str, str] = {}
    for i in range(0, len(stages), 40):
        batch = stages[i:i + 40]
        r = api(action="query", prop="imageinfo", iiprop="url", iiurlwidth=520,
                titles="|".join("File:" + s["image"] for s in batch))
        norm = {n["to"]: n["from"] for n in r["query"].get("normalized", [])}
        for pg in r["query"]["pages"]:
            if "imageinfo" in pg:
                ii = pg["imageinfo"][0]
                urls[norm.get(pg["title"], pg["title"]).split(":", 1)[1]] = ii.get("thumburl") or ii["url"]
        time.sleep(.5)
    missing = []
    for s in stages:
        url = urls.get(s["image"])
        if not url:
            missing.append(s["image"])
            continue
        ext = Path(urllib.parse.urlparse(url).path).suffix.lower() or ".png"
        dst = out / f"{s['id']}{ext}"
        if not dst.exists():
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                dst.write_bytes(r.read())
            time.sleep(.4)
        print(f"{s['id']:26} {dst.stat().st_size // 1024:5} Ko")
    if missing:
        print("introuvables sur le wiki :", ", ".join(missing))


if __name__ == "__main__":
    main()
