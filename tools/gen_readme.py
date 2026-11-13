#!/usr/bin/env python3
"""Génère les SVG du README de profil : un numéro de comics façon Spider-Verse.

Couverture (glitch cyan / magenta), origin story en quatre cases, stack en toile
d'araignée, projets en « Terres » du multivers, stats en méchants vaincus et calendrier
de contributions en trame de points. Tout est auto-contenu : un SVG affiché via <img> ne
charge ni police ni image extérieure. Les titres sont écrits avec la police Bangers
(OFL), convertie une fois pour toutes en tracés dans data/comic-font.json
(tools/build_comic_font.py) : ce script-ci n'utilise que la bibliothèque standard,
comme le workflow quotidien qui le lance.

Usage:
    python tools/gen_readme.py            # utilise data/gh-raw.json
    python tools/gen_readme.py --fetch    # rappelle l'API GitHub d'abord
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "gen"
ICONS = ROOT / "assets" / "icons"
DATA = ROOT / "data"

W = 860  # largeur de rendu d'un README GitHub

# Palette Spider-Verse : encre, nuit, papier, et les quatre couleurs d'impression.
INK = "#0b0a12"
NIGHT = "#15143a"
NIGHT2 = "#1f1d52"
PAPER = "#fff8e7"
MUTED = "#b9b5d6"
MAG = "#ff2e88"
CYAN = "#19e3ff"
RED = "#ff3b3b"
YEL = "#ffd23f"
BLUE = "#4d7cff"
VIOLET = "#a26bff"
ACCENTS = [MAG, CYAN, YEL, RED, BLUE, VIOLET]
SANS = "'Segoe UI','Helvetica Neue',Helvetica,Arial,sans-serif"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ---------------------------------------------------------------- données GitHub

def load_gh() -> dict:
    f = DATA / "gh-raw.json"
    if not f.exists():
        raise SystemExit("data/gh-raw.json absent — lance avec --fetch")
    return json.loads(f.read_text(encoding="utf-8"))["data"]["user"]


GQL = """
query {
  user(login: "%s") {
    login
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions restrictedContributionsCount
      totalPullRequestContributions totalIssueContributions
      totalPullRequestReviewContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes {
        name stargazerCount isPrivate updatedAt
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""


def fetch(login: str) -> None:
    DATA.mkdir(exist_ok=True)
    r = subprocess.run(["gh", "api", "graphql", "-f", f"query={GQL % login}"],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise SystemExit(f"gh a echoue : {r.stderr[:400]}")
    (DATA / "gh-raw.json").write_text(r.stdout, encoding="utf-8")


def rank(commits: int, prs: int, issues: int, reviews: int, stars: int, followers: int) -> str:
    """Rang lettre, même esprit que github-readme-stats : moyenne pondérée de percentiles."""
    def pct(v, med):
        return 1.0 / (1.0 + (med / max(v, 1)) ** 0.5)
    s = (pct(commits, 250) * .30 + pct(prs, 50) * .20 + pct(issues, 25) * .10
         + pct(reviews, 20) * .10 + pct(stars, 50) * .20 + pct(followers, 25) * .10)
    for lim, name in ((.92, "S"), (.82, "A+"), (.70, "A"), (.58, "B+"), (.45, "B"), (.30, "C+")):
        if s >= lim:
            return name
    return "C"


def languages(repos: list[dict], top: int = 6) -> list[tuple[str, float]]:
    tot: dict[str, int] = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            tot[e["node"]["name"]] = tot.get(e["node"]["name"], 0) + e["size"]
    allsum = sum(tot.values()) or 1
    ranked = sorted(tot.items(), key=lambda kv: -kv[1])
    out = [(n, v * 100.0 / allsum) for n, v in ranked[:top]]
    rest = sum(v for _, v in ranked[top:]) * 100.0 / allsum
    if rest > 0.4:
        out.append(("Other", rest))
    return out


def streaks(weeks: list[dict]) -> tuple[int, int]:
    """(série en cours, plus longue série). Un dernier jour vide ne casse pas la série."""
    days = [d for wk in weeks for d in wk["contributionDays"]]
    best = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] > 0 else 0
        best = max(best, run)
    cur = 0
    for d in reversed(days):
        if d["contributionCount"] > 0:
            cur += 1
        elif cur == 0:
            continue
        else:
            break
    return cur, best


# ---------------------------------------------------------------- briques

_ICON_CACHE: dict[str, str] = {}


def icon_path(slug: str) -> str | None:
    """Contenu du <path> d'un logo simple-icons, en viewBox 24."""
    if slug in _ICON_CACHE:
        return _ICON_CACHE[slug]
    f = ICONS / f"{slug}.svg"
    if not f.exists():
        return None
    ds = re.findall(r'<path[^>]*\sd="([^"]+)"', f.read_text(encoding="utf-8"))
    if not ds:
        return None
    _ICON_CACHE[slug] = " ".join(ds)
    return _ICON_CACHE[slug]


def icon(slug: str | None, cx: float, cy: float, s: float, fill: str) -> str:
    """Un logo de côté s, centré en (cx, cy)."""
    x, y = cx - s / 2, cy - s / 2
    if slug == "__pygame":  # absent de simple-icons : triangle de lecture
        return (f'<path fill="{fill}" d="M{x + s * .2:.1f} {y + s * .12:.1f}L{x + s * .9:.1f} {cy:.1f}'
                f'L{x + s * .2:.1f} {y + s * .88:.1f}Z"/>')
    d = icon_path(slug) if slug else None
    if not d:
        return ""
    return f'<g fill="{fill}" transform="translate({x:.1f},{y:.1f}) scale({s / 24:.4f})"><path d="{d}"/></g>'


class Letters:
    """Texte en police comics (Bangers), en tracés. Chaque glyphe est défini une fois
    dans <defs> et réutilisé avec <use> : un titre ne pèse que ses lettres distinctes."""

    def __init__(self, prefix: str):
        f = json.loads((DATA / "comic-font.json").read_text(encoding="utf-8"))
        self.upm = f["unitsPerEm"]
        self.g = f["glyphs"]
        self.p = prefix
        self.used: set[str] = set()

    def _glyph(self, ch: str) -> tuple[str, dict]:
        for c in (ch, ch.upper(), " "):
            if c in self.g:
                return c, self.g[c]
        return " ", self.g[" "]

    def width(self, s: str, size: float, track: float = 0) -> float:
        return sum(self._glyph(c)[1]["adv"] for c in s) * size / self.upm + track * max(len(s) - 1, 0)

    def text(self, s: str, x: float, y: float, size: float, fill: str, stroke: str | None = None,
             sw: float = 0, anchor: str = "start", track: float = 0, cls: str = "", style: str = "") -> str:
        k = size / self.upm
        w = self.width(s, size, track)
        x -= w / 2 if anchor == "middle" else w if anchor == "end" else 0
        uses, cx = [], 0.0
        for ch in s:
            key, gl = self._glyph(ch)
            if gl["d"]:
                self.used.add(key)
                uses.append(f'<use href="#{self.p}{ord(key):x}" x="{cx:.0f}"/>')
            cx += gl["adv"] + track / k
        st = (f' stroke="{stroke}" stroke-width="{sw / k:.0f}" stroke-linejoin="round" paint-order="stroke"'
              if stroke else "")
        c = f' class="{cls}"' if cls else ""
        sty = f' style="{style}"' if style else ""
        return (f'<g{c}{sty} transform="translate({x:.1f} {y:.1f}) scale({k:.5f} {-k:.5f})" fill="{fill}"{st}>'
                + "".join(uses) + "</g>")

    def defs(self) -> str:
        return "".join(f'<path id="{self.p}{ord(c):x}" d="{self.g[c]["d"]}"/>' for c in sorted(self.used))


def svg_open(w: float, h: float, title: str, desc: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" '
            f'height="{h:.0f}" role="img" aria-labelledby="t d"><title id="t">{esc(title)}</title>'
            f'<desc id="d">{esc(desc)}</desc>')


def halftone(pid: str, color: str, step: float = 9, r: float = 2.0, angle: float = 45) -> str:
    return (f'<pattern id="{pid}" width="{step}" height="{step}" patternUnits="userSpaceOnUse" '
            f'patternTransform="rotate({angle})"><circle cx="{step / 2}" cy="{step / 2}" r="{r}" fill="{color}"/></pattern>')


def fade_mask(mid: str, x1: float, y1: float, x2: float, y2: float, w: float, h: float) -> str:
    """Masque qui fait apparaître une trame d'un coin à l'autre."""
    return (f'<linearGradient id="{mid}g" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
            f'<stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>'
            f'</linearGradient><mask id="{mid}"><rect width="{w}" height="{h}" fill="url(#{mid}g)"/></mask>')


def wrap(text: str, max_chars: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > max_chars:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    return lines


def txt(x: float, y: float, s: str, fill: str = PAPER, size: float = 13, weight: int = 600,
        anchor: str = "start", italic: bool = False, extra: str = "") -> str:
    it = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-family="{SANS}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}"{it}{extra}>{esc(s)}</text>')


def caption(x: float, y: float, w: float, h: float, rot: float = 0, fill: str = YEL) -> str:
    """Encadré de narration (le rectangle jaune des comics)."""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" stroke="{INK}" '
            f'stroke-width="3" transform="rotate({rot} {x + w / 2:.1f} {y + h / 2:.1f})"/>')


def spider(cx: float, cy: float, s: float, fill: str = INK) -> str:
    """Une araignée stylisée (pas un logo existant) : deux ovales et huit pattes."""
    legs = []
    for side in (-1, 1):
        for dy, kx, ky, tx, ty in ((-6, 15, -16, 21, -26), (-2, 18, -8, 27, -8), (2, 18, 6, 26, 14), (6, 14, 14, 18, 28)):
            legs.append(f"M{cx + side * 3 * s:.1f} {cy + dy * s:.1f}Q{cx + side * kx * s:.1f} {cy + ky * s:.1f} "
                        f"{cx + side * tx * s:.1f} {cy + ty * s:.1f}")
    return (f'<g fill="{fill}"><path d="{" ".join(legs)}" fill="none" stroke="{fill}" stroke-width="{2.4 * s:.2f}" '
            f'stroke-linecap="round"/><ellipse cx="{cx}" cy="{cy - 7 * s:.1f}" rx="{4.5 * s:.1f}" ry="{4.2 * s:.1f}"/>'
            f'<ellipse cx="{cx}" cy="{cy + 6 * s:.1f}" rx="{7 * s:.1f}" ry="{10 * s:.1f}"/></g>')


def burst(cx: float, cy: float, r: float, spikes: int = 14, inner: float = .72, rot: float = 0) -> str:
    pts = []
    for i in range(spikes * 2):
        rr = r if i % 2 == 0 else r * inner
        a = math.radians(rot + i * 180 / spikes)
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
    return " ".join(pts)


def web_corner(ox: float, oy: float, rmax: float, a0: float, a1: float, spokes: int, rings: int,
               color: str = PAPER, op: float = .22) -> str:
    """Toile d'araignée accrochée dans un coin : rayons + fils qui pendent entre eux."""
    angs = [math.radians(a0 + (a1 - a0) * i / (spokes - 1)) for i in range(spokes)]
    d = [f"M{ox} {oy}L{ox + rmax * math.cos(a):.1f} {oy + rmax * math.sin(a):.1f}" for a in angs]
    for k in range(1, rings + 1):
        r = rmax * k / (rings + .4)
        for a, b in zip(angs, angs[1:]):
            p1 = (ox + r * math.cos(a), oy + r * math.sin(a))
            p2 = (ox + r * math.cos(b), oy + r * math.sin(b))
            m = ((a + b) / 2)
            c = (ox + r * .86 * math.cos(m), oy + r * .86 * math.sin(m))
            d.append(f"M{p1[0]:.1f} {p1[1]:.1f}Q{c[0]:.1f} {c[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}")
    return f'<path d="{"".join(d)}" fill="none" stroke="{color}" stroke-width="1.4" opacity="{op}"/>'


def page(w: float, h: float) -> str:
    """Fond d'une planche : nuit, trame discrète, bord d'encre. Lisible en thème clair comme sombre."""
    return (f'<defs>{halftone("pg", NIGHT2, 7, 1.3, 30)}</defs>'
            f'<rect x="1.5" y="1.5" width="{w - 3:.0f}" height="{h - 3:.0f}" rx="16" fill="#100f2a" stroke="{INK}" stroke-width="3"/>'
            f'<rect x="1.5" y="1.5" width="{w - 3:.0f}" height="{h - 3:.0f}" rx="16" fill="url(#pg)" opacity=".7"/>')


REDUCE = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"


# ---------------------------------------------------------------- 1. couverture

def gen_cover(cfg: dict) -> None:
    H = 450
    L = Letters("c")
    s = [svg_open(W, H, "The Amazing Hamza, issue 3",
                  "Couverture de comics façon Spider-Verse : le titre HAMZA en lettres de BD qui glitchent en cyan "
                  "et magenta, une toile d'araignée dans le coin, une araignée qui se balance au bout de son fil "
                  "avec un THWIP!, et l'encadré : étudiant en informatique en alternance, un projet tous les quinze jours.")]
    title_y, size = 318, 178
    s.append("<style>"
             ".gc{animation:gc 3.4s steps(1) infinite}.gm{animation:gm 3.4s steps(1) infinite}"
             "@keyframes gc{0%,44%{transform:translate(-7px,1px)}46%{transform:translate(-19px,4px)}"
             "48%{transform:translate(5px,-3px)}50%,90%{transform:translate(-7px,1px)}92%{transform:translate(-12px,-2px)}94%{transform:translate(-7px,1px)}}"
             "@keyframes gm{0%,44%{transform:translate(7px,-1px)}46%{transform:translate(17px,-4px)}"
             "48%{transform:translate(-6px,3px)}50%,90%{transform:translate(7px,-1px)}92%{transform:translate(13px,2px)}94%{transform:translate(7px,-1px)}}"
             ".slice{opacity:0;animation:slice 3.4s steps(1) infinite}"
             "@keyframes slice{0%,45%{opacity:0;transform:none}46%{opacity:1;transform:translate(22px,0)}"
             "48%{opacity:1;transform:translate(-16px,0)}50%,100%{opacity:0;transform:none}}"
             ".swing{transform-origin:745px 0;animation:swing 3.2s ease-in-out infinite}"
             "@keyframes swing{0%,100%{transform:rotate(9deg)}50%{transform:rotate(-9deg)}}"
             ".thwip{transform-box:fill-box;transform-origin:center;animation:thwip 3.2s ease-out infinite}"
             "@keyframes thwip{0%,55%{opacity:0;transform:scale(.3) rotate(-12deg)}62%{opacity:1;transform:scale(1.15) rotate(-6deg)}"
             "70%,88%{opacity:1;transform:scale(1) rotate(-6deg)}96%,100%{opacity:0;transform:scale(1) rotate(-6deg)}}"
             ".dots{animation:dots 6s ease-in-out infinite alternate}@keyframes dots{from{opacity:.55}to{opacity:.95}}"
             + REDUCE + "</style>")
    defs = ['<radialGradient id="cg1" cx="80%" cy="15%" r="70%"><stop offset="0" stop-color="#ff2e88" stop-opacity=".55"/>'
            '<stop offset="1" stop-color="#ff2e88" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="cg2" cx="10%" cy="95%" r="60%"><stop offset="0" stop-color="#19e3ff" stop-opacity=".4"/>'
            '<stop offset="1" stop-color="#19e3ff" stop-opacity="0"/></radialGradient>',
            halftone("cd1", MAG, 10, 2.3), halftone("cd2", CYAN, 9, 1.7, 30),
            fade_mask("cm1", 1, 1, .35, .2, W, H), fade_mask("cm2", 0, 1, .5, .4, W, H),
            f'<clipPath id="card"><rect width="{W}" height="{H}" rx="16"/></clipPath>',
            f'<clipPath id="band"><rect x="0" y="{title_y - 118}" width="{W}" height="34"/></clipPath>']
    body = [f'<g clip-path="url(#card)"><rect width="{W}" height="{H}" fill="{NIGHT}"/>',
            f'<rect width="{W}" height="{H}" fill="url(#cg1)"/><rect width="{W}" height="{H}" fill="url(#cg2)"/>',
            f'<g class="dots"><rect width="{W}" height="{H}" fill="url(#cd1)" mask="url(#cm1)"/>'
            f'<rect width="{W}" height="{H}" fill="url(#cd2)" mask="url(#cm2)"/></g>']
    # Lignes de vitesse depuis le titre.
    rays = []
    for i in range(36):
        a = math.radians(i * 10 + 3)
        r1, r2 = 330, 900
        rays.append(f"M{430 + r1 * math.cos(a):.0f} {250 + r1 * .55 * math.sin(a):.0f}L{430 + r2 * math.cos(a):.0f} {250 + r2 * .55 * math.sin(a):.0f}")
    body.append(f'<path d="{"".join(rays)}" stroke="{PAPER}" stroke-width="2" opacity=".07"/>')
    body.append(web_corner(0, 0, 250, 0, 90, 7, 4))
    # Bandeau de numéro, en haut à gauche.
    body.append(f'<g transform="rotate(-4 92 58)"><rect x="24" y="22" width="136" height="74" fill="{RED}" stroke="{INK}" stroke-width="4"/>'
                + L.text("ISSUE", 40, 52, 22, PAPER) + L.text("#3", 104, 86, 46, YEL, INK, 5) + "</g>")
    body.append(txt(30, 120, "BUT INFO · 2026", PAPER, 12, 800, extra=' letter-spacing="2"'))
    # « Code barre » de couverture, en bas à droite.
    bars = "".join(f'<rect x="{770 + i * 3.4:.1f}" y="372" width="{1.2 + (i * 7 % 5) * .45:.2f}" height="44" fill="{INK}"/>' for i in range(18))
    body.append(f'<rect x="760" y="362" width="76" height="72" fill="{PAPER}" stroke="{INK}" stroke-width="3"/>{bars}'
                + txt(798, 429, "FREE · 0,00 €", INK, 8.5, 800, "middle"))
    # Titre : « THE AMAZING », puis HAMZA en trois couches décalées qui glitchent.
    body.append(L.text("THE AMAZING", 430, title_y - 150, 38, YEL, INK, 7, "middle", 3))
    shadow = L.text("HAMZA", 438, title_y + 9, size, INK, anchor="middle", track=6)
    cyan = L.text("HAMZA", 430, title_y, size, CYAN, anchor="middle", track=6)
    mag = L.text("HAMZA", 430, title_y, size, MAG, anchor="middle", track=6)
    main = L.text("HAMZA", 430, title_y, size, PAPER, INK, 10, "middle", 6)
    body.append(shadow + f'<g class="gc" opacity=".85">{cyan}</g><g class="gm" opacity=".85">{mag}</g>{main}')
    body.append(f'<g class="slice" clip-path="url(#band)">{L.text("HAMZA", 430, title_y, size, PAPER, INK, 10, "middle", 6)}</g>')
    # L'araignée qui se balance au bout de son fil, à droite.
    body.append(f'<g class="swing"><line x1="745" y1="0" x2="745" y2="150" stroke="{PAPER}" stroke-width="2" opacity=".8"/>'
                f'<g transform="translate(745 172)">{spider(0, 0, 1.6, INK)}</g></g>')
    body.append(f'<g class="thwip">{L.text("THWIP!", 640, 128, 40, YEL, INK, 6, "middle")}</g>')
    # Encadré de narration.
    tag = "CS student · work-study · France"
    body.append(caption(30, 352, 470, 70, -1.5))
    kicker = txt(44, 378, "IN THIS ISSUE", INK, 11, 900, extra=' letter-spacing="3"')
    body.append(f'<g transform="rotate(-1.5 265 387)">{kicker}'
                f'{txt(44, 402, tag.upper(), INK, 15, 900)}{txt(44, 416, "Ships a project every two weeks. Starts too many of them.", INK, 11.5, 600)}</g>')
    body.append("</g>")
    s.append("<defs>" + "".join(defs) + L.defs() + "</defs>")
    s.extend(body)
    s.append(f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="15" fill="none" stroke="{INK}" stroke-width="3"/></svg>')
    (OUT / "cover.svg").write_text("".join(s), encoding="utf-8")


# ---------------------------------------------------------------- 2. liens en autocollants

def gen_links(cfg: dict) -> None:
    for i, link in enumerate(cfg["identity"]["links"]):
        L = Letters("l")
        label = link["label"].upper()
        color = ACCENTS[i % len(ACCENTS)]
        ic = 22 if link.get("icon") else 0
        tw = L.width(label, 22, 1)
        w, h = tw + ic + 34 + (8 if ic else 0), 46
        body = [f'<g transform="rotate({(-2, 1.5, -1, 2, -1.5)[i % 5]} {w / 2:.0f} {h / 2:.0f})">'
                f'<rect x="5" y="6" width="{w - 10:.0f}" height="{h - 12}" rx="6" fill="{INK}" transform="translate(3 3)"/>'
                f'<rect x="5" y="6" width="{w - 10:.0f}" height="{h - 12}" rx="6" fill="{color}" stroke="{INK}" stroke-width="3"/>']
        x = 18
        if ic:
            body.append(icon(link["icon"], x + 10, h / 2, 18, INK))
            x += ic + 8
        body.append(L.text(label, x, h / 2 + 8, 22, INK, track=1) + "</g>")
        s = [svg_open(w, h, link["label"], f"Lien : {link['label']}"), f"<defs>{L.defs()}</defs>", *body, "</svg>"]
        name = re.sub(r"[^a-z0-9]+", "-", link["label"].lower()).strip("-")
        (OUT / f"link-{name}.svg").write_text("".join(s), encoding="utf-8")


# ---------------------------------------------------------------- 3. origin story

def gen_origin(cfg: dict) -> None:
    L = Letters("o")
    pw, ph, gut, top = (W - 3 * 14) / 2, 268, 14, 74
    H = top + ph * 2 + gut + 16
    pc = cfg["machines"][0]["specs"]
    cpu = next((v for k, v in pc if k == "cpu"), "").split("(")[0].strip()
    gpu = next((v for k, v in pc if k == "gpu"), "").split("·")[0].strip()
    panels = [
        ("MIDDLE SCHOOL", CYAN, ["Scratch is where I met code.", "I started a coding club, and we", "shipped Asteroids: drag-and-drop", "blocks, collision maths by hand,", "a room full of first-timers."], "asteroids"),
        ("8 YEARS OF SAVING", MAG, ["We picked every part ourselves,", "then built the PC by hand.", "The assembly took an afternoon.", "The waiting took most of my teens.", f"{cpu} · {gpu}"], "pc"),
        ("TODAY", YEL, ["Third-year CS student (BUT),", "work-study, France. I build small", "complete things: a daily game, a", "gesture engine, a fighting game,", "PSP-era Megaten fan translations."], "laptop"),
        ("SECRET IDENTITY", RED, ["Spider-Man is my guy. Spider-Verse", "is my favourite film, full stop.", "~300 manga volumes on the wall,", "and more Spider-Man Lego sets", "than a student should admit to."], "shelf"),
    ]
    css = ["<style>",
           ".spin{transform-box:fill-box;transform-origin:center;animation:spin 1.1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}",
           ".roll{transform-box:fill-box;transform-origin:center;animation:spin 9s linear infinite}",
           ".pew{animation:pew 1.6s linear infinite}@keyframes pew{0%{transform:translate(0,0);opacity:1}80%{opacity:1}100%{transform:translate(70px,-46px);opacity:0}}",
           ".tick{opacity:0;animation:tick 4.5s ease-out infinite}@keyframes tick{0%,10%{opacity:0;transform:translateX(-6px)}20%,85%{opacity:1;transform:none}100%{opacity:0}}",
           ".rgb{animation:rgb 4s linear infinite}@keyframes rgb{0%{stop-color:#ff2e88}33%{stop-color:#19e3ff}66%{stop-color:#ffd23f}100%{stop-color:#ff2e88}}",
           ".bob{animation:bob 2.4s ease-in-out infinite}@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}",
           REDUCE, "</style>"]
    defs = [halftone(f"od{i}", c, 8, 1.6) for i, c in enumerate(ACCENTS[:4])]
    defs.append('<linearGradient id="rgbg" x1="0" x2="1"><stop offset="0" class="rgb" stop-color="#ff2e88"/>'
                '<stop offset="1" stop-color="#19e3ff"/></linearGradient>')
    body = [L.text("ORIGIN STORY", 22, 52, 46, YEL, INK, 7, track=2), txt(300, 50, "the short version", MUTED, 13, 600, italic=True)]
    for i, (cap, color, lines, art) in enumerate(panels):
        x = 14 + (i % 2) * (pw + gut)
        y = top + (i // 2) * (ph + gut)
        defs.append(fade_mask(f"om{i}", 1, 0, .3, 1, pw, ph))
        body.append(f'<g transform="translate({x:.1f} {y:.1f})">'
                    f'<rect width="{pw:.1f}" height="{ph}" fill="{NIGHT}" stroke="{INK}" stroke-width="5"/>'
                    f'<rect width="{pw:.1f}" height="{ph}" fill="url(#od{i})" mask="url(#om{i})" opacity=".45"/>')
        cw = L.width(cap, 22, 1) + 26
        body.append(caption(10, 10, cw, 34, -1.2) + f'<g transform="rotate(-1.2 {10 + cw / 2:.0f} 27)">{L.text(cap, 23, 36, 22, INK, track=1)}</g>')
        for j, line in enumerate(lines):
            last = j == len(lines) - 1 and art == "pc"
            body.append(txt(18, 76 + j * 21, line, color if last else PAPER, 13.2 if not last else 12, 700 if last else 600))
        body.append(panel_art(art, pw - 98, ph / 2 + 12, color, L))
        body.append("</g>")
    s = [svg_open(W, H, "Origin story",
                  "Quatre cases de BD. Collège : Scratch et un club de code qui sort un Asteroids. Huit ans "
                  "d'économies : le PC monté à la main. Aujourd'hui : BUT informatique en alternance, des petits projets "
                  "complets. Identité secrète : Spider-Man, Spider-Verse, 300 mangas et trop de Lego Spider-Man."),
         *css, "<defs>" + "".join(defs) + L.defs() + "</defs>", page(W, H), *body, "</svg>"]
    (OUT / "origin.svg").write_text("".join(s), encoding="utf-8")


def panel_art(kind: str, cx: float, cy: float, color: str, L: Letters) -> str:
    """L'illustration à droite de chaque case, en formes simples."""
    if kind == "asteroids":
        rocks = []
        for k, (dx, dy, r) in enumerate(((-30, -62, 22), (48, -30, 15), (18, 52, 26))):
            pts = " ".join(f"{dx + r * (0.75 + 0.25 * ((j * 7 + k) % 3) / 2) * math.cos(math.radians(j * 45)):.1f},"
                           f"{dy + r * (0.75 + 0.25 * ((j * 5 + k) % 3) / 2) * math.sin(math.radians(j * 45)):.1f}" for j in range(8))
            rocks.append(f'<g transform="translate({cx:.1f} {cy:.1f})"><polygon class="roll" points="{pts}" fill="none" stroke="{PAPER}" stroke-width="3"/></g>')
        ship = (f'<g transform="translate({cx - 50:.1f} {cy + 40:.1f}) rotate(-35)"><polygon points="0,-16 11,13 0,7 -11,13" fill="{color}" stroke="{INK}" stroke-width="2"/></g>'
                f'<g class="pew"><circle cx="{cx - 38:.1f}" cy="{cy + 22:.1f}" r="3.5" fill="{YEL}"/></g>')
        return "".join(rocks) + ship + L.text("PEW!", cx - 64, cy - 48, 26, YEL, INK, 4)
    if kind == "pc":
        fans = "".join(f'<g class="spin"><circle cx="{cx}" cy="{cy - 50 + k * 40:.0f}" r="15" fill="{INK}" stroke="url(#rgbg)" stroke-width="3"/>'
                       f'<path d="M{cx} {cy - 50 + k * 40 - 12:.0f}L{cx} {cy - 50 + k * 40 + 12:.0f}M{cx - 12} {cy - 50 + k * 40:.0f}L{cx + 12} {cy - 50 + k * 40:.0f}" '
                       f'stroke="{PAPER}" stroke-width="3" stroke-linecap="round"/></g>' for k in range(3))
        return (f'<rect x="{cx - 38}" y="{cy - 80}" width="76" height="150" rx="6" fill="{NIGHT2}" stroke="{PAPER}" stroke-width="3"/>'
                f'<rect x="{cx - 30}" y="{cy - 72}" width="60" height="134" rx="4" fill="none" stroke="url(#rgbg)" stroke-width="2.5"/>'
                + fans + L.text("8 YEARS", cx, cy + 92, 18, color, INK, 3, "middle"))
    if kind == "laptop":
        checks = "".join(f'<g class="tick" style="animation-delay:{k * .5:.1f}s">{txt(cx - 46, cy + 50 + k * 16, "✓ " + w, color, 12, 800)}</g>'
                         for k, w in enumerate(("docker", "tests", "changelog")))
        return (f'<g class="bob"><rect x="{cx - 56}" y="{cy - 74}" width="112" height="72" rx="6" fill="{NIGHT2}" stroke="{PAPER}" stroke-width="3"/>'
                f'<path d="M{cx - 70} {cy + 4}H{cx + 70}L{cx + 60} {cy - 2}H{cx - 60}Z" fill="{PAPER}"/>'
                + L.text("</>", cx, cy - 26, 30, color, INK, 3, "middle") + "</g>" + checks)
    # Étagère : un gros emblème d'araignée et une pile de tomes.
    spines = "".join(f'<rect x="{cx - 52 + k * 13}" y="{cy + 18 - (k % 3) * 6}" width="11" height="{56 + (k % 3) * 6}" '
                     f'fill="{ACCENTS[k % 6]}" stroke="{INK}" stroke-width="2"/>' for k in range(8))
    return f'<g class="bob">{spider(cx, cy - 46, 1.9, PAPER)}</g>' + spines + L.text("~300 VOLS", cx, cy + 102, 16, YEL, INK, 3, "middle")


# ---------------------------------------------------------------- 4. spider-sense (stack)

def gen_spider_sense(cfg: dict) -> None:
    L = Letters("s")
    H = 520
    cx, cy, sx = 430, 285, 1.62
    cats = cfg["stack"]
    n = len(cats)

    def P(r: float, a: float) -> tuple[float, float]:
        return cx + r * sx * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))

    spokes = [-90 + 360 * k / n for k in range(n)]
    web = []
    for a in spokes:
        x, y = P(232, a)
        web.append(f"M{cx} {cy}L{x:.1f} {y:.1f}")
    for r in (52, 98, 148, 200):
        for a, b in zip(spokes, spokes[1:] + spokes[:1]):
            (x1, y1), (x2, y2), (qx, qy) = P(r, a), P(r, b), P(r * .9, (a + b) / 2 if b > a else (a + b + 360) / 2)
            web.append(f"M{x1:.1f} {y1:.1f}Q{qx:.1f} {qy:.1f} {x2:.1f} {y2:.1f}")
    body = [L.text("SPIDER-SENSE", 22, 52, 46, YEL, INK, 7, track=2), txt(318, 50, "what tingles when I build", MUTED, 13, 600, italic=True),
            f'<path d="{"".join(web)}" fill="none" stroke="{PAPER}" stroke-width="1.5" opacity=".25"/>']
    # Ondes du sens d'araignée, depuis le centre.
    for k in range(3):
        body.append(f'<ellipse class="ripple" style="animation-delay:{k * 1.2:.1f}s" cx="{cx}" cy="{cy}" rx="{60 * sx:.0f}" ry="60" '
                    f'fill="none" stroke="{MAG}" stroke-width="2"/>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="44" fill="{INK}" stroke="{YEL}" stroke-width="4"/>{spider(cx, cy + 2, 1.15, PAPER)}')
    for k, cat in enumerate(cats):
        mid = spokes[k] + 180 / n
        color = ACCENTS[k % len(ACCENTS)]
        items = cat["items"]
        inner, outer = items[:2], items[2:]
        placed = [(98 + 25, mid + (j - .5) * 22, it) for j, it in enumerate(inner)]
        span = 40 if len(outer) > 3 else 30
        for j, it in enumerate(outer):
            t = (j / (len(outer) - 1) - .5) if len(outer) > 1 else 0
            placed.append((175, mid + t * span, it))
        for r, a, (label, slug) in placed:
            x, y = P(r, a)
            body.append(f'<g class="pop" style="animation-delay:{(k * 6 + len(body) % 6) * .05:.2f}s">'
                        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="17" fill="{INK}" stroke="{color}" stroke-width="2.5"/>')
            ic = icon(slug, x, y, 19, PAPER) if slug else ""
            body.append(ic or txt(x, y + 3.5, label.split()[0][:5].upper(), PAPER, 8.5, 800, "middle"))
            body.append("</g>")
        lx, ly = P(230, mid)
        lab = cat["cat"].upper()
        ly += 8 if math.sin(math.radians(mid)) > .3 else -2 if math.sin(math.radians(mid)) > -.3 else -6
        body.append(L.text(lab, lx, ly + 6, 21, color, INK, 4, "middle", 1))
    css = ("<style>.ripple{transform-box:fill-box;transform-origin:center;animation:ripple 3.6s ease-out infinite;opacity:0}"
           "@keyframes ripple{0%{transform:scale(.6);opacity:.9}100%{transform:scale(3.6);opacity:0}}"
           ".pop{transform-box:fill-box;transform-origin:center;animation:pop 4.2s ease-in-out infinite}"
           "@keyframes pop{0%,100%{transform:scale(1)}8%{transform:scale(1.18)}16%{transform:scale(1)}}" + REDUCE + "</style>")
    alt = " / ".join(f"{c['cat']}: " + ", ".join(i[0] for i in c["items"]) for c in cats)
    s = [svg_open(W, H, "Spider-sense : mon stack", "Mon stack en toile d'araignée, une branche par catégorie. " + alt),
         css, "<defs>" + L.defs() + "</defs>", page(W, H), *body, "</svg>"]
    (OUT / "spider-sense.svg").write_text("".join(s), encoding="utf-8")


# ---------------------------------------------------------------- 5. le multivers (projets)

def earth(name: str) -> str:
    return f"EARTH-{int(hashlib.md5(name.encode()).hexdigest(), 16) % 9000 + 1000}"


def gen_multiverse(cfg: dict) -> None:
    L = Letters("m")
    cols, gap, top = 3, 14, 76
    cw, ch = (W - 2 * 16 - (cols - 1) * gap) / cols, 262
    rows = math.ceil(len(cfg["projects"]) / cols)
    uni_top = top + rows * (ch + gap) + 8
    uh = 118
    H = uni_top + 46 + uh + 18
    body = [L.text("THE MULTIVERSE", 22, 52, 46, YEL, INK, 7, track=2), txt(366, 50, "every project is its own Earth", MUTED, 13, 600, italic=True)]
    css = ("<style>.glc{animation:glc 4s steps(1) infinite}.glm{animation:glm 4s steps(1) infinite}"
           "@keyframes glc{0%,70%{transform:translate(-3px,0)}72%{transform:translate(-8px,2px)}74%,100%{transform:translate(-3px,0)}}"
           "@keyframes glm{0%,70%{transform:translate(3px,0)}72%{transform:translate(8px,-2px)}74%,100%{transform:translate(3px,0)}}"
           + REDUCE + "</style>")

    def card(x: float, y: float, w: float, h: float, p: dict, color: str, delay: float, small: bool = False) -> None:
        g = [f'<g transform="translate({x:.1f} {y:.1f})">',
             f'<g class="glc" style="animation-delay:{delay:.1f}s"><rect width="{w:.1f}" height="{h}" fill="none" stroke="{CYAN}" stroke-width="3" opacity=".8"/></g>'
             f'<g class="glm" style="animation-delay:{delay:.1f}s"><rect width="{w:.1f}" height="{h}" fill="none" stroke="{MAG}" stroke-width="3" opacity=".8"/></g>',
             f'<rect width="{w:.1f}" height="{h}" fill="{NIGHT}" stroke="{INK}" stroke-width="4"/>',
             f'<rect x="2" y="2" width="{w - 4:.1f}" height="30" fill="{color}"/>',
             L.text(earth(p["name"]), 12, 25, 19, INK, track=1),
             txt(w - 10, 22, ("ORG" if p.get("kind") == "org" else "REPO"), INK, 10, 900, "end", extra=' letter-spacing="2"')]
        name = p["name"].replace("_", " ").upper()
        size = 30.0
        while L.width(name, size, 1) > w - 26 and size > 15:
            size -= 1
        g.append(L.text(name, 13, 68 if not small else 64, size, PAPER, INK, 4, track=1))
        desc = wrap(p["desc"], 34 if not small else 58)[:3]
        for j, line in enumerate(desc):
            g.append(txt(13, (92 if not small else 86) + j * 17, line, PAPER, 13, 600))
        meta_y = (92 + len(desc) * 17 + 10) if not small else 86 + len(desc) * 17 + 2
        for j, line in enumerate(wrap(p.get("meta", ""), 40 if not small else 70)[:3]):
            g.append(txt(13, meta_y + j * 15, line, MUTED, 11, 600))
        stars = p.get("stars", 0)
        if stars:
            g.append(f'<polygon points="{burst(w - 30, h - 28, 24, 10, .7)}" fill="{YEL}" stroke="{INK}" stroke-width="2.5"/>'
                     + L.text(f"★{stars}", w - 30, h - 21, 18, INK, anchor="middle"))
        g.append("</g>")
        body.append("".join(g))

    for i, p in enumerate(cfg["projects"]):
        x = 16 + (i % cols) * (cw + gap)
        y = top + (i // cols) * (ch + gap)
        card(x, y, cw, ch, p, ACCENTS[i % len(ACCENTS)], i * .6)
    body.append(L.text("TEAM-UP ISSUES", 22, uni_top + 30, 30, CYAN, INK, 5, track=1)
                + txt(232, uni_top + 28, "school projects, written with classmates", MUTED, 12.5, 600, italic=True))
    uw = (W - 2 * 16 - gap) / 2
    for i, p in enumerate(cfg.get("uni", [])[:2]):
        card(16 + i * (uw + gap), uni_top + 46, uw, uh, p, (BLUE, VIOLET)[i % 2], 1 + i * .7, small=True)
    alt = "; ".join(f"{p['name']} — {p['desc']}" for p in cfg["projects"] + cfg.get("uni", []))
    s = [svg_open(W, H, "Le multivers de mes projets", "Mes projets, chacun présenté comme une Terre du multivers : " + alt),
         css, "<defs>" + L.defs() + "</defs>", page(W, H), *body, "</svg>"]
    (OUT / "multiverse.svg").write_text("".join(s), encoding="utf-8")


# ---------------------------------------------------------------- 6. méchants vaincus (stats)

def gen_villains(cfg: dict, gh: dict) -> None:
    L = Letters("v")
    cc = gh["contributionsCollection"]
    cal = cc["contributionCalendar"]
    repos = gh["repositories"]["nodes"]
    commits = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    prs = cc["totalPullRequestContributions"]
    issues = cc["totalIssueContributions"]
    reviews = cc["totalPullRequestReviewContributions"]
    org_stars = sum(p.get("stars", 0) for p in cfg["projects"] if p.get("kind") == "org")
    stars = sum(r["stargazerCount"] for r in repos) + org_stars
    followers = gh["followers"]["totalCount"]
    rk = rank(commits, prs, issues, reviews, stars, followers)
    cur, best = streaks(cal["weeks"])
    langs = languages(repos)

    def num(n: int) -> str:
        return f"{n:,}".replace(",", " ")

    items = [("THWIP!", commits, "commits", MAG), ("KRAK!", prs, "pull requests", CYAN), ("POW!", issues, "issues", YEL),
             ("ZAP!", reviews, "reviews", RED), ("BAM!", stars, "stars", BLUE), ("WHAM!", best, "day best streak", VIOLET)]
    H = 380
    body = [L.text("THIS YEAR'S VILLAINS", 22, 52, 46, YEL, INK, 7, track=2),
            txt(468, 50, "last 12 months · refreshed every night", MUTED, 13, 600, italic=True)]
    for i, (word, value, label, color) in enumerate(items):
        x = 16 + 69 + i * 138.5
        y = 160
        body.append(f'<g class="wob" style="animation-delay:{i * .35:.2f}s">'
                    f'<polygon points="{burst(x, y, 64, 13, .74, i * 7)}" fill="{color}" stroke="{INK}" stroke-width="4"/>'
                    + L.text(num(value), x, y + 13, 36 if value < 1000 else 30, INK, anchor="middle") + "</g>"
                    + f'<g transform="rotate({(-8, 6, -5, 7, -6, 5)[i]} {x:.0f} {y - 76:.0f})">{L.text(word, x, y - 66, 24, PAPER, INK, 5, "middle")}</g>'
                    + txt(x, y + 90, label.upper(), PAPER, 11.5, 800, "middle", extra=' letter-spacing="1.5"'))
    # Rang et niveaux de pouvoir (langages).
    by = 282
    body.append(f'<circle cx="62" cy="{by + 34}" r="40" fill="{INK}" stroke="{YEL}" stroke-width="4"/>'
                + L.text(rk, 62, by + 50, 40 if len(rk) == 1 else 32, YEL, anchor="middle") + txt(62, by + 92, "RANK", MUTED, 10, 800, "middle"))
    body.append(L.text("POWER LEVELS", 124, by + 4, 22, PAPER, INK, 4, track=1)
                + txt(124 + L.width("POWER LEVELS", 22, 1) + 10, by + 3, f"current streak {cur} day{'s' if cur != 1 else ''}", MUTED, 11.5, 600))
    bx, bw = 124, W - 124 - 22
    x = bx
    tot = sum(v for _, v in langs) or 1
    for j, (name, v) in enumerate(langs):
        w = bw * v / tot
        color = ACCENTS[j % len(ACCENTS)]
        body.append(f'<rect class="grow" style="animation-delay:{j * .12:.2f}s" x="{x:.1f}" y="{by + 18}" width="{max(w - 3, 1):.1f}" height="22" fill="{color}" stroke="{INK}" stroke-width="2.5"/>')
        if w > 54:
            body.append(txt(x + 6, by + 58, f"{name} {v:.0f}%", PAPER, 11, 700))
        x += w
    css = ("<style>.wob{transform-box:fill-box;transform-origin:center;animation:wob 3s ease-in-out infinite}"
           "@keyframes wob{0%,100%{transform:rotate(0) scale(1)}10%{transform:rotate(-4deg) scale(1.06)}20%{transform:rotate(2deg) scale(1)}}"
           ".grow{transform-box:fill-box;transform-origin:left;animation:grow 1.2s cubic-bezier(.2,1.2,.3,1) both}"
           "@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}" + REDUCE + "</style>")
    alt = (f"Douze derniers mois : {commits} commits, {prs} pull requests, {issues} issues, {reviews} reviews, "
           f"{stars} étoiles, meilleure série de {best} jours, série en cours de {cur} jours, rang {rk}. "
           "Langages : " + ", ".join(f"{n} {v:.0f} %" for n, v in langs))
    s = [svg_open(W, H, "Statistiques GitHub", alt), css, "<defs>" + L.defs() + "</defs>", page(W, H), *body, "</svg>"]
    (OUT / "villains.svg").write_text("".join(s), encoding="utf-8")


# ---------------------------------------------------------------- 7. calendrier en trame

def gen_web_of_days(gh: dict) -> None:
    L = Letters("w")
    cal = gh["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    days = [(wi, di, d) for wi, wk in enumerate(weeks) for di, d in enumerate(wk["contributionDays"])]
    mx = max((d["contributionCount"] for _, _, d in days), default=1) or 1
    step = 14.6
    x0 = (W - len(weeks) * step) / 2 + step / 2
    y0 = 112
    H = y0 + 7 * step + 34
    ramp = [CYAN, BLUE, VIOLET, MAG, RED]
    cols: dict[int, list[str]] = {}
    for wi, di, d in days:
        c = d["contributionCount"]
        x, y = x0 + wi * step, y0 + di * step
        if c == 0:
            cols.setdefault(wi, []).append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.3" fill="{NIGHT2}"/>')
            continue
        t = math.sqrt(c / mx)
        cols.setdefault(wi, []).append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{1.9 + 4.6 * t:.2f}" fill="{ramp[min(4, int(t * 5))]}"/>')
    grid = "".join(f'<g class="wave" style="animation-delay:{wi * .045:.2f}s">{"".join(v)}</g>' for wi, v in sorted(cols.items()))
    wi, di, top = max(days, key=lambda t: t[2]["contributionCount"]) if days else (0, 0, {"date": "", "contributionCount": 0})
    bx, by = x0 + wi * step, y0 + di * step
    when = dt.date.fromisoformat(top["date"]).strftime("%b %d").replace(" 0", " ") if top["date"] else "—"
    body = [L.text("WEB OF DAYS", 22, 52, 46, YEL, INK, 7, track=2),
            txt(296, 50, f"{cal['totalContributions']:,} contributions in the last year".replace(",", " "), MUTED, 13, 600, italic=True),
            grid,
            f'<g class="drop"><line x1="{bx:.1f}" y1="64" x2="{bx:.1f}" y2="{by - 14:.1f}" stroke="{PAPER}" stroke-width="1.6"/>'
            f'<g transform="translate({bx:.1f} {by - 22:.1f})">{spider(0, 0, .75, PAPER)}</g></g>']
    label = f"BUSIEST DAY · {when.upper()} · {top['contributionCount']}"
    lw = L.width(label, 16, 1) + 22
    lx = min(max(bx - lw / 2, 16), W - 16 - lw)
    body.append(caption(lx, 66, lw, 26, -1) + f'<g transform="rotate(-1 {lx + lw / 2:.0f} 79)">{L.text(label, lx + 11, 86, 16, INK, track=1)}</g>')
    css = ("<style>.wave{animation:wave 5s ease-in-out infinite}@keyframes wave{0%,100%{opacity:1}12%{opacity:.35}24%{opacity:1}}"
           ".drop{animation:drop 2.8s ease-in-out infinite}@keyframes drop{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}"
           + REDUCE + "</style>")
    s = [svg_open(W, H, "Calendrier de contributions",
                  f"Calendrier de contributions en trame de points : {cal['totalContributions']} contributions sur un an, "
                  f"journée la plus chargée le {top['date']} avec {top['contributionCount']}. Une araignée descend sur ce jour-là."),
         css, "<defs>" + L.defs() + "</defs>", page(W, H), *body, "</svg>"]
    (OUT / "web-of-days.svg").write_text("".join(s), encoding="utf-8")


# ---------------------------------------------------------------- 8. encadrés de narration

def gen_captions() -> None:
    for name, label, w, color in (("offduty", "MEANWHILE, OFF DUTY…", W, YEL), ("continued", "TO BE CONTINUED IN ISSUE #4…", 470, YEL)):
        L = Letters("k")
        size = 28
        tw = L.width(label, size, 2)
        bw = tw + 44
        x = (w - bw) / 2 if name == "offduty" else w - bw - 8
        body = [caption(x, 10, bw, 48, -1.2, color), f'<g transform="rotate(-1.2 {x + bw / 2:.0f} 34)">{L.text(label, x + 22, 45, size, INK, track=2)}</g>']
        if name == "continued":
            body.append(f'<path d="M{x - 6:.0f} 34l-30 -14v8h-40v12h40v8z" fill="{RED}" stroke="{INK}" stroke-width="3"/>')
        s = [svg_open(w, 70, label, label), "<defs>" + L.defs() + "</defs>", *body, "</svg>"]
        (OUT / f"{name}.svg").write_text("".join(s), encoding="utf-8")


# ---------------------------------------------------------------- main

def main() -> None:
    cfg = json.loads((DATA / "profile.json").read_text(encoding="utf-8"))
    if "--fetch" in sys.argv:
        fetch(os.environ.get("GH_LOGIN", "CodeByHaamza"))
    gh = load_gh()
    OUT.mkdir(parents=True, exist_ok=True)
    gen_cover(cfg)
    gen_links(cfg)
    gen_origin(cfg)
    gen_spider_sense(cfg)
    gen_multiverse(cfg)
    gen_villains(cfg, gh)
    gen_web_of_days(gh)
    gen_captions()
    for f in sorted(OUT.glob("*.svg")):
        print(f"{f.name:22} {f.stat().st_size / 1024:7.1f} Ko")


if __name__ == "__main__":
    main()
