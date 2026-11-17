"""Écrit README.md : les panneaux à deux styles, puis le bas de page commun.

Le bloc des animes/mangas, entre les marqueurs anime-favorites, appartient au workflow
anime-box : on le recopie tel quel d'une génération à l'autre.
"""
from __future__ import annotations

import html
import re

from . import arrow
from .kit import DATA, REPO_URL, ROOT

START, END = "<!-- anime-favorites start -->", "<!-- anime-favorites end -->"
NOTE = "<!-- Généré par tools/gen_readme.py : modifier data/profile.json ou le générateur, pas ce fichier. -->"


def a(s: str) -> str:
    return html.escape(s, quote=True)


def anime_block() -> str:
    f = ROOT / "README.md"
    if f.exists():
        m = re.search(re.escape(START) + r"\n?(.*?)\n?" + re.escape(END), f.read_text(encoding="utf-8"), re.S)
        if m and m.group(1).strip():
            return m.group(1).strip()
    f = DATA / "anime-block.html"
    return f.read_text(encoding="utf-8").strip() if f.exists() else ""


def img(name: str, alt: str, width: str = "100%", height: str = "") -> str:
    size = f'height="{height}"' if height else f'width="{width}"'
    return f'<img src="assets/gen/{name}" {size} alt="{a(alt)}">'


def linked(url: str, inner: str) -> str:
    return f'<a href="{a(url)}">{inner}</a>'


def games(cfg: dict) -> str:
    """Les jeux, sans style de console ni de manga : trois grandes vignettes Steam par ligne."""
    cells = [linked(f"https://store.steampowered.com/app/{g['appid']}/",
                    f'<img src="https://cdn.cloudflare.steamstatic.com/steam/apps/{g["appid"]}/header.jpg" '
                    f'width="32%" alt="{a(g["name"])}">') for g in cfg["games"]]
    return '<h3 align="center">Favourite games</h3>\n\n<p align="center">\n' + "\n".join(cells) + "\n</p>"


def picture(name: str, alt: str) -> str:
    """Une image en deux versions, claire et sombre : le thème GitHub du visiteur choisit."""
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/gen/{name}-dark.svg">'
            f'<img src="assets/gen/{name}-light.svg" width="100%" alt="{a(alt)}"></picture>')


SNAKE = ('<picture><source media="(prefers-color-scheme: dark)" '
         f'srcset="https://raw.githubusercontent.com/CodeByHaamza/CodeByHaamza/output/snake-dark.svg">'
         '<img src="https://raw.githubusercontent.com/CodeByHaamza/CodeByHaamza/output/snake-light.svg" width="100%" '
         'alt="A snake eating my contribution graph"></picture>')


def write_readme(cfg: dict, links: list, projects: list, block: str) -> None:
    descs = {p["name"]: p["desc"] for p in cfg["projects"] + cfg["uni"]}
    menu = "; ".join(f"{t} ({s})" for t, s in cfg["menu"])
    out = [
        NOTE, '<div align="center">', "",
        img("hero.svg", "Every 12 seconds this page switches between two styles: a handheld console menu and a manga "
                        f"chapter. Home menu, category Hamza: {menu}."),
        "",
        " ".join(linked(url, img(n, label, height="44")) for n, url, label in links),
        "", "</div>", "",
        img("portal.svg", "A hand spins a PSP in its palm, a golden spiral turning behind it (the Golden Rotation, phi = 1.618). "
                          "In manga mode, the hand spins a steel ball instead."),
        "",
        img("setup.svg", "My setup: my PC and my home server"), "",
        img("stack.svg", "Stack: " + " / ".join(f"{c['cat']}: " + ", ".join(i[0] for i in c["items"]) for c in cfg["stack"])), "",
        img("grades.svg", "My GitHub year graded from A to E: trophies in console mode, a Stand card 「HELLO WORLD」 in manga mode"), "",
        img("projects.svg", "Projects"),
        *[linked(url, img(n, f"{label}: {descs[label]}")) for n, url, label in projects],
        "", games(cfg), "",
        picture("stats", "My GitHub stats for the last twelve months: rank, totals, streaks and languages"), "",
        picture("calendar", "My contribution calendar for the last year"), "",
        '<h3 align="center">Stand Arrow</h3>', "",
        arrow.readme_block(), "",
        START, block, END, "",
        SNAKE, "",
        "<sub>Every panel on this page is an SVG generated in this repo by "
        f'<a href="{REPO_URL}/tree/main/tools"><code>tools/gen_readme.py</code></a> and refreshed every night by GitHub Actions. '
        "Fonts: M PLUS Rounded 1c, Dela Gothic One, Anton (SIL Open Font License). Logos: Simple Icons (CC0). "
        "Steel ball artwork from <i>Steel Ball Run</i> © Hirohiko Araki / Shueisha, used as a fan homage.</sub>",
        "",
    ]
    (ROOT / "README.md").write_text("\n".join(out), encoding="utf-8")
