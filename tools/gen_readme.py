#!/usr/bin/env python3
"""Genere les SVG du README de profil.

Tout est auto-contenu : aucun service externe, aucune police externe, aucune
image externe. Un SVG affiche via <img> ne peut rien charger de l'exterieur,
donc les logos sont inlines et les arts braille sont convertis en rectangles
(une police mono sans les glyphes U+28xx afficherait sinon des carres vides).

Usage:
    python tools/gen_readme.py            # utilise data/gh-raw.json
    python tools/gen_readme.py --fetch    # rappelle l'API GitHub d'abord
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "gen"
ICONS = ROOT / "assets" / "icons"
ASCII = ROOT / "assets" / "ascii"
DATA = ROOT / "data"

W = 860  # largeur de rendu d'un README GitHub

# Catppuccin Mocha
C = {
    "bg": "#11111b", "panel": "#181825", "line": "#313244", "edge": "#1e1e2e",
    "text": "#cdd6f4", "sub": "#a6adc8", "dim": "#6c7086", "faint": "#45475a",
    "blue": "#89b4fa", "green": "#a6e3a1", "mauve": "#cba6f7", "peach": "#fab387",
    "red": "#f38ba8", "yellow": "#f9e2af", "teal": "#94e2d5",
}
MONO = ("ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,"
        "'Liberation Mono','DejaVu Sans Mono',monospace")


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


# ---------------------------------------------------------------- braille

def braille_rects(art: str, x0: float, y0: float, dot: float,
                  fill: str, gap: float = 0.0) -> str:
    """Convertit un art braille en UN SEUL chemin SVG.

    Une cellule braille U+2800+n code une matrice 2 colonnes x 4 lignes de
    points. Les bits ne suivent pas l'ordre de lecture : les points 7 et 8
    (la 4e ligne) ont ete ajoutes apres coup, d'ou la table explicite.

    Les points voisins d'une meme ligne sont fusionnes en une seule passe
    horizontale. Un <rect> par point coutait ~70 octets et l'etoile en compte
    plus de 3 000 : le fichier passait les 140 Ko. Ici une passe vaut ~18
    octets, et il y en a bien moins.

    `gap` est accepte pour compatibilite mais ignore : separer les points
    empecherait la fusion, qui est tout l'interet.
    """
    del gap
    # bit -> (colonne, ligne)
    bits = ((0x01, 0, 0), (0x02, 0, 1), (0x04, 0, 2), (0x40, 0, 3),
            (0x08, 1, 0), (0x10, 1, 1), (0x20, 1, 2), (0x80, 1, 3))
    rows: dict[int, set[int]] = {}
    for row, line in enumerate(art.rstrip("\n").split("\n")):
        for col, ch in enumerate(line):
            o = ord(ch)
            if not (0x2800 <= o <= 0x28FF):
                continue
            n = o - 0x2800
            for bit, dc, dr in bits:
                if n & bit:
                    rows.setdefault(row * 4 + dr, set()).add(col * 2 + dc)

    subs = []
    for dr in sorted(rows):
        cols = sorted(rows[dr])
        start = prev = cols[0]
        for c in cols[1:] + [None]:
            if c is not None and c == prev + 1:
                prev = c
                continue
            x = x0 + start * dot
            y = y0 + dr * dot
            w = (prev - start + 1) * dot
            subs.append(f"M{x:.1f} {y:.1f}h{w:.1f}v{dot:.1f}h-{w:.1f}z")
            if c is None:
                break
            start = prev = c
    return f'<path fill="{fill}" d="{"".join(subs)}"/>'


def braille_size(art: str, dot: float) -> tuple[float, float]:
    lines = art.rstrip("\n").split("\n")
    cols = max(len(l) for l in lines)
    return cols * 2 * dot, len(lines) * 4 * dot


# ---------------------------------------------------------------- figlet

def figlet_rects(art: str, x0: float, y0: float, cw: float, ch: float,
                 bright: str, shadow: str) -> str:
    """Rend un figlet ANSI Shadow en rectangles deux tons.

    '#' plein -> couleur vive ; les caracteres de filet (les bords d'ombre de
    la police ANSI Shadow) -> couleur sourde. Rendu identique partout, sans
    dependre des metriques d'une police.
    """
    hi, lo = [], []
    for row, line in enumerate(art.rstrip("\n").split("\n")):
        for col, chx in enumerate(line):
            if chx in " \t ":
                continue
            r = (f'<rect x="{x0 + col * cw:.2f}" y="{y0 + row * ch:.2f}" '
                 f'width="{cw + .4:.2f}" height="{ch + .4:.2f}"/>')
            (hi if chx == "█" else lo).append(r)
    return (f'<g fill="{shadow}">' + "".join(lo) + "</g>"
            f'<g fill="{bright}">' + "".join(hi) + "</g>")


def figlet_size(art: str, cw: float, ch: float) -> tuple[float, float]:
    lines = art.rstrip("\n").split("\n")
    return max(len(l) for l in lines) * cw, len(lines) * ch


# ---------------------------------------------------------------- logos

_ICON_CACHE: dict[str, str] = {}


def icon_path(slug: str) -> str | None:
    """Retourne le contenu du <path> d'un logo simple-icons, en viewBox 24."""
    if slug in _ICON_CACHE:
        return _ICON_CACHE[slug]
    f = ICONS / f"{slug}.svg"
    if not f.exists():
        return None
    svg = f.read_text(encoding="utf-8")
    ds = re.findall(r'<path[^>]*\sd="([^"]+)"', svg)
    if not ds:
        return None
    _ICON_CACHE[slug] = " ".join(ds)
    return _ICON_CACHE[slug]


def icon(slug: str | None, x: float, y: float, s: float, fill: str) -> str:
    """Un logo de cote s, coin haut-gauche en (x, y)."""
    if slug == "__pygame":  # absent de simple-icons : triangle de lecture
        return (f'<g fill="{fill}" transform="translate({x:.2f},{y:.2f})">'
                f'<path d="M{s*.18:.2f} {s*.12:.2f}L{s*.88:.2f} {s*.5:.2f}'
                f'L{s*.18:.2f} {s*.88:.2f}Z"/></g>')
    d = icon_path(slug) if slug else None
    if not d:
        return ""
    k = s / 24.0
    return (f'<g fill="{fill}" transform="translate({x:.2f},{y:.2f}) '
            f'scale({k:.4f})"><path d="{d}"/></g>')


# ---------------------------------------------------------------- briques

def head(w: float, h: float, title: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" '
            f'height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}" '
            f'role="img" aria-label="{esc(title)}">'
            f'<title>{esc(title)}</title>')


def panel(w: float, h: float, r: float = 8) -> str:
    return (f'<rect x=".5" y=".5" width="{w-1:.1f}" height="{h-1:.1f}" '
            f'rx="{r}" fill="{C["bg"]}" stroke="{C["edge"]}"/>')


def txt(x: float, y: float, s: str, fill: str = None, size: float = 13,
        weight: str = "400", anchor: str = "start", opacity: str = None) -> str:
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    o = f' opacity="{opacity}"' if opacity else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{MONO}" '
            f'font-size="{size}" font-weight="{weight}" '
            f'fill="{fill or C["text"]}" xml:space="preserve"{a}{o}>'
            f'{esc(s)}</text>')


