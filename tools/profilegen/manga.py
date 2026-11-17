"""Style B, la page MANGA.md : un chapitre de manga en noir et blanc, une seule couleur d'accent.

On y arrive en touchant la PSP du profil : la page s'ouvre sur un zoom à travers son écran.
On en repart en touchant la steel ball qui tourne dans la paume.
"""
from __future__ import annotations

import math
import random

from . import art, xmb
from .kit import (DATA, REDUCE, ROOT, SANS, SERIF, W, Font, data_uri, dots, icon, num, poly, save, slug, svg_open,
                  txt, wrap)

PAPER, INK, GREY, SPOT = "#f7f4ec", "#111111", "#6b6b6b", "#8a3cff"
BALL = ROOT / "assets" / "steel-ball.png"


class Page:
    """Un SVG du style manga : feuille blanche, polices, trames, CSS."""

    def __init__(self, name: str, h: float, title: str, desc: str = ""):
        self.name, self.h = name, h
        self.D = Font("dela", "dg")
        self.A = Font("anton", "an")
        self.head = [svg_open(W, h, title, desc)]
        self.defs = [dots("tone", INK, 6, 1.25, 45), dots("tone2", INK, 4.5, 1.5, 45),
                     '<linearGradient id="fadeD" x1="0" y1="0" x2="0" y2="1"><stop offset=".35" stop-color="#fff" stop-opacity="0"/>'
                     '<stop offset="1" stop-color="#fff"/></linearGradient>']
        self.css: list[str] = []
        self.b = [f'<rect width="{W}" height="{h}" rx="14" fill="#fff"/>']

    def write(self, extra_fonts: tuple = ()) -> None:
        css = (CSS + "".join(self.css) + REDUCE)
        fonts = self.D.defs() + self.A.defs() + "".join(f.defs() for f in extra_fonts)
        save(self.name, self.head + ["<defs>"] + self.defs + [fonts, "</defs>", f"<style>{css}</style>"] + self.b)


CSS = ("@keyframes gogo{0%,100%{transform:translate(0,0) scale(1)}25%{transform:translate(-1.5px,1px) scale(1.04)}"
       "50%{transform:translate(1px,-1.5px) scale(.98)}75%{transform:translate(1.5px,1px) scale(1.03)}}"
       ".gogo{animation:gogo .9s steps(2) infinite}"
       "@keyframes pop{0%{transform:scale(0)}70%{transform:scale(1.15)}100%{transform:scale(1)}}.pop{animation:pop .4s ease-out both}"
       "@keyframes grow{from{transform:scale(0)}to{transform:scale(1)}}"
       "@keyframes row{from{transform:translateX(24px);opacity:0}to{transform:none;opacity:1}}.row{animation:row .45s ease-out both}"
       "@keyframes spin{to{transform:rotate(360deg)}}")


def panel(x, y, w, h, fill=PAPER, sw=4) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{INK}" stroke-width="{sw}"/>'


def focus_lines(cx, cy, box, n, rin, rnd, color=INK) -> str:
    """集中線 : des lignes qui convergent vers (cx, cy)."""
    x0, y0, x1, y1 = box
    R = math.hypot(max(cx - x0, x1 - cx), max(cy - y0, y1 - cy)) + 20
    out = []
    for _ in range(n):
        a = rnd.uniform(0, 2 * math.pi)
        da = math.radians(rnd.uniform(.25, 1.1))
        r0 = rin * rnd.uniform(.85, 1.6)
        out.append(poly([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)),
                         (cx + R * math.cos(a - da), cy + R * math.sin(a - da)),
                         (cx + R * math.cos(a + da), cy + R * math.sin(a + da))]))
    return f'<g fill="{color}">' + "".join(f'<polygon points="{p}"/>' for p in out) + "</g>"


def bubble(cx, cy, rx, ry, tail, lines, size=12.5) -> str:
    tx, ty = tail
    a = math.atan2(ty - cy, tx - cx)
    p1 = (cx + rx * .8 * math.cos(a - .22), cy + ry * .8 * math.sin(a - .22))
    p2 = (cx + rx * .8 * math.cos(a + .22), cy + ry * .8 * math.sin(a + .22))
    out = [f'<polygon points="{poly([p1, (tx, ty), p2])}" fill="#fff" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/>',
           f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#fff" stroke="{INK}" stroke-width="2.5"/>',
           f'<ellipse cx="{cx}" cy="{cy}" rx="{rx - 1.5}" ry="{ry - 1.5}" fill="#fff"/>']
    y = cy - (len(lines) - 1) * size * .62
    for i, ln in enumerate(lines):
        out.append(txt(cx, y + i * size * 1.24 + size * .35, ln, INK, size, 800, "middle", italic=True))
    return "".join(out)


