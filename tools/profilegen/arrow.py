"""La Flèche du Stand : un visiteur ouvre une issue, la Flèche le transperce, il reçoit un Stand.

Ce module dessine les cartes des Stands (avec l'évolution animée pour les actes et les
Requiem), le bouton du README et le tableau des Stand users. Bibliothèque standard
uniquement : il sert aussi au workflow stand-arrow, qui n'a rien d'autre d'installé.
"""
from __future__ import annotations

import html
import json
import math
import random
import urllib.parse
from pathlib import Path

from . import fx
from .kit import DATA, REDUCE, REPO_URL, ROOT, SERIF, Font, data_uri, esc, poly, txt, wrap, write

STANDS_DIR = ROOT / "assets" / "stands"
CARDS = STANDS_DIR / "cards"
LOG = DATA / "stand-users.json"
START, END = "<!-- stand-arrow start -->", "<!-- stand-arrow end -->"

INK, GOLD, VIOLET, PAPER = "#120a1f", "#f2c14e", "#8a3cff", "#fff8ea"
CW, CH = 860, 300
STAGE = 4.2  # secondes par étape d'évolution


def load_stands() -> list[dict]:
    return json.loads((DATA / "stands.json").read_text(encoding="utf-8"))["stands"]


def load_log() -> list[dict]:
    return json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else []


def issue_url() -> str:
    q = urllib.parse.urlencode({
        "title": "arrow: pierce me",
        "body": "Just press **Create** (or **Submit new issue**).\n\nA GitHub Action shoots the Stand Arrow at you and "
                "replies here within a minute or two with the Stand you awakened. One arrow per visitor per day.",
    }, quote_via=urllib.parse.quote)
    return f"{REPO_URL}/issues/new?{q}"


def card_url(stand_id: str) -> str:
    return f"{REPO_URL}/raw/main/assets/stands/cards/{stand_id}.svg"


# ---------------------------------------------------------------- la carte d'un Stand

def _pc(t: float, period: float) -> str:
    return f"{max(0, min(100, t / period * 100)):.2f}%"


def _image(stage_id: str, cx: float, cy: float, size: float) -> str:
    f = STANDS_DIR / f"{stage_id}.png"
    if f.exists():
        return (f'<image href="{data_uri(f)}" x="{cx - size / 2:.0f}" y="{cy - size / 2:.0f}" width="{size:.0f}" '
                f'height="{size:.0f}" preserveAspectRatio="xMidYMid meet"/>')
    # pas encore d'image : une silhouette de Stand et ses onomatopées
    return (f'<circle cx="{cx}" cy="{cy}" r="{size * .3:.0f}" fill="{VIOLET}" opacity=".35"/>'
            f'<text x="{cx}" y="{cy + size * .12:.0f}" text-anchor="middle" font-size="{size * .4:.0f}" font-weight="900" '
            f'fill="{GOLD}" font-family="{SERIF}">?</text>')