def reveal_css(sel: str, count: int, dur: float = .42, step: float = .13,
               dx: float = 6) -> str:
    """Apparition en cascade, jouee une seule fois.

    L'etat ECRIT est l'etat final (visible). Les keyframes partent de
    l'invisible et y ramenent. C'est l'inverse du reflexe habituel, et c'est
    volontaire : si les animations ne tournent pas — rendu sans CSS, cache,
    prefers-reduced-motion — le contenu reste lisible au lieu de disparaitre.
    """
    out = [f"@keyframes rise{{from{{opacity:0;transform:translate({dx}px,4px)}}"
           f"to{{opacity:1;transform:none}}}}",
           f"{sel}{{opacity:1;animation:rise {dur}s ease-out both}}"]
    for i in range(count):
        out.append(f"{sel}:nth-of-type({i+1}){{animation-delay:{i*step:.2f}s}}")
    out.append("@media(prefers-reduced-motion:reduce){"
               f"{sel}{{animation:none}}}}")
    return "".join(out)


def wipe(x: float, y: float, w: float, h: float, delay: float, dur: float,
         bg: str = None) -> str:
    """Un cache couleur de fond qui glisse vers la droite : effet de frappe.

    Le cache est ECRIT deja ecarte (translateX(102%)) et l'animation part de
    0 pour y revenir. Sans animation il n'est donc nulle part, et le texte
    se lit. Ecrit a 0 comme je l'avais fait d'abord, il masquait tout quand
    les animations ne tournaient pas.
    """
    return (f'<rect class="wipe" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
            f'height="{h:.1f}" fill="{bg or C["bg"]}" '
            f'style="animation-delay:{delay:.2f}s;animation-duration:{dur:.2f}s"/>')


WIPE_CSS = ("@keyframes wipe{from{transform:translateX(0)}"
            "to{transform:translateX(102%)}}"
            ".wipe{transform:translateX(102%);animation:wipe linear both}"
            "@media(prefers-reduced-motion:reduce){"
            ".wipe{animation:none}}")

TITLEBAR_DOTS = [(C["red"], 0), (C["yellow"], 1), (C["green"], 2)]


def titlebar(w: float, label: str) -> str:
    g = [f'<path d="M.5 8.5A8 8 0 0 1 8.5.5h{w-17:.1f}a8 8 0 0 1 8 8V26H.5Z" '
         f'fill="{C["panel"]}" stroke="{C["edge"]}"/>']
    for col, i in TITLEBAR_DOTS:
        g.append(f'<circle cx="{16 + i*15}" cy="13.5" r="4.5" fill="{col}"/>')
    g.append(txt(72, 17.5, label, C["dim"], 10.5))
    return "".join(g)


def prompt(x: float, y: float, cmd: str, user: str, host: str,
           size: float = 12.5) -> str:
    """user@host:~$ cmd — colore par morceaux, largeurs calees en ch."""
    ch = size * 0.6
    parts = [(f"{user}@{host}", C["blue"]), (":", C["text"]),
             ("~", C["yellow"]), ("$ ", C["green"]), (cmd, C["text"])]
    out, cx = [], x
    for s, col in parts:
        out.append(txt(cx, y, s, col, size))
        cx += len(s) * ch
    return "".join(out)


# ---------------------------------------------------------------- donnees

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


def rank(commits: int, prs: int, issues: int, reviews: int,
         stars: int, followers: int) -> str:
    """Rang lettre, meme esprit que github-readme-stats : une moyenne ponderee
    de percentiles, pas une note absolue."""
    def pct(v, med):  # position approx. vs une mediane de reference
        return 1.0 / (1.0 + (med / max(v, 1)) ** 0.5)
    s = (pct(commits, 250) * .30 + pct(prs, 50) * .20 + pct(issues, 25) * .10
         + pct(reviews, 20) * .10 + pct(stars, 50) * .20
         + pct(followers, 25) * .10)
    for lim, name in ((.92, "S"), (.82, "A+"), (.70, "A"), (.58, "B+"),
                      (.45, "B"), (.30, "C+")):
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
    out = [(n.lower(), v * 100.0 / allsum) for n, v in ranked[:top]]
    rest = sum(v for _, v in ranked[top:]) * 100.0 / allsum
    if rest > 0.4:
        out.append(("other", rest))
    return out


# ---------------------------------------------------------------- 1. header

# Les cinq lettres, dessinees en polygones sur une grille de 100 x 140.
# Pourquoi pas du <text> : un SVG affiche via <img> ne charge aucune police,
# donc le rendu dependrait de ce que la machine du visiteur possede. Arial
# Black existe sous Windows et macOS, pas sous Linux, et la graisse change
# tout a l'effet de decalage chromatique. En chemins, c'est identique partout.
GLYPHS = {
    "H": "M0 0H28V56H72V0H100V140H72V84H28V140H0Z",
    "A": ("M50 0 100 140H70L61 112H39L30 140H0ZM50 44 40 86H60Z"),
    "M": "M0 140V0H26L50 58 74 0H100V140H78V50L58 94H42L22 50V140Z",
    "Z": "M0 0H100V26L40 114H100V140H0V114L60 26H0Z",
}
NAME = "HAMZA"
GW, GH, ADV = 100.0, 140.0, 108.0


def name_path(scale: float) -> tuple:
    """Le mot entier en un seul chemin, plus sa largeur rendue."""
    subs = []
    for k, chx in enumerate(NAME):
        d = GLYPHS[chx]
        subs.append(f'<path d="{d}" transform="translate({k * ADV:.1f},0)"/>')
    return "".join(subs), (len(NAME) - 1) * ADV + GW


def hobby_glyphs(cx_: float, cy_: float, side: int) -> list:
    """Motifs de mes hobbies, chacun centre sur (0,0) pour que le scale de
    l'animation tourne autour de son propre centre sans transform-origin."""
    out = []
    # araignee (Spider-Man)
    spider = ('<g stroke="#f4f4ff" stroke-width="2.1" fill="none" '
              'stroke-linecap="round">'
              '<path d="M-13-9-5-2M13-9 5-2M-15 1-6 1M15 1 6 1'
              'M-13 11-5 4M13 11 5 4"/></g>'
              '<ellipse cx="0" cy="1" rx="4.6" ry="6" fill="#f4f4ff"/>')
    # arcane Persona : une carte avec son chiffre romain
    tarot = ('<rect x="-9" y="-12.5" width="18" height="25" rx="2" '
             'fill="none" stroke="#c9a227" stroke-width="2"/>'
             '<path d="M0-7 2.1-1.6 7.6-1.6 3.2 1.9 4.9 7.3 0 4 -4.9 7.3'
             '-3.2 1.9 -7.6-1.6 -2.1-1.6Z" fill="#c9a227"/>')
    # le code
    code = ('<g stroke="#a6e3a1" stroke-width="2.4" fill="none" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M-5-8-13 0-5 8M5-8 13 0 5 8M1.5-10-1.5 10"/></g>')
    # haltere
    gym = ('<g fill="#89b4fa">'
           '<rect x="-14" y="-7" width="4.5" height="14" rx="1.5"/>'
           '<rect x="-8.5" y="-10" width="4.5" height="20" rx="1.5"/>'
           '<rect x="4" y="-10" width="4.5" height="20" rx="1.5"/>'
           '<rect x="9.5" y="-7" width="4.5" height="14" rx="1.5"/>'
           '<rect x="-4.5" y="-2" width="9" height="4"/></g>')
    # lignes de vitesse (manga)
    speed = ('<g stroke="#f38ba8" stroke-width="2" stroke-linecap="round">'
             '<path d="M-14-7H2M-14 0H8M-14 7H-1"/></g>')
    return [spider, tarot, code, gym, speed]


