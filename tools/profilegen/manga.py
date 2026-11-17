"""Style manga : un chapitre en noir et blanc, une seule couleur d'accent.

Chaque fonction renvoie un calque (defs, css, body) ; dual.py le superpose au calque PSP du
même panneau. Les animations d'entrée se rejouent à chaque apparition du manga dans la boucle.
"""
from __future__ import annotations

import math
import random

from . import art
from .kit import (GRADE_AXES, GRADES, ROOT, SERIF, SHOW_MANGA, SWITCH_OUT, T, UNIT, W, Font, data_uri, dots, icon,
                  keyframes, num, on_loop, poly, txt, wrap)

PAPER, INK, GREY, SPOT = "#f7f4ec", "#111111", "#6b6b6b", "#8a3cff"
BALL = ROOT / "assets" / "steel-ball.png"
ENTER = SHOW_MANGA - .9  # les entrées commencent pendant que l'iris s'ouvre


def enter(name: str, start: str, dur: float = .6, end: str = "transform:none;opacity:1") -> str:
    """Une entrée qui se rejoue à chaque apparition du manga. L'état écrit reste l'état final."""
    return keyframes(name, [(0, start), (ENTER, start), (ENTER + dur, end), (T, end)])


class Page:
    """Un calque du style manga : feuille blanche, polices, trames, CSS."""

    def __init__(self, h: float, w: float = W, sheet: bool = True):
        self.h, self.w = h, w
        self.D = Font("dela", "dg")
        self.A = Font("anton", "an")
        self.defs = [dots("tone", INK, 6, 1.25, 45), dots("tone2", INK, 4.5, 1.5, 45),
                     '<linearGradient id="fadeD" x1="0" y1="0" x2="0" y2="1"><stop offset=".35" stop-color="#fff" stop-opacity="0"/>'
                     '<stop offset="1" stop-color="#fff"/></linearGradient>']
        self.css: list[str] = []
        self.b = [f'<rect width="{w}" height="{h}" rx="14" fill="#fff"/>'] if sheet else []

    def layer(self, extra_fonts: tuple = ()) -> tuple:
        css = CSS + "".join(self.css)
        fonts = self.D.defs() + self.A.defs() + "".join(f.defs() for f in extra_fonts)
        return "".join(self.defs) + fonts, css, "".join(self.b)


CSS = ("@keyframes mgogo{0%,100%{transform:translate(0,0) scale(1)}25%{transform:translate(-1.5px,1px) scale(1.04)}"
       "50%{transform:translate(1px,-1.5px) scale(.98)}75%{transform:translate(1.5px,1px) scale(1.03)}}"
       ".gogo{animation:mgogo .9s steps(2) infinite}"
       "@keyframes mspin{to{transform:rotate(360deg)}}"
       + enter("mrow", "transform:translateX(24px);opacity:0", .45) + on_loop("row", "mrow")
       + enter("mpop", "transform:scale(0)", .4, "transform:scale(1)") + on_loop("pop", "mpop"))


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


# ---------------------------------------------------------------- 1. page de titre