def caption_box(x, y, w, lines, size=12) -> str:
    h = len(lines) * size * 1.35 + 14
    out = [f'<rect x="{x + 3}" y="{y + 3}" width="{w}" height="{h:.0f}" fill="{INK}"/>',
           f'<rect x="{x}" y="{y}" width="{w}" height="{h:.0f}" fill="#fff" stroke="{INK}" stroke-width="2"/>']
    for i, ln in enumerate(lines):
        out.append(txt(x + 10, y + 7 + size + i * size * 1.35, ln, INK, size, 600, family=SERIF))
    return "".join(out)


def menacing(D: Font, x, y, size, n=4, delay=0.0, rot=-8) -> str:
    """ゴゴゴ : des onomatopées qui tremblent."""
    out = []
    for i in range(n):
        dx, dy = i * size * .62, (i % 2) * size * .55
        out.append(f'<g class="gogo" style="animation-delay:{delay + i * .18:.2f}s;transform-origin:{x + dx:.0f}px {y + dy:.0f}px">'
                   + D.text("ゴ", x + dx, y + dy, size * (1 - i * .08), SPOT, INK, size * .07, anchor="middle", skew=rot)
                   + "</g>")
    return "".join(out)


# ---------------------------------------------------------------- 1. page de titre (avec le zoom d'arrivée)