def gen_header(cfg: dict) -> None:
    """Le nom a la Spider-Verse : trame de points, decalage chromatique
    cyan/magenta qui converge a l'apparition, et des motifs de mes hobbies
    qui popent autour.

    Les lettres sont des polygones (voir GLYPHS) et non du texte : pas de
    police a charger, donc le meme rendu partout. Les ゴゴゴ viennent de
    l'art braille de mes dotfiles.

    Comme partout ici, l'etat ECRIT est l'etat final. Les keyframes partent
    du decale/invisible et y ramenent : sans animations, le nom se lit.
    """
    ident = cfg["identity"]
    ono = (ASCII / "jojo-onomatope").with_suffix(".txt").read_text(encoding="utf-8")

    scale = 0.60
    letters, raw_w = name_path(scale)
    nw, nh = raw_w * scale, GH * scale
    nx, ny = (W - nw) / 2, 46.0
    tag_y = ny + nh + 40
    h = tag_y + 28

    SKEW = -11          # l'italique
    CY, MG, INK = "#00e5ff", "#ff2e63", "#0a0a12"

    css = ("@keyframes cyIn{from{opacity:0;transform:translate(-40px,13px)}"
           "to{opacity:1;transform:translate(-5px,3px)}}"
           "@keyframes mgIn{from{opacity:0;transform:translate(40px,-13px)}"
           "to{opacity:1;transform:translate(5px,-3px)}}"
           "@keyframes fgIn{from{opacity:0;transform:scale(1.08)}"
           "to{opacity:1;transform:scale(1)}}"
           "@keyframes jit{0%,100%{transform:translate(0,0)}"
           "20%{transform:translate(-3px,1px)}40%{transform:translate(3px,-1px)}"
           "60%{transform:translate(-2px,0)}80%{transform:translate(2px,1px)}}"
           "@keyframes pop{from{opacity:0;transform:scale(.3) rotate(-25deg)}"
           "to{opacity:1;transform:scale(1) rotate(0)}}"
           "@keyframes fade{from{opacity:0}to{opacity:1}}"
           f".cy{{opacity:1;transform:translate(-5px,3px);"
           f"animation:cyIn .8s cubic-bezier(.2,1.1,.3,1) both}}"
           f".mg{{opacity:1;transform:translate(5px,-3px);"
           f"animation:mgIn .8s cubic-bezier(.2,1.1,.3,1) both}}"
           ".fg{opacity:1;animation:fgIn .55s ease-out both;animation-delay:.5s}"
           ".gl{animation:jit .45s steps(5,end) 1 both;animation-delay:.8s}"
           ".hb{opacity:1;animation:pop .5s cubic-bezier(.2,1.5,.3,1) both}"
           ".tg{opacity:1;animation:fade .6s ease-out both;animation-delay:1.1s}"
           "@media(prefers-reduced-motion:reduce){"
           ".cy,.mg,.fg,.gl,.hb,.tg{animation:none}}")

    s = [head(W, h, "HAMZA — " + ident["tagline"]), panel(W, h),
         titlebar(W, f'{ident["handle"]}@{ident["host"]} — {ident["shell"]}'),
         "<style>" + css + "</style>",
         '<defs><pattern id="ht" width="8" height="8" '
         'patternUnits="userSpaceOnUse">'
         f'<circle cx="2" cy="2" r="1.15" fill="{MG}" opacity=".3"/>'
         '</pattern>'
         f'<clipPath id="pan"><rect x="1" y="27" width="{W-2}" '
         f'height="{h-28:.1f}"/></clipPath></defs>',
         f'<g clip-path="url(#pan)">'
         f'<rect x="1" y="27" width="{W-2}" height="{h-28:.1f}" '
         f'fill="url(#ht)"/>']

    # trois calques du meme mot : cyan et magenta decales, blanc par-dessus
    base = (f'translate({nx:.1f},{ny:.1f}) scale({scale:.4f}) '
            f'skewX({SKEW})')
    s.append('<g class="gl">')
    for cls, col in (("cy", CY), ("mg", MG)):
        s.append(f'<g class="{cls}"><g transform="{base}" fill="{col}" '
                 f'fill-rule="evenodd">{letters}</g></g>')
    s.append(f'<g class="fg"><g transform="{base}" fill="none" stroke="{INK}" '
             f'stroke-width="9" stroke-linejoin="round" '
             f'fill-rule="evenodd">{letters}</g>'
             f'<g transform="{base}" fill="#f4f4ff" '
             f'fill-rule="evenodd">{letters}</g></g>')
    s.append("</g>")

    # les hobbies, de part et d'autre du nom
    glyphs = hobby_glyphs(0, 0, 1)
    # Bornes voulues : rien sous ny+95, sinon le glyphe mord sur l'accroche
    # (c'etait le cas de </> au premier rendu).
    spots = [(nx - 62, ny + 20), (nx - 44, ny + 58), (nx - 66, ny + 94),
             (nx + nw + 44, ny + 26), (nx + nw + 34, ny + 70)]
    for k, (gx, gy) in enumerate(spots):
        s.append(f'<g transform="translate({gx:.1f},{gy:.1f})">'
                 f'<g class="hb" style="animation-delay:{.95 + k * .11:.2f}s">'
                 f'{glyphs[k]}</g></g>')

    # les ゴゴゴ de mes dotfiles, derriere a droite
    # a dot=1.0 les go-go-go n'etaient qu'une tache rose : illisibles.
    odot = 1.9
    ow, oh = braille_size(ono, odot)
    s.append(f'<g class="hb" style="animation-delay:1.5s" opacity=".45">'
             + braille_rects(ono, W - ow - 22, ny + 2, odot, MG) + "</g>")

    s.append(f'<g class="tg">'
             + txt(W / 2, tag_y, ident["tagline"], "#8b93a8", 12.5,
                   anchor="middle") + "</g>")
    s.append("</g>")   # ferme le groupe de rognage du panneau
    s.append("</svg>")
    (OUT / "header.svg").write_text("".join(s), encoding="utf-8")


# ----------------------------------------------------------- 1b. les liens