def hero(cfg: dict, H: float) -> tuple:
    rnd = random.Random(4)
    p = Page(H)
    D, A = p.D, p.A
    p.defs += ['<clipPath id="p1"><rect x="18" y="18" width="590" height="404"/></clipPath>',
               '<clipPath id="p2"><rect x="624" y="18" width="218" height="250"/></clipPath>',
               f'<mask id="m1"><rect width="{W}" height="{H}" fill="url(#fadeD)"/></mask>']
    # le titre claque à chaque fois que le manga apparaît
    p.css.append(keyframes("mslam", [(0, "transform:scale(1.6);opacity:0"), (13.0, "transform:scale(1.6);opacity:0"),
                                     (13.45, "transform:scale(.96);opacity:1"), (13.7, "transform:scale(1);opacity:1"),
                                     (T, "transform:scale(1);opacity:1")])
                 + on_loop("slam", "mslam", "transform-origin:300px 210px;"))
    b = p.b
    b.append(panel(18, 18, 590, 404))
    b.append('<g clip-path="url(#p1)">')
    b.append(f'<rect x="18" y="18" width="590" height="404" fill="url(#tone)" mask="url(#m1)" opacity=".9"/>')
    b.append(focus_lines(300, 205, (18, 18, 608, 422), 170, 175, rnd))
    b.append(A.text("CHAPTER 3", 300, 112, 22, INK, "#fff", 6, anchor="middle", track=6))
    b.append('<g class="slam">' + D.text("HAMZA", 304, 246, 118, INK, "#fff", 14, anchor="middle", skew=-12) + "</g>")
    b.append(f'<g transform="rotate(-3 300 300)"><rect x="150" y="276" width="300" height="34" fill="{INK}"/>'
             + A.text("THE STUDENT WHO SHIPS", 300, 302, 22, "#fff", anchor="middle", track=3) + "</g>")
    b.append(caption_box(36, 34, 210, ["Third-year CS student.", "Work-study. France."], 12.5))
    b.append(menacing(D, 500, 120, 44, 4, 0))
    b.append(menacing(D, 70, 352, 34, 3, .4, rot=-14))
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
    return p.layer()


# ---------------------------------------------------------------- 2. un lien en autocollant

def link_size(l: dict) -> tuple[float, float]:
    return Font("anton", "an").width(l["label"].upper(), 17, 1.5) + (58 if l.get("icon") else 34), 44


def link(l: dict, w: float, h: float, rot: float = -2) -> tuple:
    p = Page(h, w, sheet=False)
    A = p.A
    lw, lh = link_size(l)
    x0 = (w - lw) / 2
    label = l["label"].upper()
    b = [f'<g transform="rotate({rot} {w / 2:.0f} {h / 2:.0f})">'
         f'<rect x="{x0 + 7:.1f}" y="8" width="{lw - 12:.0f}" height="{h - 14}" fill="{INK}"/>'
         f'<rect x="{x0 + 3:.1f}" y="4" width="{lw - 12:.0f}" height="{h - 14}" fill="#fff" stroke="{INK}" stroke-width="2.5"/>']
    x = x0 + 15
    if l.get("icon"):
        b.append(icon(l["icon"], x + 8, h / 2 - 1, 16, INK))
        x += 24
    b.append(A.text(label, x, h / 2 + 6, 17, INK, track=1.5) + "</g>")
    p.b += b
    return p.layer()


# ---------------------------------------------------------------- 3. la main qui fait tourner la steel ball