def card(stand: dict) -> str:
    D, A = Font("dela", "cd"), Font("anton", "ca")
    rnd = random.Random(stand["id"])
    stages = stand["stages"]
    n = len(stages)
    period = n * STAGE
    cx, cy, isz = 190, 150, 250
    b, css = [], []
    defs = (f'<radialGradient id="bg" cx=".22" cy=".5" r=".85"><stop offset="0" stop-color="#5b2a8c"/>'
            f'<stop offset=".55" stop-color="#2a1245"/><stop offset="1" stop-color="{INK}"/></radialGradient>'
            f'<radialGradient id="halo" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="{GOLD}" stop-opacity=".55"/>'
            f'<stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>'
            f'<pattern id="dots" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(30)">'
            f'<circle cx="3.5" cy="3.5" r="1.1" fill="#fff" opacity=".08"/></pattern>'
            f'<clipPath id="cc"><rect width="{CW}" height="{CH}" rx="16"/></clipPath>')
    b.append(f'<g clip-path="url(#cc)"><rect width="{CW}" height="{CH}" fill="url(#bg)"/><rect width="{CW}" height="{CH}" fill="url(#dots)"/>')
    # lignes de vitesse qui tournent lentement derrière le Stand
    rays = []
    for i in range(40):
        a = i * 2 * math.pi / 40 + rnd.uniform(-.05, .05)
        da = rnd.uniform(.01, .025)
        rays.append(poly([(cx, cy), (cx + 700 * math.cos(a - da), cy + 700 * math.sin(a - da)),
                          (cx + 700 * math.cos(a + da), cy + 700 * math.sin(a + da))]))
    css.append(f"@keyframes rays{{to{{transform:rotate(360deg)}}}}.rays{{transform-origin:{cx}px {cy}px;animation:rays 60s linear infinite}}")
    b.append('<g class="rays" fill="#fff" opacity=".05">' + "".join(f'<polygon points="{p}"/>' for p in rays) + "</g>")
    b.append(f'<circle cx="{cx}" cy="{cy}" r="150" fill="url(#halo)"/>')
    css.append(f"@keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-6px)}}}}"
               f".bob{{animation:bob 3.2s ease-in-out infinite}}")
    x0 = 368
    b.append(A.text("STAND", x0, 58, 16, GOLD, track=6))
    b.append(A.text(f"PART {stand['part']}", 830, 58, 16, GOLD, anchor="end", track=4))
    fx_defs, fx_layers = [], []
    for i, s in enumerate(stages):
        name = s["name"].upper()
        size = D.fit(name, 38, 460, floor=18)
        lines = wrap(s["text"], 52)[:3]
        img_id = f"si{i}"
        fx_defs.append(f'<g id="{img_id}">{_image(s["id"], cx, cy, isz)}</g>')
        # l'effet d'apparition, lié au pouvoir du Stand : une fois au chargement, ou à chaque étape
        if n > 1:
            ctx = fx.Ctx(f"x{i}_", cx, cy, i * STAGE, period, True, s["id"], D, img_id)
        else:
            ctx = fx.Ctx(f"x{i}_", cx, cy, .1, fx.DURATION + 1.3, False, s["id"], D, img_id)
        fx_layers.append(fx.render(s.get("fx"), ctx))
        fx_defs += ctx.defs
        css += ctx.css
        image = f'<g class="bob"><use href="#{img_id}"/></g>'
        if n == 1:  # le Stand apparaît une fois l'effet lancé
            image = f'<g class="appear" style="transform-origin:{cx}px {cy}px">{image}</g>'
            css.append("@keyframes appear{0%,55%{opacity:0;transform:scale(.75)}100%{opacity:1;transform:none}}"
                       ".appear{animation:appear 1.5s cubic-bezier(.2,1.3,.4,1) both}")
        g = [image,
             D.text(name, x0, 108, size, "#fff", INK, 6, skew=-6),
             A.text(f"STAND USER  ·  {stand['user'].upper()}", x0, 140, 15, GOLD, track=1.5)]
        for k, ln in enumerate(lines):
            g.append(txt(x0, 182 + k * 22, ln, PAPER, 16, 600, italic=True, family=SERIF))
        if n > 1:  # les étapes, en pastilles
            for j in range(n):
                g.append(f'<circle cx="{x0 + 8 + j * 22}" cy="262" r="6.5" fill="{GOLD if j == i else "none"}" '
                         f'stroke="{GOLD}" stroke-width="2"/>')
            g.append(A.text("REQUIEM" if stand.get("evolution") == "requiem" and i == n - 1 else f"STAGE {i + 1}/{n}",
                            x0 + 8 + n * 22, 268, 14, GOLD, track=3))
        visible = "opacity:1" if i == 0 else "opacity:0"
        if n > 1:
            t0, t1 = i * STAGE, (i + 1) * STAGE
            frames = [(0, "opacity:0"), (max(0, t0 - .01), "opacity:0"), (t0, "opacity:1"), (t1 - .25, "opacity:1"),
                      (t1, "opacity:0"), (period, "opacity:0")]
            if i == 0:
                frames = [(0, "opacity:1"), (t1 - .25, "opacity:1"), (t1, "opacity:0"), (period - .01, "opacity:0"), (period, "opacity:1")]
            css.append(f"@keyframes st{i}{{" + "".join(f"{_pc(t, period)}{{{c}}}" for t, c in frames) + "}"
                       f".st{i}{{{visible};animation:st{i} {period}s linear infinite}}")
            b.append(f'<g class="st{i}">' + "".join(g) + "</g>")
        else:
            b.append("".join(g))
    # les effets restent dans la zone de l'image : le nom et la phrase du Stand ne sont jamais recouverts
    b.append(f'<g clip-path="url(#fxclip)">' + "".join(fx_layers) + "</g>")
    defs += "".join(fx_defs) + f'<clipPath id="fxclip"><rect width="354" height="{CH}"/></clipPath>'
    # le passage d'une étape à la suivante : flash, et le mot qui claque (ou la flèche Requiem qui transperce)
    if n > 1:
        for i in range(n - 1):
            t = (i + 1) * STAGE
            req = stand.get("evolution") == "requiem"
            word = (stages[i + 1].get("burst") or ("REQUIEM!" if req else f"ACT {i + 2}!" if stand["id"] in ("echoes", "tusk")
                                                   else "EVOLUTION!"))
            css.append(f"@keyframes fl{i}{{0%,{_pc(t - .3, period)}{{opacity:0}}{_pc(t, period)}{{opacity:.95}}"
                       f"{_pc(t + .5, period)},100%{{opacity:0}}}}.fl{i}{{opacity:0;animation:fl{i} {period}s linear infinite}}")
            b.append(f'<rect class="fl{i}" width="{CW}" height="{CH}" fill="#fff"/>')
            css.append(f"@keyframes bw{i}{{0%,{_pc(t - .1, period)}{{opacity:0;transform:scale(2.2)}}"
                       f"{_pc(t + .2, period)}{{opacity:1;transform:scale(1)}}{_pc(t + 1.1, period)}{{opacity:1;transform:scale(1)}}"
                       f"{_pc(t + 1.5, period)},100%{{opacity:0;transform:scale(1)}}}}"
                       f".bw{i}{{opacity:0;transform-origin:{cx}px 268px;animation:bw{i} {period}s linear infinite}}")
            b.append(f'<g class="bw{i}">' + D.text(word, cx, 280, 26, GOLD, INK, 5, anchor="middle", skew=-8) + "</g>")
            if req and (ROOT / "assets" / "arrow-requiem.png").exists():
                css.append(f"@keyframes ar{i}{{0%,{_pc(t - 1.1, period)}{{opacity:0;transform:translate(260px,-200px)}}"
                           f"{_pc(t - 1.0, period)}{{opacity:1;transform:translate(260px,-200px)}}"
                           f"{_pc(t - .05, period)}{{opacity:1;transform:translate(0,0)}}{_pc(t + .15, period)},100%{{opacity:0;transform:translate(0,0)}}}}"
                           f".ar{i}{{opacity:0;animation:ar{i} {period}s cubic-bezier(.5,0,.9,.4) infinite}}")
                b.append(f'<g class="ar{i}"><image href="{data_uri(ROOT / "assets" / "arrow-requiem.png")}" x="{cx - 20}" '
                         f'y="{cy - 120}" width="150" height="150"/></g>')
    # ゴゴゴ
    css.append("@keyframes gogo{0%,100%{transform:translate(0,0)}25%{transform:translate(-1.5px,1px)}50%{transform:translate(1px,-1.5px)}"
               "75%{transform:translate(1.5px,1px)}}.gogo{animation:gogo .9s steps(2) infinite}")
    for k in range(3):
        x, y = 742 + k * 30, 250 + (k % 2) * 18
        b.append(f'<g class="gogo" style="animation-delay:{k * .2:.1f}s;transform-origin:{x}px {y}px">'
                 + D.text("ゴ", x, y, 28 - k * 3, VIOLET, INK, 2.5, anchor="middle", skew=-12) + "</g>")
    b.append(f'<rect x="1.5" y="1.5" width="{CW - 3}" height="{CH - 3}" rx="15" fill="none" stroke="{GOLD}" stroke-width="3"/></g>')
    names = " → ".join(s["name"] for s in stages)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH}" width="{CW}" height="{CH}" role="img">'
            f'<title>{esc(names)}</title><desc>{esc(" ".join(s["text"] for s in stages))}</desc>'
            f"<defs>{defs}{D.defs()}{A.defs()}</defs><style>{''.join(css)}{REDUCE}</style>" + "".join(b) + "</svg>")


