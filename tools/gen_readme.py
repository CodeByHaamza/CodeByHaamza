#!/usr/bin/env python3
"""Génère le profil GitHub (README.md) : chaque panneau contient deux styles, un menu de console
portable et un chapitre de manga, qui alternent tout seuls toutes les 12 secondes.

    python tools/gen_readme.py            # utilise data/gh-raw.json
    python tools/gen_readme.py --fetch    # rappelle l'API GitHub d'abord

Les transitions passent par la steel ball (voir tools/profilegen/dual.py). Le bas de page
(stats, calendrier, contributions 3D, animes) garde un look GitHub neutre et ne bascule pas.

Bibliothèque standard uniquement : les polices sont déjà converties en tracés dans
data/fonts/ (tools/build_fonts.py, à relancer seulement pour changer de police).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from profilegen import arrow, dual, footer, kit, manga, pages, xmb  # noqa: E402
from profilegen.kit import W  # noqa: E402


def main() -> None:
    cfg = kit.load_cfg()
    if "--fetch" in sys.argv:
        kit.fetch(os.environ.get("GH_LOGIN", "CodeByHaamza"))
    st = kit.stats(cfg, kit.load_gh())
    projs = cfg["projects"] + cfg["uni"]

    dual.hero("hero.svg", W, 440, "HAMZA", "Home menu and manga chapter title page, switching every 12 seconds.",
              xmb.hero(cfg, 440), manga.hero(cfg, 440))

    links = []
    for i, l in enumerate(cfg["identity"]["links"]):
        (pw, ph), (mw, mh) = xmb.link_size(l), manga.link_size(l)
        w, h = max(pw, mw) + 6, 44
        name = f"link-{kit.slug(l['label'])}.svg"
        dual.flip(name, w, h, l["label"], xmb.link(l, w, h), manga.link(l, w, h, (-2.5, 1.8, -1.2, 2.4, -1.8)[i % 5]))
        links.append((name, l["url"], l["label"]))

    panels = [
        ("portal.svg", 340, "Golden Rotation", xmb.portal, manga.portal, ()),
        ("setup.svg", max(xmb.system_height(cfg), manga.equipment_height(cfg)), "My setup", xmb.system, manga.equipment, ()),
        ("stack.svg", max(400, manga.stack_height(cfg)), "My stack", xmb.stack, manga.stack, ()),
    ]
    for name, h, title, fp, fm, _ in panels:
        dual.wipe(name, W, h, title, "", fp(cfg, h), fm(cfg, h))
    dual.wipe("grades.svg", W, 440, "My GitHub year, graded", "", xmb.trophies(cfg, st, 440), manga.stand(cfg, st, 440))
    dual.wipe("projects.svg", W, 92, "Projects", "", xmb.projects_head(cfg, 92), manga.contents_head(cfg, 92))
    rows = []
    for i, pr in enumerate(projs):
        name = f"project-{kit.slug(pr['name'])}.svg"
        dual.wipe(name, W, 76, pr["name"], f"{pr['desc']} — {pr['meta']}",
                  xmb.project_row(cfg, st, i, pr, 76), manga.chapter_row(cfg, i, pr, 76))
        rows.append((name, pr["url"], pr["name"]))
    footer.stats_card(cfg, st)
    footer.calendar(st)

    arrow.button()
    arrow.build_cards()

    pages.write_readme(cfg, links, rows, pages.anime_block())

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