def hero(cfg: dict) -> None:
    H = 440
    rnd = random.Random(4)
    p = Page("manga-hero.svg", H, "Chapter 3 — HAMZA",
             "Manga chapter title page: CHAPTER 3, HAMZA, THE STUDENT WHO SHIPS, with focus lines and menacing sound "
             "effects. The vertical title reads CODE BY HAAMZA in katakana. Speech bubbles: I don't leave projects "
             "half-finished… I just start too many of them. The page opens by zooming through the screen of a PSP.")
    D, A = p.D, p.A
    p.defs += ['<clipPath id="p1"><rect x="18" y="18" width="590" height="404"/></clipPath>',
               '<clipPath id="p2"><rect x="624" y="18" width="218" height="250"/></clipPath>',
               f'<mask id="m1"><rect width="{W}" height="{H}" fill="url(#fadeD)"/></mask>']
    b = p.b
    b.append(panel(18, 18, 590, 404))
    b.append('<g clip-path="url(#p1)">')
    b.append(f'<rect x="18" y="18" width="590" height="404" fill="url(#tone)" mask="url(#m1)" opacity=".9"/>')
    b.append(focus_lines(300, 205, (18, 18, 608, 422), 170, 175, rnd))
    b.append(A.text("CHAPTER 3", 300, 112, 22, INK, "#fff", 6, anchor="middle", track=6))
    b.append('<g class="slam" style="transform-origin:300px 210px">'
             + D.text("HAMZA", 304, 246, 118, INK, "#fff", 14, anchor="middle", skew=-12) + "</g>")
    b.append(f'<g transform="rotate(-3 300 300)"><rect x="150" y="276" width="300" height="34" fill="{INK}"/>'
             + A.text("THE STUDENT WHO SHIPS", 300, 302, 22, "#fff", anchor="middle", track=3) + "</g>")
    b.append(caption_box(36, 34, 210, ["Third-year CS student.", "Work-study. France."], 12.5))
    b.append(menacing(D, 500, 120, 44, 4, 2.0))
    b.append(menacing(D, 70, 352, 34, 3, 2.4, rot=-14))
    b.append("</g>")
    b.append(panel(624, 18, 218, 250, INK))
    b.append('<g clip-path="url(#p2)">')
    b.append(focus_lines(733, 330, (624, 18, 842, 268), 50, 60, random.Random(8), "#2a2a2a"))
    b.append(D.vtext("コード", 800, 66, 38, "#fff", 1.08))
    b.append(D.vtext("バイ", 800, 194, 30, SPOT, 1.08))
    b.append(D.vtext("ハムザ", 752, 66, 48, "#fff", 1.04, stroke=INK, sw=4))
    b.append('<rect x="640" y="36" width="44" height="88" fill="#fff"/>' + D.vtext("第三話", 662, 64, 24, INK, 1.05))
    b.append(txt(733, 254, "CODE BY HAAMZA", "#fff", 9, 700, "middle", attrs=' letter-spacing="2"'))
    b.append("</g>")
    b.append(panel(624, 282, 218, 140))
    b.append('<rect x="624" y="282" width="218" height="140" fill="url(#tone2)" opacity=".18"/>')
    b.append(bubble(733, 322, 96, 30, (700, 362), ["I don't leave projects", "half-finished…"], 11.5))
    b.append(bubble(746, 384, 86, 26, (792, 414), ["I just start too", "many of them."], 11.5))

    # Le zoom d'arrivée : l'écran de la PSP qu'on vient de toucher grossit jusqu'à remplir la page.
    # Écrit invisible (opacity 0) : sans animation (rendu statique, mouvement réduit), on voit la page.
    k = 1.6
    cx, cy = W / 2, H / 2
    sx, sy, sw_, sh = art.screen_rect(cx, cy, k)
    scx, scy = sx + sw_ / 2, sy + sh / 2
    p.defs.append(f'<linearGradient id="xbg" x1="0" y1="0" x2=".35" y2="1"><stop offset="0" stop-color="{xmb.TOP}"/>'
                  f'<stop offset="1" stop-color="{xmb.BOT}"/></linearGradient>')
    # Le fond reste fixe ; seul le trou de l'écran (un masque) suit la PSP qui tourne puis grossit.
    p.defs.append(f'<mask id="hole" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
                  f'<rect width="{W}" height="{H}" fill="#fff"/><g class="geo"><rect x="{sx:.1f}" y="{sy:.1f}" '
                  f'width="{sw_:.1f}" height="{sh:.1f}" fill="#000"/></g></mask>')
    p.css.append("@keyframes geo{0%{transform:rotate(-160deg) scale(.55)}28%{transform:rotate(0) scale(1)}"
                 "40%{transform:scale(1)}88%{transform:scale(7)}100%{transform:scale(7.4)}}"
                 f".geo{{transform-origin:{scx:.1f}px {scy:.1f}px;animation:geo 2.1s cubic-bezier(.6,0,.4,1) both}}"
                 "@keyframes fade{0%,88%{opacity:1}100%{opacity:0}}.dive{opacity:0;animation:fade 2.1s linear both}"
                 "@keyframes slam{0%{transform:scale(1.6);opacity:0}60%{transform:scale(.96);opacity:1}100%{transform:scale(1)}}"
                 ".slam{animation:slam .6s cubic-bezier(.2,1.4,.4,1) 1.9s both}")
    b.append(f'<g class="dive"><rect width="{W}" height="{H}" rx="14" fill="url(#xbg)" mask="url(#hole)"/>'
             f'<g class="geo">{art.psp(cx, cy, k, "#fff", "#141418", hole=True)}</g></g>')
    p.write()


# ---------------------------------------------------------------- 2. les liens en autocollants

def links(cfg: dict) -> list[tuple[str, str, str]]:
    out = []
    for i, l in enumerate(cfg["identity"]["links"]):
        A = Font("anton", "an")
        label = l["label"].upper()
        has_icon = bool(l.get("icon"))
        tw = A.width(label, 17, 1.5)
        w, h = tw + (58 if has_icon else 34), 44
        rot = (-2.5, 1.8, -1.2, 2.4, -1.8)[i % 5]
        name = f"manga-link-{slug(l['label'])}.svg"
        body = [f'<g transform="rotate({rot} {w / 2:.0f} {h / 2:.0f})">'
                f'<rect x="7" y="8" width="{w - 12:.0f}" height="{h - 14}" fill="{INK}"/>'
                f'<rect x="3" y="4" width="{w - 12:.0f}" height="{h - 14}" fill="#fff" stroke="{INK}" stroke-width="2.5"/>']
        x = 15
        if has_icon:
            body.append(icon(l["icon"], x + 8, h / 2 - 1, 16, INK))
            x += 24
        body.append(A.text(label, x, h / 2 + 6, 17, INK, track=1.5) + "</g>")
        save(name, [svg_open(w, h, l["label"]), f"<defs>{A.defs()}</defs>"] + body)
        out.append((name, l["url"], l["label"]))
    return out