def portal(cfg: dict, H: float) -> tuple:
    p = Page(H)
    D, A = p.D, p.A
    cx, cy, hs, r = 236, 190, .95, 50
    p.defs.append(art.hand_shade_clip(cx, cy + 4 * hs, hs))
    p.defs.append(f'<clipPath id="pp"><rect x="18" y="18" width="{W - 36}" height="{H - 36}"/></clipPath>'
                  f'<clipPath id="ball"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>')
    p.css.append(f".gold{{transform-origin:{cx}px {cy}px;animation:mspin 16.18s linear infinite reverse}}"
                 f".ballspin{{transform-origin:{cx}px {cy}px;animation:mspin 1.618s linear infinite}}")
    b = p.b
    b.append(panel(18, 18, W - 36, H - 36))
    b.append('<g clip-path="url(#pp)">')
    b.append(focus_lines(cx, cy, (18, 18, W - 18, H - 18), 120, 150, random.Random(12), "#e4e0d6"))
    b.append(f'<g class="gold">{art.golden(cx, cy, 440, INK, 1.2, .2, .65)}</g>')
    b.append(art.hand(cx, cy + 4 * hs, hs, "#fff", INK, 3, "url(#tone)", sleeve=INK))
    b.append(art.palm_shadow(cx, cy + 4 * hs, hs, r, INK, .35))
    b.append(f'<g class="ballspin"><image href="{data_uri(BALL)}" x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" '
             f'clip-path="url(#ball)"/>{art.spin_arcs(cx, cy, r + 14, INK, 3, 3)}</g>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{INK}" stroke-width="3"/>')
    x0 = 470
    b.append(D.text("黄金の回転", x0, 100, 44, INK, skew=-6))
    b.append(A.text("GOLDEN ROTATION", x0 + 2, 136, 26, SPOT, track=4))
    b.append(txt(x0 + 2, 162, "φ = 1.6180339887…  one turn every 1.618 s", GREY, 13, 700, family=SERIF, italic=True))
    b.append(caption_box(x0, 182, 340, ["Every 12 seconds the steel ball spins", "this page back to the PSP menu."], 13))
    # compte à rebours jusqu'au retour
    y = 284
    b.append(A.text("BACK TO THE MENU IN…", x0 + 2, y - 10, 16, INK, track=2))
    b.append(f'<rect x="{x0}" y="{y}" width="330" height="10" fill="#fff" stroke="{INK}" stroke-width="2"/>')
    p.css.append(keyframes("mcd", [(0, "transform:scaleX(0)"), (SHOW_MANGA, "transform:scaleX(0)"),
                                   (SWITCH_OUT, "transform:scaleX(1)"), (T, "transform:scaleX(1)")])
                 + on_loop("cd", "mcd", f"transform-origin:{x0}px {y}px;"))
    b.append(f'<rect class="cd" x="{x0}" y="{y}" width="330" height="10" fill="url(#tone)"/>')
    b.append(menacing(D, 790, 66, 30, 2, 0, rot=-14))
    b.append("</g>")
    return p.layer()


# ---------------------------------------------------------------- 4. la fiche de Stand (stats)

def stand(cfg: dict, st: dict, H: float) -> tuple:
    gs = st["grades"]
    p = Page(H)
    D, A = p.D, p.A
    p.defs += ['<clipPath id="q1"><rect x="18" y="18" width="330" height="404"/></clipPath>',
               '<clipPath id="q2"><rect x="362" y="18" width="480" height="404"/></clipPath>']
    b = p.b
    b.append(panel(18, 18, 330, H - 36))
    b.append('<g clip-path="url(#q1)">')
    b.append(f'<rect x="18" y="230" width="330" height="{H - 230}" fill="url(#tone)" opacity=".55"/>')
    b.append(A.text("STAND NAME", 38, 60, 16, GREY, track=4))
    b.append(D.text("「HELLO", 30, 116, 46, INK, skew=-8))
    b.append(D.text("WORLD」", 70, 170, 46, SPOT, INK, 3, skew=-8))
    b.append(A.text("STAND USER", 38, 210, 16, GREY, track=4))
    b.append(D.text("HAMZA", 38, 246, 30, INK, skew=-8))
    b.append(caption_box(34, 272, 298, ["ABILITY — turns any idea into a finished", "project: Docker, tests and a changelog",
                                        "included, every time.", "WEAKNESS — starts too many of them."], 11.5))
    b.append(menacing(D, 262, 70, 30, 3, .2, rot=-14))
    b.append("</g>")
    b.append(panel(362, 18, 480, H - 36))
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
    p.css.append(enter("mgrow", "transform:scale(0)", .9, "transform:scale(1)")
                 + on_loop("grow", "mgrow", f"transform-origin:{cx}px {cy}px;"))
    b.append(f'<g class="grow"><polygon points="{poly(pts)}" fill="{SPOT}" opacity=".85"/>'
             f'<polygon points="{poly(pts)}" fill="url(#tone)" opacity=".35"/>'
             f'<polygon points="{poly(pts)}" fill="none" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/></g>')
    for i, ((en, jp, key, th), g, a) in enumerate(zip(GRADE_AXES, gs, ang)):
        gx, gy = cx + (r + 26) * math.cos(a), cy + (r + 26) * math.sin(a)
        b.append(f'<g class="pop" style="animation-delay:{.4 + i * .1:.2f}s;transform-origin:{gx:.0f}px {gy:.0f}px">'
                 f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="19" fill="{INK}"/><circle cx="{gx:.1f}" cy="{gy:.1f}" r="16" fill="#fff"/>'
                 + D.text(GRADES[g], gx, gy + 8, 22, INK, anchor="middle") + "</g>")
        side = abs(math.cos(a)) > .3
        anchor = "middle" if not side else ("start" if math.cos(a) > 0 else "end")
        lx = gx + (26 if math.cos(a) > 0 else -26) if side else gx
        ly = gy - 4 if side else (gy - 56 if math.sin(a) < 0 else gy + 38)
        b.append(A.text(en, lx, ly, 17, INK, anchor=anchor, track=1.5))
        b.append(txt(lx, ly + 15, f"{num(st[key])} {UNIT[key]}", GREY, 10.5, 700, anchor))
        b.append(D.text(jp, lx, ly + 30, 9.5, GREY, anchor=anchor))
    b.append(txt(828, H - 30, "graded on the last 12 months · A is best", GREY, 10, 600, "end", italic=True))
    b.append("</g>")
    return p.layer()