EXAMPLE = "gold-experience"  # la carte montrée tant que personne n'a tiré


def build_card(stand_id: str) -> Path:
    """Écrit la carte d'un Stand (si elle a changé) et renvoie son chemin."""
    CARDS.mkdir(parents=True, exist_ok=True)
    st = next(s for s in load_stands() if s["id"] == stand_id)
    svg = card(st)
    f = CARDS / f"{stand_id}.svg"
    if not f.exists() or f.read_text(encoding="utf-8") != svg:
        f.write_text(svg, encoding="utf-8")
    return f


def build_cards() -> None:
    """Les cartes ne sont faites que pour les Stands déjà tirés (et l'exemple) : avec plus de 160 Stands,
    on ne stocke pas une carte animée par Stand d'avance. Le workflow fait la carte du Stand tiré."""
    wanted = {r["stand"] for r in load_log()} | {EXAMPLE}
    known = {s["id"] for s in load_stands()}
    for sid in sorted(wanted & known):
        build_card(sid)
    for f in CARDS.glob("*.svg"):
        if f.stem not in wanted:
            f.unlink()


# ---------------------------------------------------------------- le bouton du README

def button() -> None:
    D, A = Font("dela", "bd"), Font("anton", "ba")
    w, h = 560, 120
    arrow = ROOT / "assets" / "arrow-stand.png"
    b = [f'<rect x="2" y="2" width="{w - 4}" height="{h - 4}" rx="16" fill="{INK}" stroke="{GOLD}" stroke-width="3"/>']
    if arrow.exists():
        b.append(f'<g class="shake"><image href="{data_uri(arrow)}" x="18" y="22" width="220" height="77"/></g>')
    b.append(D.text("GET PIERCED", 250, 62, 32, "#fff", INK, 4, skew=-8))
    b.append(A.text("BY THE STAND ARROW  ▶", 252, 94, 20, GOLD, track=3))
    css = ("@keyframes shake{0%,100%{transform:translate(0,0) rotate(0)}20%{transform:translate(-3px,1px) rotate(-1.5deg)}"
           "40%{transform:translate(10px,-1px) rotate(1deg)}60%{transform:translate(-2px,1px)}80%{transform:translate(2px,0)}}"
           ".shake{transform-origin:128px 60px;animation:shake 1.618s ease-in-out infinite}")
    write("arrow-button.svg", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">'
          f"<title>Get pierced by the Stand Arrow</title><defs>{D.defs()}{A.defs()}</defs><style>{css}{REDUCE}</style>"
          + "".join(b) + "</svg>")