# ---------------------------------------------------------------- 3. le portail : la steel ball

def portal(cfg: dict) -> None:
    H = 340
    p = Page("manga-portal.svg", H, "Tap the spinning steel ball to go back to the PSP menu",
             "A hand spins a steel ball in its palm, an ink golden spiral turning behind it: the Golden Rotation, "
             "phi = 1.618. Tap it to go back to the PSP menu version of this page.")
    D, A = p.D, p.A
    cx, cy, hs, r = 236, 190, .95, 50
    p.defs.append(art.hand_shade_clip(cx, cy + 4 * hs, hs))
    p.defs.append('<clipPath id="pp"><rect x="18" y="18" width="824" height="304"/></clipPath>'
                  f'<clipPath id="ball"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>')
    p.css.append(f".gold{{transform-origin:{cx}px {cy}px;animation:spin 16.18s linear infinite reverse}}"
                 f".ballspin{{transform-origin:{cx}px {cy}px;animation:spin 1.618s linear infinite}}"
                 "@keyframes nudge{0%,100%{transform:translateX(0)}50%{transform:translateX(-6px)}}"
                 ".nudge{animation:nudge 1.618s ease-in-out infinite}")
    b = p.b
    b.append(panel(18, 18, 824, 304))
    b.append('<g clip-path="url(#pp)">')
    b.append(focus_lines(cx, cy, (18, 18, 842, 322), 120, 150, random.Random(12), "#e4e0d6"))
    b.append(f'<g class="gold">{art.golden(cx, cy, 440, INK, 1.2, .2, .65)}</g>')
    b.append(art.hand(cx, cy + 4 * hs, hs, "#fff", INK, 3, "url(#tone)", sleeve=INK))
    b.append(art.palm_shadow(cx, cy + 4 * hs, hs, r, INK, .35))
    b.append(f'<g class="ballspin"><image href="{data_uri(BALL)}" x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" '
             f'clip-path="url(#ball)"/>{art.spin_arcs(cx, cy, r + 14, INK, 3, 3)}</g>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{INK}" stroke-width="3"/>')
    # à droite : le titre
    x0 = 470
    b.append(D.text("黄金の回転", x0, 104, 44, INK, skew=-6))
    b.append(A.text("GOLDEN ROTATION", x0 + 2, 140, 26, SPOT, track=4))
    b.append(txt(x0 + 2, 166, "φ = 1.6180339887…  one turn every 1.618 s", GREY, 13, 700, family=SERIF, italic=True))
    b.append(caption_box(x0, 190, 340, ["Tap the spinning steel ball to go back", "to the PSP menu version of this page."], 13))
    b.append(f'<g class="nudge"><polygon points="{poly([(x0 + 6, 274), (x0 + 30, 260), (x0 + 30, 288)])}" fill="{INK}"/>'
             + A.text("BACK TO THE MENU", x0 + 40, 284, 22, INK, track=2) + "</g>")
    b.append(menacing(D, 790, 70, 30, 2, 0, rot=-14))
    b.append("</g>")
    p.write()


# ---------------------------------------------------------------- 4. la fiche de Stand (stats)

GRADES = "EDCBA"
STAND = [
    ("POWER", "破壊力", "commits", [300, 1000, 2500, 4000]),
    ("SPEED", "スピード", "prs", [20, 80, 200, 500]),
    ("RANGE", "射程距離", "nlangs", [2, 4, 7, 12]),
    ("STAMINA", "持続力", "best", [7, 21, 45, 90]),
    ("PRECISION", "精密動作性", "reviews", [10, 30, 80, 200]),
    ("POTENTIAL", "成長性", "total", [500, 1500, 3000, 5000]),
]
UNIT = {"commits": "commits", "prs": "PRs", "nlangs": "languages", "best": "day streak", "reviews": "reviews",
        "total": "contributions"}


def grade(v: int, th: list[int]) -> int:
    return sum(v >= t for t in th)  # 0..4 → E..A


