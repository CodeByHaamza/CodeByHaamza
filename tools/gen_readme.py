#!/usr/bin/env python3
"""Génère le profil GitHub : README.md (style PSP, par défaut) et MANGA.md (style manga).

    python tools/gen_readme.py            # utilise data/gh-raw.json
    python tools/gen_readme.py --fetch    # rappelle l'API GitHub d'abord

Les deux pages sont reliées : la PSP qui tourne dans la paume (README) ouvre MANGA.md,
qui démarre sur un zoom à travers son écran ; la steel ball (MANGA.md) ramène au profil.
Le bas de page (stats, contributions 3D, animes) est le même sur les deux.

Bibliothèque standard uniquement : les polices sont déjà converties en tracés dans
data/fonts/ (tools/build_fonts.py, à relancer seulement pour changer de police).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from profilegen import footer, kit, manga, pages, xmb  # noqa: E402


def main() -> None:
    cfg = kit.load_cfg()
    if "--fetch" in sys.argv:
        kit.fetch(os.environ.get("GH_LOGIN", "CodeByHaamza"))
    st = kit.stats(cfg, kit.load_gh())

    # style PSP (README.md)
    xmb.hero(cfg)
    psp_links = xmb.links(cfg)
    xmb.portal(cfg)
    xmb.system(cfg)
    xmb.stack(cfg)
    psp_projects = xmb.projects(cfg, st)
    xmb.games_head(cfg)

    # style manga (MANGA.md)
    manga.hero(cfg)
    manga_links = manga.links(cfg)
    manga.portal(cfg)
    manga.stand(cfg, st)
    manga.equipment(cfg)
    manga.stack(cfg)
    chapters = manga.contents(cfg, st)
    manga.offduty(cfg)

    # commun
    footer.stats_card(cfg, st)

    block = pages.anime_block()
    pages.write_readme(cfg, psp_links, psp_projects, block)
    pages.write_manga(cfg, manga_links, chapters, block)

    # on retire les SVG générés qu'aucune page n'utilise plus
    for f in sorted(kit.OUT.glob("*.svg")):
        if f.name not in kit.WRITTEN:
            f.unlink()
            print(f"supprimé : {f.name}")
    total = sum(f.stat().st_size for f in kit.OUT.glob("*.svg"))
    print(f"{len(kit.WRITTEN)} SVG, {total / 1024:.0f} Ko au total")
    if kit.MISSING:
        print("glyphes absents des polices (relancer tools/build_fonts.py) :", " ".join(sorted(kit.MISSING)))


if __name__ == "__main__":
    main()