def gen_prompts(cfg: dict) -> None:
    """Lignes de prompt isolees, pour les sections faites d'images externes
    (jaquettes Steam, couvertures AniList) que ce script ne dessine pas."""
    i = cfg["identity"]
    for name, cmd, right in (
        ("games", "cat passions/games.md", "what I actually play"),
        ("manga", "cat passions/manga.md", "auto-updated from AniList"),
    ):
        h = 34.0
        s = [head(W, h, cmd),
             f'<rect x=".5" y=".5" width="{W-1}" height="{h-1:.1f}" rx="8" '
             f'fill="{C["bg"]}" stroke="{C["edge"]}"/>',
             prompt(17, 21.5, cmd, i["handle"], i["host"]),
             txt(W - 17, 21.5, right, C["faint"], 10.5, anchor="end"),
             "</svg>"]
        (OUT / f"prompt-{name}.svg").write_text("".join(s), encoding="utf-8")


def gen_links(cfg: dict) -> None:
    """Une pastille par lien, en fichiers separes.

    Un SVG affiche via <img> ne rend pas ses <a> cliquables : c'est le
    markdown qui doit porter le lien, donc une image par destination.
    """
    fs, h = 11.5, 26.0
    ch = fs * 0.6
    for l in cfg["identity"]["links"]:
        label, slug = l["label"], l["icon"]
        w = len(label) * ch + (34 if slug else 22)
        s = [head(w, h, label),
             f'<rect x=".5" y=".5" width="{w-1:.1f}" height="{h-1:.1f}" rx="5" '
             f'fill="{C["panel"]}" stroke="{C["line"]}"/>']
        tx = 11.0
        if slug:
            s.append(icon(slug, 9, (h - 12) / 2, 12, C["blue"]))
            tx = 25.0
        s.append(txt(tx, h / 2 + fs * .36, label, C["blue"], fs))
        s.append("</svg>")
        name = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
        (OUT / f"link-{name}.svg").write_text("".join(s), encoding="utf-8")


# ---------------------------------------------------------------- 2. whoami

def gen_whoami(cfg: dict) -> None:
    lines = cfg["whoami"]
    fs, lh = 12.5, 20.0
    ch = fs * 0.6
    pad = 17.0
    h = pad * 2 + 24 + len(lines) * lh + 6
    i = cfg["identity"]

    s = [head(W, h, "whoami"), panel(W, h), "<style>" + WIPE_CSS +
         "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
         ".cur{animation:blink 1.1s steps(1,end) infinite}</style>"]
    s.append(prompt(pad, pad + 12, "whoami", i["handle"], i["host"]))

    t, y = 0.35, pad + 24
    for ln in lines:
        y += lh
        if not ln.strip():
            t += .18
            continue
        s.append(txt(pad, y, ln, C["text"], fs))
        wd = len(ln) * ch
        dur = max(.28, len(ln) * 0.016)
        s.append(wipe(pad - 1, y - fs, wd + 3, fs + 6, t, dur))
        t += dur * .72
    s.append(f'<rect class="cur" x="{pad:.1f}" y="{y+7:.1f}" width="{ch:.1f}" '
             f'height="3" fill="{C["text"]}"/>')
    s.append("</svg>")
    (OUT / "whoami.svg").write_text("".join(s), encoding="utf-8")


# ------------------------------------------------------------- 3. neofetch

def gen_neofetch(cfg: dict) -> None:
    art = (ASCII / "etoile-joestar.txt").read_text(encoding="utf-8")
    dot = 2.0
    aw, ah = braille_size(art, dot)
    pad, fs, lh = 17.0, 12.0, 18.0
    ch = fs * 0.6
    col_x = pad + aw + 26

    rows = []  # (type, payload)
    for m in cfg["machines"]:
        rows.append(("host", (m["user"], m["host"], m["accent"])))
        rows.append(("rule", None))
        for k, v in m["specs"]:
            rows.append(("spec", (k, v)))
        rows.append(("blank", None))
    rows.pop()

    body_h = len(rows) * lh
    h = pad * 2 + 24 + max(ah, body_h) + 6
    i = cfg["identity"]

    s = [head(W, h, "neofetch — PC-HAMZA et karrouchi-server"), panel(W, h),
         "<style>" + reveal_css(".rv", len(rows), step=.055) +
         "@keyframes tw{0%,100%{opacity:.75}50%{opacity:1}}"
         ".star{animation:tw 4s ease-in-out infinite}</style>"]
    s.append(prompt(pad, pad + 12, "neofetch --both", i["handle"], i["host"]))

    top = pad + 30
    s.append(f'<g class="star">'
             + braille_rects(art, pad, top, dot, C["yellow"], .35) + "</g>")

    y = top + 10
    for kind, p in rows:
        if kind == "host":
            u, hn, acc = p
            s.append(f'<g class="rv">' + txt(col_x, y, f"{u}@{hn}", C[acc], fs,
                                             "700") + "</g>")
        elif kind == "rule":
            s.append(f'<g class="rv"><rect x="{col_x:.1f}" y="{y-5:.1f}" '
                     f'width="{W - col_x - pad:.1f}" height="1" '
                     f'fill="{C["faint"]}"/></g>')
        elif kind == "spec":
            k, v = p
            s.append('<g class="rv">' + txt(col_x, y, k, C["mauve"], fs)
                     + txt(col_x + 10 * ch, y, v, C["sub"], fs) + "</g>")
        else:
            s.append('<g class="rv"/>')
        y += lh
    s.append("</svg>")
    (OUT / "neofetch.svg").write_text("".join(s), encoding="utf-8")


# ---------------------------------------------------------------- 4. stack

def gen_stack(cfg: dict) -> None:
    fs, lh, pad = 12.0, 26.0, 17.0
    ch, isz, gap = fs * 0.6, 14.0, 15.0
    cat_w = 112.0
    rows = cfg["stack"]
    h = pad * 2 + 22 + len(rows) * lh + 26

    s = [head(W, h, "stack"), panel(W, h),
         "<style>" + reveal_css(".rv", len(rows) + 1, step=.085) + "</style>"]
    s.append(txt(pad, pad + 11, "── stack " + "─" * 62, C["red"], 11.5))

    y = pad + 22 + 16
    for r in rows:
        s.append('<g class="rv">')
        s.append(txt(pad, y, r["cat"], C["teal"], fs))
        x = pad + cat_w
        for label, slug in r["items"]:
            g = icon(slug, x, y - isz + 2.5, isz, C["blue"])
            if g:
                s.append(g)
                x += isz + 5
            s.append(txt(x, y, label, C["text"] if slug else C["dim"], fs))
            x += len(label) * ch + gap
        s.append("</g>")
        y += lh

    s.append('<g class="rv">'
             + txt(pad, y + 2, "gym", C["teal"], fs)
             + txt(pad + cat_w, y + 2, cfg["gym"], C["dim"], fs) + "</g>")
    s.append("</svg>")
    (OUT / "stack.svg").write_text("".join(s), encoding="utf-8")


# ------------------------------------------------------------- 5. projects