def stand(cfg: dict, st: dict) -> None:
    H = 440
    gs = [grade(st[k], th) for _, _, k, th in STAND]
    p = Page("manga-stand.svg", H, "Stand stats — 「HELLO WORLD」",
             "Stand name HELLO WORLD, Stand user Hamza. Graded on the last 12 months: "
             + ", ".join(f"{en} {GRADES[g]} ({num(st[k])} {UNIT[k]})" for (en, _, k, _), g in zip(STAND, gs)))
    D, A = p.D, p.A
    p.defs += ['<clipPath id="q1"><rect x="18" y="18" width="330" height="404"/></clipPath>',
               '<clipPath id="q2"><rect x="362" y="18" width="480" height="404"/></clipPath>']
    b = p.b
    b.append(panel(18, 18, 330, 404))
    b.append('<g clip-path="url(#q1)">')
    b.append('<rect x="18" y="230" width="330" height="200" fill="url(#tone)" opacity=".55"/>')
    b.append(A.text("STAND NAME", 38, 60, 16, GREY, track=4))
    b.append(D.text("「HELLO", 30, 116, 46, INK, skew=-8))
    b.append(D.text("WORLD」", 70, 170, 46, SPOT, INK, 3, skew=-8))
    b.append(A.text("STAND USER", 38, 210, 16, GREY, track=4))
    b.append(D.text("HAMZA", 38, 246, 30, INK, skew=-8))
    b.append(caption_box(34, 272, 298, ["ABILITY — turns any idea into a finished",
                                        "project: Docker, tests and a changelog",
                                        "included, every time.",
                                        "WEAKNESS — starts too many of them."], 11.5))
    b.append(menacing(D, 262, 70, 30, 3, .2, rot=-14))
    b.append("</g>")
    b.append(panel(362, 18, 480, 404))
    b.append('<g clip-path="url(#q2)">')
    cx, cy, r = 602, 222, 96
    b.append(focus_lines(cx, cy, (362, 18, 842, 422), 90, 205, random.Random(2), "#e4e0d6"))
    ang = [math.radians(-90 + i * 60) for i in range(6)]
    for k in range(5, 0, -1):
        rr = r * k / 5
        b.append(f'<polygon points="{poly([(cx + rr * math.cos(a), cy + rr * math.sin(a)) for a in ang])}" '
                 f'fill="{"#fff" if k % 2 else PAPER}" stroke="{INK}" stroke-width="{2.5 if k == 5 else 1}"/>')
    for a in ang:
        b.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + r * math.cos(a):.1f}" y2="{cy + r * math.sin(a):.1f}" stroke="{INK}" stroke-width="1"/>')
    pts = [(cx + r * (g + 1) / 5 * math.cos(a), cy + r * (g + 1) / 5 * math.sin(a)) for g, a in zip(gs, ang)]
    p.css.append(f".grow{{transform-origin:{cx}px {cy}px;animation:grow .9s cubic-bezier(.2,1.5,.4,1) both}}")
    b.append(f'<g class="grow"><polygon points="{poly(pts)}" fill="{SPOT}" opacity=".85"/>'
             f'<polygon points="{poly(pts)}" fill="url(#tone)" opacity=".35"/>'
             f'<polygon points="{poly(pts)}" fill="none" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/></g>')
    for i, ((en, jp, key, th), g, a) in enumerate(zip(STAND, gs, ang)):
        gx, gy = cx + (r + 26) * math.cos(a), cy + (r + 26) * math.sin(a)
        b.append(f'<g class="pop" style="animation-delay:{.5 + i * .1:.2f}s;transform-origin:{gx:.0f}px {gy:.0f}px">'
                 f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="19" fill="{INK}"/><circle cx="{gx:.1f}" cy="{gy:.1f}" r="16" fill="#fff"/>'
                 + D.text(GRADES[g], gx, gy + 8, 22, INK, anchor="middle") + "</g>")
        side = abs(math.cos(a)) > .3
        anchor = "middle" if not side else ("start" if math.cos(a) > 0 else "end")
        lx = gx + (26 if math.cos(a) > 0 else -26) if side else gx
        ly = gy - 4 if side else (gy - 56 if math.sin(a) < 0 else gy + 38)
        b.append(A.text(en, lx, ly, 17, INK, anchor=anchor, track=1.5))
        b.append(txt(lx, ly + 15, f"{num(st[key])} {UNIT[key]}", GREY, 10.5, 700, anchor))
        b.append(D.text(jp, lx, ly + 30, 9.5, GREY, anchor=anchor))
    b.append(txt(828, 410, "graded on the last 12 months · A is best", GREY, 10, 600, "end", italic=True))
    b.append("</g>")
    p.write()