# ---------------------------------------------------------------- 5. le setup, en fiche d'équipement

def equipment_height(cfg: dict) -> float:
    return 96 + len(cfg["machines"][0]["specs"]) * 27 + 40


def equipment(cfg: dict, H: float) -> tuple:
    pc, srv = cfg["machines"][0], cfg["machines"][1]
    p = Page(H)
    D, A = p.D, p.A
    b = p.b
    b.append(panel(18, 18, W - 36, H - 36))
    b.append(f'<rect x="18" y="18" width="92" height="{H - 36}" fill="{INK}"/>')
    b.append(D.vtext("機材", 64, 82, 40, "#fff", 1.1))
    b.append(f'<g transform="rotate(90 64 {H - 110})">' + A.text("EQUIPMENT", 64, H - 104, 18, SPOT, anchor="middle", track=8) + "</g>")

    def sheet(x, w, m, y0, tag):
        b.append(f'<g transform="rotate(-2 {x + 70} {y0 - 14})"><rect x="{x}" y="{y0 - 32}" '
                 f'width="{A.width(m["host"].upper(), 22, 1.5) + 24:.0f}" height="34" fill="{INK}"/>'
                 + A.text(m["host"].upper(), x + 12, y0 - 7, 22, "#fff", track=1.5) + "</g>")
        b.append(txt(x + w, y0 - 10, tag, GREY, 11, 700, "end", italic=True, family=SERIF))
        y = y0 + 26
        for i, (k, v) in enumerate(m["specs"]):
            b.append(f'<g class="row" style="animation-delay:{i * .05:.2f}s">')
            if k:
                b.append(A.text(k.upper(), x, y, 14, SPOT if k in ("cpu", "gpu") else INK, track=1.5))
            b.append(txt(x + 74, y, v, INK, 12.5 if len(v) * 6.6 < w - 74 else 11.5, 600, family=SERIF))
            b.append(f'<line x1="{x}" y1="{y + 9}" x2="{x + w}" y2="{y + 9}" stroke="{INK}" stroke-width="1" '
                     f'stroke-dasharray="1 4" stroke-linecap="round"/></g>')
            y += 27
        return y

    sheet(134, 380, pc, 68, "the main machine")
    y = sheet(540, 284, srv, 68, "always on")
    b.append(caption_box(540, y + 4, 284, ["In the lab, private for now:"] + wrap(cfg["private_note"], 38) + wrap(cfg["gym"], 42), 11.5))
    return p.layer()


# ---------------------------------------------------------------- 6. le stack, en planche de cases