# ---------------------------------------------------------------- le bloc du README

def readme_block(log: list[dict] | None = None) -> str:
    log = load_log() if log is None else log
    stands = {s["id"]: s for s in load_stands()}
    awakened = len({r["stand"] for r in log})
    out = [START, '<div align="center">', "",
           f'<a href="{html.escape(issue_url(), quote=True)}"><img src="assets/gen/arrow-button.svg" width="460" '
           'alt="Get pierced by the Stand Arrow: opens an issue, a GitHub Action replies with your Stand"></a>', "",
           f"<sub><b>{len(log)}</b> arrows shot · <b>{len({r['user'].lower() for r in log})}</b> Stand users · "
           f"<b>{awakened}/{len(stands)}</b> Stands awakened · one arrow per visitor per day</sub>", "", "</div>", ""]
    if log:
        last = log[-1]
        s = stands.get(last["stand"])
        if s:
            out += [f'<img src="assets/stands/cards/{s["id"]}.svg" width="100%" '
                    f'alt="Latest awakening: @{html.escape(last["user"])} got {html.escape(" → ".join(x["name"] for x in s["stages"]))}">', ""]
        out += ["| Stand user | Stand | Part | Date |", "|:--|:--|:-:|:--|"]
        for r in reversed(log[-10:]):
            s = stands.get(r["stand"])
            if s:
                out.append(f"| [@{r['user']}](https://github.com/{r['user']}) | {' → '.join(x['name'] for x in s['stages'])} "
                           f"| {s['part']} | {r['date']} |")
    else:
        out += ['<img src="assets/stands/cards/gold-experience.svg" width="100%" '
                'alt="Example card: Gold Experience, pierced by the Requiem Arrow, becomes Gold Experience Requiem">', "",
                "<p align=\"center\"><sub>No one has been pierced yet. Be the first.</sub></p>"]
    out.append(END)
    return "\n".join(out)