# ---------------------------------------------------------------- 5. le setup, en fiche de personnage

def equipment(cfg: dict) -> None:
    pc, srv = cfg["machines"][0], cfg["machines"][1]
    rows = len(pc["specs"])
    H = 96 + rows * 27 + 40
    p = Page("manga-setup.svg", H, "Equipment — my setup",
             f"{pc['host']}: " + "; ".join(f"{k} {v}" for k, v in pc["specs"]) + f". {srv['host']}: "
             + "; ".join(f"{k} {v}" for k, v in srv["specs"]))
    D, A = p.D, p.A
    b = p.b
    b.append(panel(18, 18, W - 36, H - 36))
    b.append(f'<rect x="18" y="18" width="92" height="{H - 36}" fill="{INK}"/>')
    b.append(D.vtext("機材", 64, 82, 40, "#fff", 1.1))
    b.append(f'<g transform="rotate(90 64 {H - 110})">' + A.text("EQUIPMENT", 64, H - 104, 18, SPOT, anchor="middle", track=8) + "</g>")

    def sheet(x, w, m, y0, tag):
        b.append(f'<g transform="rotate(-2 {x + 70} {y0 - 14})"><rect x="{x}" y="{y0 - 32}" width="{A.width(m["host"].upper(), 22, 1.5) + 24:.0f}" '
                 f'height="34" fill="{INK}"/>' + A.text(m["host"].upper(), x + 12, y0 - 7, 22, "#fff", track=1.5) + "</g>")
        b.append(txt(x + w, y0 - 10, tag, GREY, 11, 700, "end", italic=True, family=SERIF))
        y = y0 + 26
        for k, v in m["specs"]:
            if k:
                b.append(A.text(k.upper(), x, y, 14, SPOT if k in ("cpu", "gpu") else INK, track=1.5))
            b.append(txt(x + 74, y, v, INK, 12.5 if len(v) * 6.6 < w - 74 else 11.5, 600, family=SERIF))
            b.append(f'<line x1="{x}" y1="{y + 9}" x2="{x + w}" y2="{y + 9}" stroke="{INK}" stroke-width="1" '
                     f'stroke-dasharray="1 4" stroke-linecap="round"/>')
            y += 27
        return y

    sheet(134, 380, pc, 68, "the main machine")
    y = sheet(540, 284, srv, 68, "always on")
    b.append(caption_box(540, y + 4, 284, ["In the lab, private for now:"] + wrap(cfg["private_note"], 38)
                         + wrap(cfg["gym"], 42), 11.5))
    p.write()


# ---------------------------------------------------------------- 6. le stack, en planche de cases