def _stack_geom(cfg: dict):
    cats = cfg["stack"]
    cols, gap = 3, 14
    pw = (W - 36 - (cols - 1) * gap) / cols
    ph = 52 + max(math.ceil(len(c["items"]) / 2) for c in cats) * 26 + 10
    nrow = math.ceil(len(cats) / cols)
    return cats, cols, gap, pw, ph, 84 + nrow * ph + (nrow - 1) * gap + 22


def stack_height(cfg: dict) -> float:
    return _stack_geom(cfg)[-1]


def stack(cfg: dict, H: float) -> tuple:
    cats, cols, gap, pw, ph, natural = _stack_geom(cfg)
    p = Page(H)
    D, A = p.D, p.A
    b = p.b
    dy = (H - natural) / 2
    b.append(D.text("技術", 24, 62 + dy, 36, INK))
    b.append(A.text("TECHNIQUES", 106, 58 + dy, 24, SPOT, track=5))
    b.append(txt(W - 24, 56 + dy, "what I fight with", GREY, 12, 600, "end", italic=True, family=SERIF))
    for i, c in enumerate(cats):
        col, row = i % cols, i // cols
        x, y = 18 + col * (pw + gap), 84 + dy + row * (ph + gap)
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
    return p.layer()


# ---------------------------------------------------------------- 7. le sommaire (projets)

def contents_head(cfg: dict, H: float) -> tuple:
    p = Page(H)
    D, A = p.D, p.A
    y = (H - 56) / 2
    p.b.append(panel(18, y, W - 36, 56, INK))
    p.b.append(D.text("目次", 36, y + 42, 30, "#fff"))
    p.b.append(A.text("CONTENTS", 112, y + 38, 22, SPOT, track=6))
    p.b.append(txt(W - 36, y + 34, "tap a chapter to open it · ★ GitHub stars", "#cfcfcf", 11.5, 600, "end", italic=True, family=SERIF))
    return p.layer()


def chapter_row(cfg: dict, i: int, pr: dict, H: float) -> tuple:
    team = pr in cfg["uni"]
    q = Page(H, sheet=False)
    D, A = q.D, q.A
    q.b.append(f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" fill="{PAPER}" stroke="{INK}" stroke-width="3"/>')
    q.b.append(f'<rect x="1.5" y="1.5" width="14" height="{H - 3}" fill="{SPOT if not team else GREY}"/>')
    col = GREY if team else INK
    cy = H / 2
    q.b.append(f'<g class="row" style="animation-delay:{i * .06:.2f}s">')
    q.b.append(A.text(f"{i + 1:02d}", 34, cy + 12, 32, SPOT if not team else GREY))
    q.b.append(D.text(pr["name"].replace("_", " "), 92, cy - 4, 18, col))
    q.b.append(txt(92, cy + 17, pr["desc"], col, 12.5, 600, family=SERIF, italic=True))
    meta = ""
    for part in pr["meta"].split("→")[0].split("·"):
        cand = f"{meta} · {part.strip()}" if meta else part.strip()
        if len(cand) > 40:
            break
        meta = cand
    q.b.append(f'<line x1="520" y1="{cy - 6}" x2="{W - 110}" y2="{cy - 6}" stroke="{INK}" stroke-width="2" stroke-dasharray="1 6" stroke-linecap="round"/>')
    q.b.append(txt(520, cy + 14, meta, GREY, 10.5, 700))
    if team:
        q.b.append(A.text("TEAM-UP", W - 30, cy + 5, 14, GREY, anchor="end", track=2))
    elif pr.get("stars"):
        sw = A.width(str(pr["stars"]), 24)
        q.b.append(A.text(str(pr["stars"]), W - 30, cy + 8, 24, INK, anchor="end") + txt(W - 36 - sw, cy + 7, "★", SPOT, 16, 700, "end"))
    q.b.append("</g>")
    return q.layer()
