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
    """Apparition en cascade, jouee une seule fois (fill: forwards)."""
    out = [f"@keyframes rise{{from{{opacity:0;transform:translate({dx}px,4px)}}"
           f"to{{opacity:1;transform:none}}}}",
           f"{sel}{{opacity:0;animation:rise {dur}s ease-out forwards}}"]
    for i in range(count):
        out.append(f"{sel}:nth-of-type({i+1}){{animation-delay:{i*step:.2f}s}}")
    return "".join(out)


def wipe(x: float, y: float, w: float, h: float, delay: float, dur: float,
         bg: str = None) -> str:
    """Un cache couleur de fond qui glisse vers la droite : effet de frappe."""
    return (f'<rect class="wipe" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
            f'height="{h:.1f}" fill="{bg or C["bg"]}" '
            f'style="animation-delay:{delay:.2f}s;animation-duration:{dur:.2f}s"/>')


WIPE_CSS = ("@keyframes wipe{from{transform:translateX(0)}"
            "to{transform:translateX(102%)}}"
            ".wipe{animation:wipe linear forwards}")

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

def gen_header(cfg: dict) -> None:
    art = (ASCII / "hamza.txt").read_text(encoding="utf-8")
    cw, chh = 9.0, 14.0
    fw, fh = figlet_size(art, cw, chh)
    ident = cfg["identity"]

    fy = 26.0 + 26
    tag_y = fy + fh + 26
    h = tag_y + 20

    s = [head(W, h, "Hamza — profil GitHub"), panel(W, h),
         titlebar(W, f'{ident["handle"]}@{ident["host"]} — {ident["shell"]}')]
    s.append("<style>" + WIPE_CSS +
             "@keyframes fade{from{opacity:0}to{opacity:1}}"
             ".fi{opacity:0;animation:fade .5s ease-out forwards}"
             "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
             ".cur{animation:blink 1.1s steps(1,end) infinite}"
             "</style>")

    # le figlet se devoile de gauche a droite
    s.append(f'<g clip-path="url(#cf)">')
    s.append(figlet_rects(art, (W - fw) / 2, fy, cw, chh,
                          C["blue"], "#3a4a6b"))
    s.append("</g>")
    s.append(f'<clipPath id="cf"><rect x="0" y="{fy-2:.1f}" width="{W}" '
             f'height="{fh+4:.1f}"/></clipPath>')
    s.append(wipe((W - fw) / 2 - 1, fy - 2, fw + 2, fh + 4, 0.0, 1.1))

    s.append(f'<g class="fi" style="animation-delay:1.1s">'
             + txt(W / 2, tag_y, ident["tagline"], C["dim"], 12,
                   anchor="middle") + "</g>")
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
    lines = cfg.get("funfacts", [])
    if not lines:
        return
    fs, lh, pad = 12.0, 19.0, 17.0
    ch = fs * 0.6
    h = pad * 2 + 24 + len(lines) * lh + 4
    i = cfg["identity"]

    s = [head(W, h, "fun facts"), panel(W, h), "<style>" + WIPE_CSS + "</style>"]
    s.append(prompt(pad, pad + 12, "cat fun-facts.txt", i["handle"], i["host"]))

    t, y = .3, pad + 24
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
    repos = gh["repositories"]["nodes"]
    commits = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    prs = cc["totalPullRequestContributions"]
    issues = cc["totalIssueContributions"]
    reviews = cc["totalPullRequestReviewContributions"]
    stars = sum(r["stargazerCount"] for r in repos) + 71  # + l'organisation
    followers = gh["followers"]["totalCount"]
    rk = rank(commits, prs, issues, reviews, stars, followers)
    langs = languages(repos)

    fs, pad, lh = 12.0, 17.0, 19.0
    ch = fs * 0.6
    h = pad * 2 + 24 + 2 * lh + 14 + len(langs) * lh + 10

    s = [head(W, h, "mes statistiques GitHub"), panel(W, h),
         "<style>" + WIPE_CSS + reveal_css(".rv", 8, step=.07) + "</style>"]
    i = cfg["identity"]
    s.append(prompt(pad, pad + 12, "git stats --self-hosted",
                    i["handle"], i["host"]))
    s.append(txt(W - pad, pad + 12, "generated in-repo · no external service",
                 C["faint"], 10, anchor="end"))

    y = pad + 30 + lh
    cells = [("rank", rk, C["yellow"]), ("commits", f"{commits:,}".replace(",", " "), C["text"]),
             ("stars", str(stars), C["text"]), ("PRs", str(prs), C["text"])]
    x = pad
    for k, v, col in cells:
        s.append('<g class="rv">' + txt(x, y, k, C["mauve"], fs)
                 + txt(x + (len(k) + 1) * ch, y, v, col, fs, "700") + "</g>")
        x += (len(k) + len(v) + 4) * ch + 22
    y += lh
    cells2 = [("repos", str(gh["repositories"]["totalCount"])),
              ("reviews", str(reviews)), ("issues", str(issues)),
              ("followers", str(followers)),
              ("contributions/12mo", f'{cc["contributionCalendar"]["totalContributions"]:,}'.replace(",", " "))]
    x = pad
    for k, v in cells2:
        s.append('<g class="rv">' + txt(x, y, k, C["mauve"], fs)
                 + txt(x + (len(k) + 1) * ch, y, v, C["text"], fs) + "</g>")
        x += (len(k) + len(v) + 4) * ch + 18

    # barres de langages : pleines, puis devoilees par un cache qui glisse
    y += 20
    bar_x = pad + 13 * ch
    bar_w = W - bar_x - pad - 70
    for n, (name, pctv) in enumerate(langs):
        y += lh
        s.append(txt(pad, y, name, C["teal"], fs))
        fillw = max(bar_w * pctv / 100.0, 2)
        s.append(f'<rect x="{bar_x:.1f}" y="{y-8:.1f}" width="{bar_w:.1f}" '
                 f'height="7" rx="3.5" fill="{C["line"]}"/>')
        col = [C["blue"], C["yellow"], C["mauve"], C["green"], C["peach"],
               C["red"], C["teal"]][n % 7]
        s.append(f'<rect x="{bar_x:.1f}" y="{y-8:.1f}" width="{fillw:.1f}" '
                 f'height="7" rx="3.5" fill="{col}"/>')
        s.append(wipe(bar_x - .5, y - 9, bar_w + 2, 9, .25 + n * .1, .85))
        s.append(txt(W - pad, y, f"{pctv:.1f}%", C["sub"], 11.5, anchor="end"))
    s.append("</svg>")
    (OUT / "stats.svg").write_text("".join(s), encoding="utf-8")