def stack(cfg: dict) -> None:
    cats = cfg["stack"]
    cols, gap = 3, 14
    pw = (W - 36 - (cols - 1) * gap) / cols
    rows_per = [math.ceil(len(c["items"]) / 2) for c in cats]
    ph = 52 + max(rows_per) * 26 + 10
    nrow = math.ceil(len(cats) / cols)
    H = 84 + nrow * ph + (nrow - 1) * gap + 22
    p = Page("manga-stack.svg", H, "Techniques — my stack",
             " / ".join(f"{c['cat']}: " + ", ".join(i[0] for i in c["items"]) for c in cats))
    D, A = p.D, p.A
    b = p.b
    b.append(D.text("技術", 24, 62, 36, INK))
    b.append(A.text("TECHNIQUES", 106, 58, 24, SPOT, track=5))
    b.append(txt(W - 24, 56, "what I fight with", GREY, 12, 600, "end", italic=True, family=SERIF))
    for i, c in enumerate(cats):
        col, row = i % cols, i // cols
        x, y = 18 + col * (pw + gap), 84 + row * (ph + gap)
        b.append(f'<g class="row" style="animation-delay:{i * .08:.2f}s">')
        b.append(panel(x, y, pw, ph, "#fff", 3))
        b.append(f'<polygon points="{poly([(x + pw - 70, y), (x + pw, y), (x + pw, y + 50)])}" fill="url(#tone)" opacity=".7"/>')
        b.append(A.text(c["cat"].upper(), x + 14, y + 32, 20, INK, track=2))
        for j, (label, ic) in enumerate(c["items"]):
            cx = x + 14 + (j % 2) * (pw / 2 - 4)
            cy = y + 60 + (j // 2) * 26
            if ic:
                b.append(icon(ic, cx + 8, cy - 4, 15, INK))
            room = pw / 2 - 30
            size = 12.5 if len(label) * 7 < room else max(9.5, room / len(label) * 1.75)
            b.append(txt(cx + (22 if ic else 0), cy + 1, label, INK if ic else GREY, size, 700, italic=not ic))
        b.append("</g>")
    p.write()


# ---------------------------------------------------------------- 7. le sommaire (projets)

def contents(cfg: dict, st: dict) -> list[tuple[str, str, str]]:
    projs = cfg["projects"] + cfg["uni"]
    p = Page("manga-contents.svg", 92, "Contents — my projects")
    D, A = p.D, p.A
    p.b.append(panel(18, 18, W - 36, 56, INK))
    p.b.append(D.text("目次", 36, 60, 30, "#fff"))
    p.b.append(A.text("CONTENTS", 112, 56, 22, SPOT, track=6))
    p.b.append(txt(W - 36, 52, "tap a chapter to open it · ★ GitHub stars", "#cfcfcf", 11.5, 600, "end", italic=True, family=SERIF))
    p.write()
    out = []
    for i, pr in enumerate(projs):
        team = pr in cfg["uni"]
        name = f"manga-chapter-{slug(pr['name'])}.svg"
        H = 64
        q = Page(name, H, f"Chapter {i + 1:02d} — {pr['name']}", f"{pr['desc']} — {pr['meta']}")
        D, A = q.D, q.A
        q.b[0] = f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" fill="{PAPER}" stroke="{INK}" stroke-width="3"/>'
        q.b.append(f'<rect x="1.5" y="1.5" width="14" height="{H - 3}" fill="{SPOT if not team else GREY}"/>')
        col = GREY if team else INK
        q.b.append(A.text(f"{i + 1:02d}", 46, 42, 30, SPOT if not team else GREY))
        q.b.append(D.text(pr["name"].replace("_", " "), 96, 30, 17, col))
        q.b.append(txt(96, 50, pr["desc"], col, 12, 600, family=SERIF, italic=True))
        meta = ""
        for part in pr["meta"].split("→")[0].split("·"):
            cand = f"{meta} · {part.strip()}" if meta else part.strip()
            if len(cand) > 40:
                break
            meta = cand
        q.b.append(f'<line x1="520" y1="26" x2="{W - 110}" y2="26" stroke="{INK}" stroke-width="2" stroke-dasharray="1 6" stroke-linecap="round"/>')
        q.b.append(txt(520, 46, meta, GREY, 10, 700))
        if team:
            q.b.append(A.text("TEAM-UP", W - 40, 36, 14, GREY, anchor="end", track=2))
        elif pr.get("stars"):
            sw = A.width(str(pr["stars"]), 22)
            q.b.append(A.text(str(pr["stars"]), W - 40, 38, 22, INK, anchor="end")
                       + txt(W - 46 - sw, 37, "★", SPOT, 16, 700, "end"))
        q.write()
        out.append((name, pr["url"], pr["name"]))
    return out


# ---------------------------------------------------------------- 8. en-tête « hors service »

def offduty(cfg: dict) -> None:
    p = Page("manga-offduty.svg", 92, "Meanwhile, off duty…")
    D, A = p.D, p.A
    p.b.append(f'<g transform="rotate(-1.5 {W / 2} 46)"><rect x="{W / 2 - 230}" y="22" width="460" height="50" fill="{INK}"/>'
               f'<rect x="{W / 2 - 236}" y="16" width="460" height="50" fill="#fff" stroke="{INK}" stroke-width="3"/>'
               + D.text("休日", W / 2 - 214, 52, 22, INK)
               + A.text("MEANWHILE, OFF DUTY…", W / 2 - 150, 52, 24, INK, track=2) + "</g>")
    p.write()