def gen_projects(cfg: dict) -> None:
    fs, pad = 12.0, 17.0
    ch = fs * 0.6
    row_h, meta_h = 20.0, 17.0
    projs = cfg["projects"]
    uni = cfg.get("uni", [])
    nx = pad + 164  # colonne des descriptions, commune a toutes les lignes
    n_rv = len(projs) + len(uni) + 2

    h = (pad * 2 + 24 + (len(projs) + len(uni)) * (row_h + meta_h)
         + 30 + row_h + 10)
    i = cfg["identity"]

    s = [head(W, h, "mes projets"), panel(W, h),
         "<style>" + reveal_css(".rv", n_rv, step=.085) + "</style>"]
    s.append(prompt(pad, pad + 12, "ls -l projects/", i["handle"], i["host"]))
    s.append(txt(W - pad, pad + 12, "stars", C["dim"], 10.5, anchor="end"))

    def row(p: dict, y: float, stars: bool) -> None:
        s.append('<g class="rv">')
        s.append(txt(pad, y, p["name"],
                     C["mauve"] if p["kind"] == "org" else C["blue"], fs, "700"))
        s.append(txt(nx, y, p["desc"], C["text"], fs))
        if stars:
            s.append(txt(W - pad, y, f'★ {p["stars"]}',
                         C["yellow"] if p["stars"] else C["faint"], fs,
                         anchor="end"))
        s.append(txt(nx, y + meta_h, p["meta"], C["dim"], 11))
        s.append("</g>")

    y = pad + 30 + row_h
    for p in projs:
        row(p, y, True)
        y += row_h + meta_h

    if uni:
        y += 4
        s.append('<g class="rv">'
                 + txt(pad, y, "── university " + "─" * 56, C["faint"], 11)
                 + "</g>")
        y += 22
        for p in uni:
            row(p, y, False)
            y += row_h + meta_h

    s.append('<g class="rv">'
             + txt(pad, y + 4, "private", C["faint"], fs)
             + txt(nx, y + 4, cfg["private_note"], C["faint"], 11) + "</g>")
    s.append("</svg>")
    (OUT / "projects.svg").write_text("".join(s), encoding="utf-8")


# ------------------------------------------------------------ 6b. fun facts

def gen_funfacts(cfg: dict) -> None:
    """Les fun facts, avec le Spider-Man braille de mes dotfiles a droite.

    Il est la parce qu'un des facts parle de Spider-Man, et parce que cet art
    vit deja sur mes machines : autant qu'il serve.
    """
    lines = cfg.get("funfacts", [])
    if not lines:
        return
    art = (ASCII / "spiderman.txt").read_text(encoding="utf-8")
    dot = 1.45
    aw, ah = braille_size(art, dot)

    fs, lh, pad = 12.0, 19.0, 17.0
    ch = fs * 0.6
    text_h = len(lines) * lh
    h = pad * 2 + 24 + max(text_h, ah) + 6
    i = cfg["identity"]

    s = [head(W, h, "fun facts"), panel(W, h), "<style>" + WIPE_CSS + "</style>",
         prompt(pad, pad + 13, "cat fun-facts.txt", i["handle"], i["host"])]

    ax = W - pad - aw
    s.append(braille_rects(art, ax, pad + 26, dot, "#5a4a7a"))

    t, y = .3, pad + 26
    for ln in lines:
        y += lh
        if not ln.strip():
            t += .14
            continue
        s.append(txt(pad, y, ln, C["sub"], fs))
        dur = max(.26, len(ln) * .013)
        s.append(wipe(pad - 1, y - fs, len(ln) * ch + 3, fs + 6, t, dur))
        t += dur * .66
    s.append("</svg>")
    (OUT / "funfacts.svg").write_text("".join(s), encoding="utf-8")


# ---------------------------------------------------------------- 6. stats