# -------------------------------------------------- 7. pacman + contributions

def gen_pacman(gh: dict) -> None:
    weeks = gh["contributionsCollection"]["contributionCalendar"]["weeks"]
    pad, cell, gap = 17.0, 12.0, 3.0
    cols = len(weeks)
    grid_w = cols * (cell + gap) - gap
    scale = min(1.0, (W - 2 * pad) / grid_w)
    cell *= scale
    gap *= scale
    grid_w = cols * (cell + gap) - gap
    grid_h = 7 * (cell + gap) - gap
    x0 = (W - grid_w) / 2
    y0 = pad + 24
    h = y0 + grid_h + 34

    pal = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
    counts = [d["contributionCount"] for wk in weeks for d in wk["contributionDays"]]
    hi = max(counts) or 1

    LOOP = 14.0  # secondes pour une traversee
    s = [head(W, h, "Pac-Man mange mes contributions"), panel(W, h)]
    s.append("<style>"
             f"@keyframes eat{{0%,100%{{opacity:1}}6%{{opacity:1}}10%,96%{{opacity:.12}}}}"
             f".c{{animation:eat {LOOP}s linear infinite}}"
             f"@keyframes run{{from{{transform:translateX(0)}}"
             f"to{{transform:translateX({grid_w + cell*2:.1f}px)}}}}"
             f".pac{{animation:run {LOOP}s linear infinite}}"
             "@keyframes chomp{0%,49%{transform:scale(1,1)}"
             "50%,100%{transform:scale(1,.45)}}"
             ".jaw{animation:chomp .4s steps(2,end) infinite;"
             "transform-origin:center}"
             "</style>")
    s.append(txt(pad, pad + 12, "./contrib-eater --sprite=pacman", C["green"], 12))
    s.append(txt(W - pad, pad + 12,
                 f'{gh["contributionsCollection"]["contributionCalendar"]["totalContributions"]} contributions, 12 months',
                 C["dim"], 10.5, anchor="end"))

    for ci, wk in enumerate(weeks):
        # chaque colonne s'eteint quand Pac-Man la croise
        delay = -LOOP + (ci / max(cols - 1, 1)) * LOOP
        for ri, d in enumerate(wk["contributionDays"]):
            v = d["contributionCount"]
            lvl = 0 if v == 0 else min(4, 1 + int(3.0 * v / hi))
            x = x0 + ci * (cell + gap)
            y = y0 + ri * (cell + gap)
            cls = ' class="c"' if v else ""
            st = (f' style="animation-delay:{delay:.2f}s"' if v else "")
            s.append(f'<rect{cls}{st} x="{x:.2f}" y="{y:.2f}" '
                     f'width="{cell:.2f}" height="{cell:.2f}" rx="{cell*.22:.2f}" '
                     f'fill="{pal[lvl]}"/>')

    # Pac-Man et deux fantomes, sur la ligne du milieu
    py = y0 + 3 * (cell + gap) + cell / 2
    r = cell * .85
    s.append(f'<g class="pac" transform="translate({x0 - cell*2:.1f},0)">')
    s.append(f'<g class="jaw" transform="translate({0:.1f},{py:.1f})">')
    s.append(f'<path d="M0,0 L{r:.1f},{-r*.62:.1f} A{r:.1f},{r:.1f} 0 1,0 '
             f'{r:.1f},{r*.62:.1f} Z" fill="{C["yellow"]}"/></g>')
    for gi, gc in enumerate((C["red"], C["peach"])):
        gx = -(gi + 1) * cell * 2.4
        s.append(f'<g transform="translate({gx:.1f},{py:.1f})" opacity=".85">'
                 f'<path d="M{-r*.7:.1f},{r*.7:.1f} v{-r*.9:.1f} '
                 f'a{r*.7:.1f},{r*.7:.1f} 0 0 1 {r*1.4:.1f},0 '
                 f'v{r*.9:.1f} l{-r*.23:.1f},{-r*.23:.1f} '
                 f'l{-r*.23:.1f},{r*.23:.1f} l{-r*.24:.1f},{-r*.23:.1f} '
                 f'l{-r*.23:.1f},{r*.23:.1f} l{-r*.24:.1f},{-r*.23:.1f} Z" '
                 f'fill="{gc}"/></g>')
    s.append("</g>")
    s.append("</svg>")
    (OUT / "contrib-pacman.svg").write_text("".join(s), encoding="utf-8")


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
