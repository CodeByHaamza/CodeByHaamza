"""Écrit README.md (style PSP, le profil) et MANGA.md (style manga).

Le bloc des animes/mangas, entre les marqueurs anime-favorites, appartient au workflow
anime-box : on le recopie tel quel d'une génération à l'autre.
"""
from __future__ import annotations

import html
import re

from .kit import DATA, MANGA_URL, PROFILE_URL, REPO_URL, ROOT

START, END = "<!-- anime-favorites start -->", "<!-- anime-favorites end -->"
NOTE = "<!-- Généré par tools/gen_readme.py : modifier data/profile.json ou le générateur, pas ce fichier. -->"


def a(s: str) -> str:
    return html.escape(s, quote=True)


def anime_block() -> str:
    for f in (ROOT / "README.md", ROOT / "MANGA.md"):
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
    cells = [linked(f"https://store.steampowered.com/app/{g['appid']}/",
                    f'<img src="https://cdn.cloudflare.steamstatic.com/steam/apps/{g["appid"]}/header.jpg" '
                    f'width="122" alt="{a(g["name"])}">') for g in cfg["games"]]
    return '<div align="center">\n\n' + " ".join(cells) + "\n\n</div>"


def footer(block: str) -> str:
    return "\n".join([
        img("stats.svg", "My GitHub stats for the last twelve months: rank, totals, current and longest streak, "
                         "and languages. Generated in this repo every night."),
        "",
        '<img src="profile-3d-contrib/profile-night-view.svg" width="100%" alt="My contribution year as an animated 3D skyline">',
        "",
        START,
        block,
        END,
        "",
        "<sub>Every panel on this page is an SVG generated in this repo by "
        f'<a href="{REPO_URL}/tree/main/tools"><code>tools/gen_readme.py</code></a> and refreshed every night '
        "by GitHub Actions. Fonts: M PLUS Rounded 1c, Dela Gothic One, Anton (SIL Open Font License). "
        "Logos: Simple Icons (CC0). Steel ball artwork from <i>Steel Ball Run</i> © Hirohiko Araki / Shueisha, "
        "used as a fan homage.</sub>",
        "",
    ])


def write_readme(cfg: dict, links: list, projects: list, block: str) -> None:
    menu = "; ".join(f"{t} ({s})" for t, s in cfg["menu"])
    out = [NOTE, '<div align="center">', "",
           img("psp-hero.svg", f"Handheld console home menu, category Hamza selected: {menu}"), "",
           " ".join(linked(url, img(n, label, height="40")) for n, url, label in links), "",
           "</div>", "",
           linked(MANGA_URL, img("psp-portal.svg", "A hand spins a PSP in its palm, a golden spiral turning behind it "
                                                   "(the Golden Rotation, phi = 1.618). Tap it to open the manga version of this page.")),
           "",
           img("psp-system.svg", "Settings › System Information: my PC and my home server"), "",
           img("psp-stack.svg", "Settings › Stack: " + " / ".join(f"{c['cat']}: " + ", ".join(i[0] for i in c["items"])
                                                                  for c in cfg["stack"])), "",
           img("psp-projects.svg", "Projects › Saved Data Utility"),
           *[linked(url, img(n, f"{label}: {next(p['desc'] for p in cfg['projects'] + cfg['uni'] if p['name'] == label)}"))
             for n, url, label in projects],
           "", img("psp-games.svg", "Game › Favourites"), "", games(cfg), "", footer(block)]
    (ROOT / "README.md").write_text("\n".join(out), encoding="utf-8")


def write_manga(cfg: dict, links: list, chapters: list, block: str) -> None:
    out = [NOTE, '<div align="center">', "",
           img("manga-hero.svg", "Manga chapter title page: CHAPTER 3, HAMZA, THE STUDENT WHO SHIPS"), "",
           " ".join(linked(url, img(n, label, height="44")) for n, url, label in links), "",
           "</div>", "",
           linked(PROFILE_URL, img("manga-portal.svg", "A hand spins a steel ball in its palm, an ink golden spiral "
                                                        "turning behind it. Tap it to go back to the PSP menu version.")),
           "",
           img("manga-stand.svg", "Stand card 「HELLO WORLD」: my GitHub stats graded from A to E"), "",
           img("manga-setup.svg", "Equipment: my PC and my home server"), "",
           img("manga-stack.svg", "Techniques: my stack, one panel per category"), "",
           img("manga-contents.svg", "Contents"),
           *[linked(url, img(n, f"{label}: {next(p['desc'] for p in cfg['projects'] + cfg['uni'] if p['name'] == label)}"))
             for n, url, label in chapters],
           "", img("manga-offduty.svg", "Meanwhile, off duty…"), "", games(cfg), "",
           '<div align="right"><img src="assets/to-be-continued.svg" width="360" alt="To Be Continued"></div>', "",
           footer(block)]
    (ROOT / "MANGA.md").write_text("\n".join(out), encoding="utf-8")