def gen_stats(cfg: dict, gh: dict) -> None:
    cc = gh["contributionsCollection"]
    cal = cc["contributionCalendar"]
    repos = gh["repositories"]["nodes"]
    commits = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    prs = cc["totalPullRequestContributions"]
    issues = cc["totalIssueContributions"]
    reviews = cc["totalPullRequestReviewContributions"]
    stars = sum(r["stargazerCount"] for r in repos) + 71  # + l'organisation
    followers = gh["followers"]["totalCount"]
    rk = rank(commits, prs, issues, reviews, stars, followers)
    langs = languages(repos)
    cur, best = streaks(cal["weeks"])

    def num(n: int) -> str:
        return f"{n:,}".replace(",", " ")  # fine space, pas de virgule

    pad, fs = 17.0, 12.0
    ch = fs * 0.6
    card_h = 124.0
    gapx = 14.0
    lw = (W - pad * 2 - gapx) * 0.56
    rw = W - pad * 2 - gapx - lw
    rx = pad + lw + gapx
    top = pad + 30
    lh = 19.0
    h = top + card_h + 16 + len(langs) * lh + pad

    s = [head(W, h, "mes statistiques GitHub"), panel(W, h),
         "<style>" + WIPE_CSS +
         "@keyframes pop{from{opacity:0;transform:scale(.82)}"
         "to{opacity:1;transform:none}}"
         ".pop{opacity:1;animation:pop .5s cubic-bezier(.2,1.4,.3,1) both}"
         + reveal_css(".rv", 12, step=.055) + "</style>"]
    i = cfg["identity"]
    s.append(prompt(pad, pad + 13, "git stats --self-hosted", i["handle"],
                    i["host"]))
    s.append(txt(W - pad, pad + 13, "generated in-repo · no external service",
                 C["faint"], 10, anchor="end"))

    def card(x: float, w: float, title: str) -> None:
        s.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{w:.1f}" '
                 f'height="{card_h:.1f}" rx="7" fill="{C["panel"]}" '
                 f'stroke="{C["edge"]}"/>')
        s.append(txt(x + 13, top + 19, title, C["faint"], 9.5))

    # ---- carte de gauche : le rang et les totaux
    card(pad, lw, "OVERALL")
    cxr = pad + 52
    cyr = top + 70
    s.append(f'<g class="pop"><circle cx="{cxr:.1f}" cy="{cyr:.1f}" r="31" '
             f'fill="none" stroke="{C["line"]}" stroke-width="4"/>'
             f'<circle cx="{cxr:.1f}" cy="{cyr:.1f}" r="31" fill="none" '
             f'stroke="{C["yellow"]}" stroke-width="4" stroke-linecap="round" '
             f'stroke-dasharray="{195 * 0.84:.0f} 400" '
             f'transform="rotate(-90 {cxr:.1f} {cyr:.1f})"/>'
             + txt(cxr, cyr + 9, rk, C["yellow"], 26, "700", "middle")
             + "</g>")
    s.append(txt(cxr, cyr + 31, "rank", C["faint"], 9.5, anchor="middle"))

    grid = [("commits", num(commits)), ("stars", num(stars)),
            ("PRs", num(prs)), ("reviews", num(reviews)),
            ("repos", num(gh["repositories"]["totalCount"])),
            ("issues", num(issues)), ("followers", num(followers)),
            ("12-mo", num(cal["totalContributions"]))]
    gx0 = pad + 104
    colw = (lw - 118) / 2
    for n, (k, v) in enumerate(grid):
        gx = gx0 + (n % 2) * colw
        gy = top + 40 + (n // 2) * 21
        s.append('<g class="rv">' + txt(gx, gy, k, C["mauve"], 11.5)
                 + txt(gx + colw - 16, gy, v, C["text"], 11.5, "700",
                       anchor="end") + "</g>")

    # ---- carte de droite : les series
    card(rx, rw, "STREAK")
    s.append(f'<g class="pop" style="animation-delay:.12s">'
             + txt(rx + rw / 2, top + 72, str(cur), C["peach"], 42, "700",
                   "middle") + "</g>")
    s.append(txt(rx + rw / 2, top + 90, "days, current", C["sub"], 10.5,
                 anchor="middle"))
    s.append(f'<rect x="{rx + 20:.1f}" y="{top + 100:.1f}" '
             f'width="{rw - 40:.1f}" height="1" fill="{C["edge"]}"/>')
    s.append('<g class="rv">'
             + txt(rx + 20, top + 115, "longest", C["mauve"], 11)
             + txt(rx + rw - 20, top + 115, f"{best} days", C["text"], 11,
                   "700", anchor="end") + "</g>")

    # ---- barres de langages
    y = top + card_h + 10
    bar_x = pad + 13 * ch
    bar_w = W - bar_x - pad - 62
    for n, (name, pctv) in enumerate(langs):
        y += lh
        s.append(txt(pad, y, name, C["teal"], fs))
        s.append(f'<rect x="{bar_x:.1f}" y="{y - 8:.1f}" width="{bar_w:.1f}" '
                 f'height="7" rx="3.5" fill="{C["line"]}"/>')
        col = [C["blue"], C["yellow"], C["mauve"], C["green"], C["peach"],
               C["red"], C["teal"]][n % 7]
        s.append(f'<rect x="{bar_x:.1f}" y="{y - 8:.1f}" '
                 f'width="{max(bar_w * pctv / 100.0, 2):.1f}" height="7" '
                 f'rx="3.5" fill="{col}"/>')
        s.append(wipe(bar_x - .5, y - 9.5, bar_w + 2, 10, .3 + n * .1, .85))
        s.append(txt(W - pad, y, f"{pctv:.1f}%", C["sub"], 11.5, anchor="end"))
    s.append("</svg>")
    (OUT / "stats.svg").write_text("".join(s), encoding="utf-8")


# -------------------------------------------------- 7. pacman + contributions

def streaks(weeks: list[dict]) -> tuple[int, int]:
    """(serie en cours, plus longue serie) sur le calendrier fourni.

    La serie en cours tolere un dernier jour vide : la journee n'est pas
    finie, et un profil ne doit pas afficher 0 a 9h du matin.
    """
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
            continue  # aujourd'hui pas encore commence
        else:
            break
    return cur, best


# Police pixel 5x7, seulement les lettres dont j'ai besoin.
PIXFONT = {
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "N": ("10001", "11001", "11001", "10101", "10011", "10011", "10001"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    " ": ("00000",) * 7,
}


def pixel_text(word, x, y, u, fill):
    """Ecrit un mot en blocs de u pixels, un <path> par mot."""
    subs = []
    for i, chx in enumerate(word):
        rows = PIXFONT.get(chx, PIXFONT[" "])
        ox = x + i * 6 * u
        for ry, row in enumerate(rows):
            cx_ = None
            for rx in range(6):
                on = rx < 5 and row[rx] == "1"
                if on and cx_ is None:
                    cx_ = rx
                elif not on and cx_ is not None:
                    subs.append("M%.1f %.1fh%.1fv%.1fh-%.1fz"
                                % (ox + cx_ * u, y + ry * u, (rx - cx_) * u,
                                   u, (rx - cx_) * u))
                    cx_ = None
    return '<path fill="%s" d="%s"/>' % (fill, "".join(subs))


def pixel_width(word, u):
    return len(word) * 6 * u


STYLE_MARK = "@@CSS@@"


def gen_pacman(gh: dict) -> None:
    """Une partie de Pac-Man jouee sur mon graphe de contributions.

      0.00-0.40  il serpente les lignes 0 a 3 et mange. Les 4 fantomes le
                 collent, en meute serree.
      0.40       il gobe la super pac-gomme au bout de la ligne 3.
      0.40-0.70  phase bleue : les fantomes fuient aux quatre coins, il fait
                 le tour du perimetre et les mange un par un (200, 400, 800,
                 1600 points).
      0.70-1.00  retour a la normale, lignes 4 a 6.

    Tout est axe : jamais de diagonale, sinon ca ne ressemble plus a un jeu
    de grille. La choregraphie est en fractions de boucle, pas en secondes.

    Deux pieges rencontres et corriges :

    - Le retournement du sprite ne peut pas etre un simple scaleX pose sur
      chaque point : CSS interpole, donc Pac-Man passait continument de -1 a
      1 en s'ecrasant a plat au milieu du trajet. Chaque virage recoit donc
      une keyframe doublee, un cheveu avant, pour que le flip soit instantane.
    - Le bleu d'effroi d'origine (#2121de) disparait sur fond sombre. Il est
      eclairci, et les fantomes ont un contour.
    """
    from math import hypot

    cal = gh["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    pad, cell, gap = 17.0, 12.0, 3.0
    cols = len(weeks)
    scale = min(1.0, (W - 2 * pad) / (cols * (cell + gap) - gap))
    cell *= scale
    gap *= scale
    step = cell + gap
    grid_w = cols * step - gap
    grid_h = 7 * step - gap
    x0 = (W - grid_w) / 2
    y0 = pad + 26
    h = y0 + grid_h + 32
    ROWS, LOOP, last = 7, 26.0, cols - 1

    def px(ci):
        return x0 + ci * step + cell / 2

    def py(ri):
        return y0 + ri * step + cell / 2

    def polyline(t0, t1, pts):
        """Repartit [t0,t1] proportionnellement aux longueurs : sinon un saut
        d'une ligne durerait aussi longtemps qu'une traversee."""
        P = [(px(a), py(b)) for a, b in pts]
        d = [0.0]
        for k in range(1, len(P)):
            d.append(d[-1] + hypot(P[k][0] - P[k - 1][0], P[k][1] - P[k - 1][1]))
        tot = d[-1] or 1.0
        return [(t0 + (t1 - t0) * d[k] / tot, P[k][0], P[k][1])
                for k in range(len(P))]

    A_END, C_END, WIN = 0.36, 0.62, 0.86
    ptsA = []
    for k, r in enumerate([0, 1, 2, 3]):
        ptsA += [(0, r), (last, r)] if k % 2 == 0 else [(last, r), (0, r)]
    # tour du perimetre : que des deplacements axes, comme dans un vrai jeu
    corners = [(0, 0), (last, 0), (last, ROWS - 1), (0, ROWS - 1)]
    ptsC = [(0, 3)] + corners + [(0, 4)]
    ptsD = []
    for k, r in enumerate([4, 5, 6]):
        ptsD += [(0, r), (last, r)] if k % 2 == 0 else [(last, r), (0, r)]

    wayA = polyline(0.0, A_END, ptsA)
    wayC = polyline(A_END, C_END, ptsC)
    wayD = polyline(C_END, WIN, ptsD)
    way = wayA + wayC[1:] + wayD[1:]
    eat_t = [wayC[1 + k][0] for k in range(4)]

    def at(t):
        if t <= way[0][0]:
            return way[0][1], way[0][2]
        for k in range(1, len(way)):
            if t <= way[k][0]:
                t0, xa, ya = way[k - 1]
                t1, xb, yb = way[k]
                f = (t - t0) / ((t1 - t0) or 1)
                return xa + (xb - xa) * f, ya + (yb - ya) * f
        return way[-1][1], way[-1][2]

    def frames(pts, flip=True):
        """Keyframes transform, avec flip instantane aux virages.

        Pour chaque point on connait la direction du segment QUI PART de lui.
        On pose donc, un cheveu avant le point, une keyframe qui garde encore
        la direction precedente : le scaleX bascule d'un coup au lieu d'etre
        interpole en passant par zero."""
        dirs = []
        for k in range(len(pts)):
            nx = pts[min(k + 1, len(pts) - 1)][1]
            # Le sprite est dessine bouche a GAUCHE (verifie au rendu, mon
            # raisonnement sur le sens de l'arc etait faux) : c'est donc
            # scaleX(-1) qui le fait regarder a droite.
            d = 1 if (flip and nx < pts[k][1] - .5) else -1
            dirs.append(d)
        out, prev = [], dirs[0]
        for k, (t, x, y) in enumerate(pts):
            if dirs[k] != prev and t > 0.0005:
                out.append("%.4f%%{transform:translate(%.1fpx,%.1fpx) "
                           "scaleX(%d)}" % ((t - .0004) * 100, x, y, prev))
            out.append("%.4f%%{transform:translate(%.1fpx,%.1fpx) scaleX(%d)}"
                       % (t * 100, x, y, dirs[k]))
            prev = dirs[k]
        return "".join(out)

    css = ["@keyframes pac{%s}" % frames(way),
           ".pac{animation:pac %ss linear infinite}" % LOOP,
           # Sans ca, il saute de la fin de la ligne 6 (a droite) au debut de
           # la ligne 0 (a gauche) a chaque boucle. On le masque derriere
           # l'ecran de fin, et la boucle redemarre proprement.
           "@keyframes pacv{0%%,%.2f%%{opacity:1}%.2f%%,99.5%%{opacity:0}"
           "100%%{opacity:1}}" % (WIN * 100, WIN * 100 + .6),
           ".pacv{animation:pacv %ss linear infinite}" % LOOP,
           "@keyframes chomp{0%,49%{transform:scaleY(1)}"
           "50%,100%{transform:scaleY(.4)}}",
           ".jaw{animation:chomp .26s steps(2,end) infinite}"]

    # ---- les cases s'eteignent quand il passe reellement dessus
    SAMPLES = 1600
    reach = cell * .8
    hit = {}
    for n in range(SAMPLES + 1):
        t = n / SAMPLES
        hx, hy = at(t)
        ci = int(round((hx - x0 - cell / 2) / step))
        ri = int(round((hy - y0 - cell / 2) / step))
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                c, r = ci + dc, ri + dr
                if not (0 <= c < cols and 0 <= r < ROWS) or (c, r) in hit:
                    continue
                if hypot(hx - px(c), hy - py(r)) <= reach:
                    hit[(c, r)] = t
    # Les cases repoussent pendant l'ecran de fin, au lieu de se rallumer
    # d'un coup a la boucle : c'etait un des sauts d'image.
    REGROW = 93.0
    for (c, r), t in hit.items():
        a = max(t * 100 - .3, 0.0)
        b = min(t * 100 + .3, 99.0)
        css.append("@keyframes k%d_%d{0%%,%.3f%%{opacity:1}"
                   "%.3f%%,%.1f%%{opacity:.1}100%%{opacity:1}}"
                   % (c, r, a, b, REGROW))
        css.append(".k%d_%d{animation:k%d_%d %ss linear infinite}"
                   % (c, r, c, r, LOOP))

    # ---- les 4 fantomes, en meute serree (un tiers de ligne au plus)
    GHOSTS = [(C["red"], .010), ("#ffb8ff", .019),
              ("#4fd6ff", .028), (C["peach"], .037)]
    BLUE, INK = "#5571ff", "#0b0d16"
    mx, my = px(last / 2), py(3)
    for gi, (col, lag) in enumerate(GHOSTS):
        te = eat_t[gi]
        cxg, cyg = px(corners[gi][0]), py(corners[gi][1])
        hx, hy = at(A_END - lag)
        pts = [(0.0, at(0.0)[0], at(0.0)[1])]
        pts += [(t + lag, x, y) for t, x, y in wayA if 0 < t + lag < A_END]
        pts.append((A_END, hx, hy))
        # fuite vers son coin, en L : vertical puis horizontal, jamais en biais
        pts.append((A_END + .030, hx, cyg))
        pts.append((A_END + .060, cxg, cyg))
        pts.append((te, cxg, cyg))
        # Le retour au centre doit avoir lieu APRES la disparition complete
        # (opacite nulle a te+0.3%), sinon on voyait le fantome sauter.
        pts.append((min(te + .006, C_END - .005), mx, my))
        pts.append((C_END, mx, my))
        pts += [(t + lag, x, y) for t, x, y in wayD if C_END < t + lag < WIN]
        pts.append((WIN, at(WIN - lag)[0], at(WIN - lag)[1]))
        pts.append((1.0, at(WIN - lag)[0], at(WIN - lag)[1]))
        seen, uniq = set(), []
        for q in sorted(pts, key=lambda z: z[0]):
            key = round(q[0], 5)
            if key not in seen:
                seen.add(key)
                uniq.append(q)
        css.append("@keyframes g%d{%s}" % (gi, frames(uniq, flip=False)))
        css.append(".g%d{animation:g%d %ss linear infinite}" % (gi, gi, LOOP))
        css.append("@keyframes c%d{0%%,%.2f%%{fill:%s}%.2f%%,%.2f%%{fill:%s}"
                   "%.2f%%,100%%{fill:%s}}"
                   % (gi, A_END * 100, col, A_END * 100 + .4, te * 100, BLUE,
                      C_END * 100, col))
        css.append(".c%d{animation:c%d %ss linear infinite}" % (gi, gi, LOOP))
        css.append("@keyframes v%d{0%%,%.2f%%{opacity:1}%.2f%%,%.2f%%{opacity:0}"
                   "%.2f%%,%.2f%%{opacity:1}%.2f%%,100%%{opacity:0}}"
                   % (gi, te * 100, te * 100 + .3, C_END * 100 - 1.5,
                      C_END * 100, WIN * 100, WIN * 100 + .6))
        css.append(".v%d{animation:v%d %ss linear infinite}" % (gi, gi, LOOP))
        css.append("@keyframes s%d{0%%,%.2f%%{opacity:0;transform:none}"
                   "%.2f%%{opacity:1}%.2f%%,100%%{opacity:0;"
                   "transform:translateY(-16px)}}"
                   % (gi, te * 100, te * 100 + .4, te * 100 + 4))
        css.append(".s%d{animation:s%d %ss linear infinite}" % (gi, gi, LOOP))

    css.append("@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}"
               "50%{opacity:.7;transform:scale(1.45)}}")
    css.append("@keyframes gone{0%%,%.2f%%{opacity:1}%.2f%%,100%%{opacity:0}}"
               % (A_END * 100, A_END * 100 + .4))
    css.append(".pell{animation:pulse .7s ease-in-out infinite}"
               ".pellw{animation:gone %ss linear infinite}" % LOOP)

    pal = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
    hi = max((d["contributionCount"] for wk in weeks
              for d in wk["contributionDays"]), default=1) or 1
    cur, best = streaks(weeks)

    s = [head(W, h, "Une partie de Pac-Man sur mon graphe de contributions"),
         panel(W, h), "<style>" + STYLE_MARK + "</style>",
         txt(pad, pad + 13, "./contrib-eater --sprite=pacman --ghosts=4",
             C["green"], 12),
         txt(W - pad, pad + 13,
             "%s contributions \u00b7 streak %sd \u00b7 best %sd"
             % (cal["totalContributions"], cur, best),
             C["dim"], 10.5, anchor="end")]

    for ci, wk in enumerate(weeks):
        for ri, d in enumerate(wk["contributionDays"]):
            v = d["contributionCount"]
            lvl = 0 if v == 0 else min(4, 1 + int(3.0 * v / hi))
            cls = ' class="k%d_%d"' % (ci, ri) if v and (ci, ri) in hit else ""
            s.append('<rect%s x="%.2f" y="%.2f" width="%.2f" height="%.2f" '
                     'rx="%.2f" fill="%s"/>'
                     % (cls, x0 + ci * step, y0 + ri * step, cell, cell,
                        cell * .22, pal[lvl]))

    # Le cercle est a l'origine d'un groupe translate : un transform:scale
    # sur un <circle> positionne par cx/cy met a l'echelle depuis l'origine
    # du SVG et le DEPLACE, au lieu de le faire pulser sur place.
    s.append('<g transform="translate(%.2f,%.2f)"><g class="pellw">'
             '<g class="pell"><circle r="4.6" fill="%s"/></g></g></g>'
             % (px(0), py(3), C["yellow"]))

    for gi, (col, lag) in enumerate(GHOSTS):
        g = cell * .72
        s.append('<g class="g%d"><g class="v%d">'
                 '<path class="c%d" fill="%s" stroke="%s" stroke-width="1.4" '
                 'd="M%.2f %.2fV0A%.2f %.2f 0 0 1 %.2f 0V%.2f'
                 'l%.2f %.2fl%.2f %.2fl%.2f %.2fZ"/>'
                 '<circle cx="%.2f" cy="%.2f" r="%.2f" fill="#f8f8ff"/>'
                 '<circle cx="%.2f" cy="%.2f" r="%.2f" fill="#f8f8ff"/>'
                 '<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s"/>'
                 '<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s"/>'
                 '</g></g>'
                 % (gi, gi, gi, col, INK, -g, g * .55, g, g, g, g * .55,
                    -g * .5, g * .28, -g * .5, -g * .28, -g * .5, g * .28,
                    -g * .33, -g * .18, g * .27, g * .33, -g * .18, g * .27,
                    -g * .33, -g * .18, g * .13, INK,
                    g * .33, -g * .18, g * .13, INK))

    r = cell * .78
    s.append('<g class="pacv"><g class="pac"><g class="jaw">'
             '<path d="M0 0L%.2f %.2fA%.2f %.2f 0 1 0 %.2f %.2fZ" fill="%s"/>'
             '</g></g></g>' % (r, -r * .58, r, r, r, r * .58, C["yellow"]))

    for gi, score in enumerate((200, 400, 800, 1600)):
        cxs, cys = px(corners[gi][0]), py(corners[gi][1])
        s.append('<g class="s%d">' % gi
                 + txt(cxs, cys - 11, str(score), "#7ef0ff", 11, "700", "middle")
                 + "</g>")

    # ---- l'ecran de fin
    word = "CONGRATULATIONS!"
    u = 3.3
    wpx = pixel_width(word, u)
    wy = y0 + grid_h / 2 - 7 * u / 2 - 7
    css.append("@keyframes win{0%%,%.2f%%{opacity:0}%.2f%%,99%%{opacity:1}"
               "100%%{opacity:0}}" % (WIN * 100, WIN * 100 + 1.2))
    css.append(".win{animation:win %ss linear infinite}" % LOOP)
    css.append("@keyframes wink{0%,100%{opacity:1}50%{opacity:.25}}")
    css.append(".wink{animation:wink .5s steps(1,end) infinite}")
    s.append('<g class="win"><g class="wink">'
             + pixel_text(word, (W - wpx) / 2, wy, u, C["yellow"])
             + "</g>"
             + txt(W / 2, wy + 7 * u + 20,
                   "%s contributions cleared" % cal["totalContributions"],
                   "#7ef0ff", 11.5, "700", "middle")
             + "</g>")

    s.append("</svg>")
    # le CSS a grossi apres coup : on le reinjecte
    out = "".join(s).replace("<style>%s</style>" % STYLE_MARK,
                             "<style>%s</style>" % "".join(css))
    (OUT / "contrib-pacman.svg").write_text(out, encoding="utf-8")


# --------------------------------------------------------- 8. etoile filante

def gen_star() -> None:
    star = (ASCII / "etoile-joestar.txt").read_text(encoding="utf-8")
    ono = (ASCII / "jojo-onomatope.txt").read_text(encoding="utf-8")
    dot = 1.7
    sw, sh = braille_size(star, dot)
    ow, oh = braille_size(ono, dot)
    h = max(sh, oh) + 54
    LOOP = 9.0

    s = [head(W, h, "etoile filante Joestar"), panel(W, h)]
    s.append("<style>"
             f"@keyframes fly{{from{{transform:translate({-(sw+ow*2.2):.0f}px,"
             f"{h*.32:.0f}px)}}to{{transform:translate({W + 30}px,"
             f"{-h*.30:.0f}px)}}}}"
             f".fly{{animation:fly {LOOP}s linear infinite}}"
             "</style>")
    s.append('<g class="fly">')
    # la trainee : trois copies de plus en plus effacees, derriere l'etoile
    for k, op in ((2.05, .10), (1.35, .22), (.70, .44)):
        s.append(f'<g opacity="{op}">'
                 + braille_rects(ono, -ow * k, (sh - oh) / 2 + 16, dot,
                                 C["red"], .3) + "</g>")
    s.append(braille_rects(star, 0, 10, dot, C["yellow"], .3))
    s.append("</g>")
    s.append("</svg>")
    (OUT / "star-trail.svg").write_text("".join(s), encoding="utf-8")


# ---------------------------------------------------------------- main

def main() -> None:
    cfg = json.loads((DATA / "profile.json").read_text(encoding="utf-8"))
    if "--fetch" in sys.argv:
        fetch(os.environ.get("GH_LOGIN", "CodeByHaamza"))
    gh = load_gh()
    OUT.mkdir(parents=True, exist_ok=True)

    gen_header(cfg)
    gen_links(cfg)
    gen_prompts(cfg)
    gen_whoami(cfg)
    gen_neofetch(cfg)
    gen_stack(cfg)
    gen_projects(cfg)
    gen_funfacts(cfg)
    gen_stats(cfg, gh)
    gen_pacman(gh)
    gen_star()

    for f in sorted(OUT.glob("*.svg")):
        print(f"{f.name:22} {f.stat().st_size / 1024:7.1f} Ko")


if __name__ == "__main__":
    main()
