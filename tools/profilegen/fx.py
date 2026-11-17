"""Effets d'apparition des Stands : une petite animation liée au pouvoir, avant que le Stand apparaisse.

Chaque effet dessine ses éléments autour de (cx, cy) et les anime sur une « fenêtre » qui commence
à ctx.t0 : une seule fois au chargement pour un Stand simple, à chaque nouvelle étape pour une
évolution. Tous les éléments sont écrits invisibles (opacity:0) : sans animation (mouvement
réduit, rendu statique), on voit directement le Stand.

Un effet se choisit dans data/stands.json, champ « fx » de l'étape : un nom (« vines »), un objet
({"type": "rush", "word": "ORA"}) ou une liste de ceux-ci.
"""
from __future__ import annotations

import math
import random

from . import art
from .kit import poly

GOLD, INK = "#f2c14e", "#120a1f"


class Ctx:
    def __init__(self, pfx: str, cx: float, cy: float, t0: float, length: float, loop: bool, seed: str, font, img_id: str):
        self.p, self.cx, self.cy, self.t0, self.L, self.loop = pfx, cx, cy, t0, length, loop
        self.rnd = random.Random(seed)
        self.D = font
        self.img_id = img_id
        self.css: list[str] = []
        self.defs: list[str] = []
        self.n = 0

    def kf(self, frames: list[tuple[float, str]], hidden: str = "opacity:0") -> str:
        """Keyframes sur la fenêtre de l'effet : (temps relatif en s, déclarations). Invisible avant et après."""
        self.n += 1
        name = f"{self.p}{self.n}"

        def pc(t):
            return f"{max(0.0, min(100.0, (self.t0 + t) / self.L * 100)):.3f}%"
        start, end = frames[0][0], frames[-1][0]
        body = [f"0%{{{hidden}}}"]
        if self.t0 + start > 0.02:
            body.append(f"{pc(start - .02)}{{{hidden}}}")
        body += [f"{pc(t)}{{{c}}}" for t, c in frames]
        if (self.t0 + end) / self.L < .995:
            body.append(f"{pc(end + .02)}{{{hidden}}}")
            body.append(f"100%{{{hidden}}}")
        self.css.append(f"@keyframes {name}{{{''.join(body)}}}")
        return name

    def style(self, name: str, delay: float = 0, origin: tuple[float, float] | None = None, extra: str = "") -> str:
        it = "infinite" if self.loop else "1"
        o = f"transform-origin:{origin[0]:.1f}px {origin[1]:.1f}px;" if origin else ""
        return f'style="opacity:0;{o}{extra}animation:{name} {self.L:.3f}s linear {it} both;animation-delay:{delay:.2f}s"'


def _smooth(pts) -> str:
    """Chemin lissé passant près des points (courbes quadratiques par les milieux)."""
    d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for a, b in zip(pts[1:-1], pts[2:]):
        d += f"Q{a[0]:.1f} {a[1]:.1f} {(a[0] + b[0]) / 2:.1f} {(a[1] + b[1]) / 2:.1f}"
    return d + f"L{pts[-1][0]:.1f} {pts[-1][1]:.1f}"


def _draw(ctx: Ctx, d: str, color: str, width: float, delay: float = 0, hold: float = .6, extra: str = "") -> str:
    """Un trait qui se dessine (stroke-dashoffset), reste, puis s'efface."""
    name = ctx.kf([(0, "opacity:1;stroke-dashoffset:100"), (.55, "opacity:1;stroke-dashoffset:0"),
                   (.55 + hold, "opacity:1;stroke-dashoffset:0"), (.95 + hold, "opacity:0;stroke-dashoffset:0")])
    return (f'<path d="{d}" pathLength="100" stroke-dasharray="100" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round" {extra} {ctx.style(name, delay)}/>')


def _pop(ctx: Ctx, svg: str, x: float, y: float, delay: float = 0, hold: float = .7, rot: float = 0) -> str:
    """Un élément qui surgit (scale 0 → 1.15 → 1), reste, puis disparaît."""
    name = ctx.kf([(0, f"opacity:0;transform:scale(0) rotate({rot - 20}deg)"), (.18, f"opacity:1;transform:scale(1.15) rotate({rot}deg)"),
                   (.28, f"opacity:1;transform:scale(1) rotate({rot}deg)"), (.28 + hold, f"opacity:1;transform:scale(1) rotate({rot}deg)"),
                   (.5 + hold, f"opacity:0;transform:scale(.9) rotate({rot}deg)")])
    return f"<g {ctx.style(name, delay, (x, y))}>{svg}</g>"


def _move(ctx: Ctx, svg: str, path: list[tuple[float, float]], dur: float, delay: float = 0, spin: float = 0,
          fade_in: float = .1, origin=(0, 0), scale=(1, 1)) -> str:
    """Un élément qui se déplace le long de points (translations relatives à sa position dessinée)."""
    n = len(path) - 1
    frames = []
    for k, (x, y) in enumerate(path):
        t = dur * k / n
        op = 0 if (k == 0 and fade_in) else (0 if k == n else 1)
        sc = scale[0] + (scale[1] - scale[0]) * k / n
        frames.append((t, f"opacity:{op};transform:translate({x:.1f}px,{y:.1f}px) rotate({spin * k / n:.0f}deg) scale({sc:.2f})"))
    if fade_in:
        x, y = path[0]
        frames.insert(1, (fade_in, f"opacity:1;transform:translate({x:.1f}px,{y:.1f}px) scale({scale[0]:.2f})"))
        frames.sort(key=lambda f: f[0])
    name = ctx.kf(frames)
    return f"<g {ctx.style(name, delay, origin)}>{svg}</g>"


def _word(ctx: Ctx, text: str, x: float, y: float, size: float, color: str = GOLD, rot: float = -8) -> str:
    size = ctx.D.fit(text, size, 300, floor=12)
    return ctx.D.text(text, x, y, size, color, INK, size * .16, anchor="middle", skew=-8)


# ---------------------------------------------------------------- les effets

def strings(ctx, color="#8fe3ff", n=8, width=2.2, **_):
    out = []
    for i in range(n):
        a = i * 2 * math.pi / n + ctx.rnd.uniform(-.2, .2)
        r = ctx.rnd.uniform(200, 260)
        pts = [(ctx.cx + r * math.cos(a), ctx.cy + r * math.sin(a))]
        for k in range(1, 5):
            rr = r * (1 - k / 5)
            aa = a + ctx.rnd.uniform(-.5, .5)
            pts.append((ctx.cx + rr * math.cos(aa), ctx.cy + rr * math.sin(aa)))
        pts.append((ctx.cx + ctx.rnd.uniform(-10, 10), ctx.cy + ctx.rnd.uniform(-10, 10)))
        out.append(_draw(ctx, _smooth(pts), color, width, i * .05))
    out.append(_pop(ctx, f'<circle cx="{ctx.cx}" cy="{ctx.cy}" r="16" fill="none" stroke="{color}" stroke-width="3"/>',
                    ctx.cx, ctx.cy, .5, .4))
    return "".join(out)


def vines(ctx, color="#6fcf5a", accent=GOLD, thorny=False, **_):
    out = []
    for i in range(7):
        x0 = 40 + i * 48 + ctx.rnd.uniform(-10, 10)
        pts = [(x0, 310)]
        x, y = x0, 310.0
        for k in range(5):
            y -= ctx.rnd.uniform(30, 48)
            x += ctx.rnd.uniform(-35, 35) + (ctx.cx - x) * .18
            pts.append((x, y))
        # la pointe s'enroule
        r = 12
        for k in range(1, 7):
            a = k * .9
            pts.append((x + r * math.cos(a) - r, y - r * math.sin(a)))
            r *= .82
        out.append(_draw(ctx, _smooth(pts), color, 4.5 if not thorny else 3.5, i * .06, .7))
        for k, (px, py) in enumerate(pts[1:5]):
            if thorny:
                leaf = (f'<path d="M{px:.1f} {py:.1f}l{8 if k % 2 else -8} -6" stroke="{color}" stroke-width="2.5" '
                        f'stroke-linecap="round"/>')
            else:
                rot = 35 if k % 2 else -35
                leaf = (f'<ellipse cx="{px + (9 if k % 2 else -9):.1f}" cy="{py:.1f}" rx="9" ry="4.5" fill="{color}" '
                        f'transform="rotate({rot} {px:.1f} {py:.1f})"/>')
            out.append(_pop(ctx, leaf, px, py, .25 + i * .06 + k * .07, .7))
        if not thorny and accent:
            fx, fy = pts[5]
            flower = "".join(f'<circle cx="{fx + 6 * math.cos(j * 1.256):.1f}" cy="{fy + 6 * math.sin(j * 1.256):.1f}" r="4" '
                             f'fill="{accent}"/>' for j in range(5)) + f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="3" fill="#fff"/>'
            out.append(_pop(ctx, flower, fx, fy, .55 + i * .06, .6))
    return "".join(out)


def hooks(ctx, color="#e6e6e6", n=5, **_):
    out = []
    for i in range(n):
        x = 60 + i * (260 / (n - 1)) + ctx.rnd.uniform(-12, 12)
        yk = ctx.rnd.uniform(110, 230)
        hook = (f'<path d="M{x:.1f} -20V{yk:.1f}" stroke="{color}" stroke-width="1.6" opacity=".8"/>'
                f'<path d="M{x:.1f} {yk:.1f}v16a9 9 0 1 1 -18 0l5 -5" fill="none" stroke="{color}" stroke-width="3.2" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')
        name = ctx.kf([(0, "opacity:1;transform:translateY(-320px)"), (.42, "opacity:1;transform:translateY(0) rotate(0)"),
                       (.55, "opacity:1;transform:translateY(-16px) rotate(6deg)"), (.7, "opacity:1;transform:translateY(0) rotate(-4deg)"),
                       (1.3, "opacity:1;transform:translateY(0) rotate(0)"), (1.7, "opacity:0;transform:translateY(-40px)")])
        out.append(f"<g {ctx.style(name, i * .08, (x, -20))}>{hook}</g>")
    return "".join(out)


def fishing(ctx, color="#f0f0f0", **_):
    wx = 104
    wall = "".join(f'<rect x="{wx + (12 if r % 2 else 0)}" y="{30 + r * 22}" width="24" height="20" rx="2" fill="#6b4f3a" '
                   f'stroke="{INK}" stroke-width="1.5"/>' for r in range(11))
    wall = f'<g>{wall}<rect x="{wx - 2}" y="28" width="40" height="246" fill="none" stroke="{INK}" stroke-width="2"/></g>'
    name = ctx.kf([(0, "opacity:0"), (.15, "opacity:.9"), (1.3, "opacity:.9"), (1.7, "opacity:0")])
    out = [f"<g {ctx.style(name)}>{wall}</g>"]
    rod = f'<path d="M380 -10L292 46" stroke="#8a5a2b" stroke-width="7" stroke-linecap="round"/>'
    name = ctx.kf([(0, "opacity:0;transform:translate(60px,-60px)"), (.2, "opacity:1;transform:none"), (1.3, "opacity:1;transform:none"),
                   (1.7, "opacity:0;transform:none")])
    out.append(f"<g {ctx.style(name)}>{rod}</g>")
    line = _smooth([(292, 46), (220, 70), (130, 120), (60, 150), (40, 190), (90, 230), (150, 215), (ctx.cx, ctx.cy + 40)])
    out.append(_draw(ctx, line, color, 1.8, .15, .65))
    hx, hy = ctx.cx, ctx.cy + 40
    out.append(_pop(ctx, f'<path d="M{hx} {hy}v10a7 7 0 1 1 -14 0l4 -4" fill="none" stroke="{color}" stroke-width="3" '
                    f'stroke-linecap="round"/>', hx, hy, .65, .5))
    return "".join(out)


def flames(ctx, colors=("#ff5a1f", "#ffb21f", "#ffe36b"), n=16, **_):
    out = []
    for i in range(n):
        x = ctx.rnd.uniform(50, 330)
        s = ctx.rnd.uniform(.8, 1.8)
        c = colors[i % len(colors)]
        fl = (f'<path d="M{x:.1f} 300c{10 * s:.1f} {-12 * s:.1f} {6 * s:.1f} {-26 * s:.1f} 0 {-40 * s:.1f}'
              f'c{-6 * s:.1f} {14 * s:.1f} {-10 * s:.1f} {28 * s:.1f} 0 {40 * s:.1f}z" fill="{c}"/>')
        rise = ctx.rnd.uniform(120, 230)
        out.append(_move(ctx, fl, [(0, 0), (0, -rise * .5), (0, -rise)], 1.1, ctx.rnd.uniform(0, .6), origin=(x, 300), scale=(1, .4)))
    return "".join(out)


def ice(ctx, color="#c8f1ff", **_):
    out = []
    for i in range(12):
        a = i * 30 + ctx.rnd.uniform(-8, 8)
        L = ctx.rnd.uniform(70, 140)
        shard = (f'<polygon points="{poly([(ctx.cx, ctx.cy - 6), (ctx.cx + L, ctx.cy), (ctx.cx, ctx.cy + 6)])}" fill="{color}" '
                 f'stroke="#fff" stroke-width="1" transform="rotate({a:.0f} {ctx.cx} {ctx.cy})"/>')
        name = ctx.kf([(0, "opacity:1;transform:scale(0)"), (.35, "opacity:1;transform:scale(1)"), (1.0, "opacity:1;transform:scale(1)"),
                       (1.5, "opacity:0;transform:scale(1.35)")])
        out.append(f"<g {ctx.style(name, i * .025, (ctx.cx, ctx.cy))}>{shard}</g>")
    out.append(_pop(ctx, f'<circle cx="{ctx.cx}" cy="{ctx.cy}" r="150" fill="none" stroke="{color}" stroke-width="2" '
                         f'stroke-dasharray="4 8"/>', ctx.cx, ctx.cy, .1, .8))
    return "".join(out)


def water(ctx, color="#5ec8ff", **_):
    out = []
    for i in range(16):
        a = ctx.rnd.uniform(-math.pi, 0)
        sp = ctx.rnd.uniform(70, 150)
        dx, dy = sp * math.cos(a), sp * math.sin(a)
        drop = f'<ellipse cx="{ctx.cx}" cy="{ctx.cy + 60}" rx="5" ry="7" fill="{color}" stroke="#fff" stroke-width=".8"/>'
        out.append(_move(ctx, drop, [(0, 0), (dx * .6, dy * .8), (dx, dy * .4 + 90)], 1.0, ctx.rnd.uniform(0, .25)))
    for k in range(3):
        name = ctx.kf([(0, "opacity:.9;transform:scale(.1)"), (.9, "opacity:0;transform:scale(1)")])
        out.append(f'<ellipse cx="{ctx.cx}" cy="{ctx.cy + 70}" rx="150" ry="30" fill="none" stroke="{color}" stroke-width="3" '
                   f'{ctx.style(name, k * .25, (ctx.cx, ctx.cy + 70))}/>')
    return "".join(out)


def lightning(ctx, color="#fff36b", n=5, **_):
    out = []
    for i in range(n):
        a = ctx.rnd.uniform(0, 2 * math.pi)
        pts = []
        for k in range(7):
            r = 210 * (1 - k / 6)
            pts.append((ctx.cx + r * math.cos(a) + ctx.rnd.uniform(-22, 22), ctx.cy + r * math.sin(a) + ctx.rnd.uniform(-22, 22)))
        d = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        flick = [(0, "opacity:0"), (.05, "opacity:1"), (.12, "opacity:.2"), (.2, "opacity:1"), (.3, "opacity:.3"), (.42, "opacity:1"),
                 (.8, "opacity:1"), (1.0, "opacity:0")]
        name = ctx.kf(flick)
        out.append(f'<g {ctx.style(name, i * .12)}><path d="{d}" fill="none" stroke="{color}" stroke-width="9" opacity=".25" '
                   f'stroke-linejoin="round"/><path d="{d}" fill="none" stroke="#fff" stroke-width="2.5" stroke-linejoin="round"/></g>')
    return "".join(out)


def timestop(ctx, word="ZA WARUDO", color="#c7b7ff", **_):
    # la sphère où le temps s'arrête : les couleurs s'inversent à l'intérieur
    name = ctx.kf([(0, "opacity:1;transform:scale(0)"), (.55, "opacity:1;transform:scale(3.2)"), (1.05, "opacity:1;transform:scale(3.2)"),
                   (1.45, "opacity:1;transform:scale(0)")])
    out = [f'<circle cx="{ctx.cx}" cy="{ctx.cy}" r="50" fill="#d8ccff" {ctx.style(name, 0, (ctx.cx, ctx.cy), "mix-blend-mode:difference;")}/>',
           f'<circle cx="{ctx.cx}" cy="{ctx.cy}" r="50" fill="none" stroke="{color}" stroke-width="1.5" '
           f'{ctx.style(name, 0, (ctx.cx, ctx.cy))}/>']
    clock = (f'<circle cx="{ctx.cx}" cy="{ctx.cy}" r="54" fill="none" stroke="{color}" stroke-width="4"/>'
             + "".join(f'<path d="M{ctx.cx + 46 * math.cos(k * math.pi / 6):.1f} {ctx.cy + 46 * math.sin(k * math.pi / 6):.1f}'
                       f'L{ctx.cx + 54 * math.cos(k * math.pi / 6):.1f} {ctx.cy + 54 * math.sin(k * math.pi / 6):.1f}" '
                       f'stroke="{color}" stroke-width="3"/>' for k in range(12)))
    out.append(_pop(ctx, clock, ctx.cx, ctx.cy, .05, .9))
    name = ctx.kf([(0, "opacity:1;transform:rotate(0)"), (.6, "opacity:1;transform:rotate(1080deg)"),
                   (1.15, "opacity:1;transform:rotate(1080deg)"), (1.4, "opacity:0;transform:rotate(1080deg)")])
    out.append(f'<path d="M{ctx.cx} {ctx.cy}V{ctx.cy - 42}" stroke="#fff" stroke-width="4" stroke-linecap="round" '
               f'{ctx.style(name, .05, (ctx.cx, ctx.cy))}/>')
    out.append(_pop(ctx, _word(ctx, word, ctx.cx, 46, 30), ctx.cx, 36, .25, .8))
    return "".join(out)


def rewind(ctx, word="", color="#c7b7ff", forward=False, **_):
    sgn = 1 if forward else -1
    clock = (f'<circle cx="{ctx.cx}" cy="{ctx.cy}" r="70" fill="none" stroke="{color}" stroke-width="4"/>'
             + "".join(f'<circle cx="{ctx.cx + 60 * math.cos(k * math.pi / 6):.1f}" cy="{ctx.cy + 60 * math.sin(k * math.pi / 6):.1f}" '
                       f'r="3" fill="{color}"/>' for k in range(12)))
    out = [_pop(ctx, clock, ctx.cx, ctx.cy, 0, 1.0)]
    for L, w, turns in ((52, 4, 6), (36, 6, 1)):
        name = ctx.kf([(0, "opacity:1;transform:rotate(0)"), (1.2, f"opacity:1;transform:rotate({sgn * 360 * turns}deg)"),
                       (1.5, f"opacity:0;transform:rotate({sgn * 360 * turns}deg)")])
        out.append(f'<path d="M{ctx.cx} {ctx.cy}V{ctx.cy - L}" stroke="#fff" stroke-width="{w}" stroke-linecap="round" '
                   f'{ctx.style(name, .05, (ctx.cx, ctx.cy))}/>')
    for k in range(3):
        r = 95 + k * 22
        arc = (f'<path d="M{ctx.cx + r:.0f} {ctx.cy}A{r} {r} 0 1 {0 if forward else 1} {ctx.cx} {ctx.cy - r}" fill="none" '
               f'stroke="{color}" stroke-width="3" stroke-linecap="round"/>')
        name = ctx.kf([(0, "opacity:0;transform:rotate(0)"), (.15, "opacity:.9"), (1.2, f"opacity:.9;transform:rotate({sgn * 360}deg)"),
                       (1.5, f"opacity:0;transform:rotate({sgn * 400}deg)")])
        out.append(f"<g {ctx.style(name, k * .1, (ctx.cx, ctx.cy))}>{arc}</g>")
    if word:
        out.append(_pop(ctx, _word(ctx, word, ctx.cx, 46, 28), ctx.cx, 36, .3, .8))
    return "".join(out)


def rush(ctx, word="ORA", color=GOLD, **_):
    out = []
    for i in range(16):
        a = ctx.rnd.uniform(0, 2 * math.pi)
        r = ctx.rnd.uniform(55, 135)
        x, y = ctx.cx + r * math.cos(a), ctx.cy + r * math.sin(a)
        fist = (f'<g><rect x="{x - 14:.1f}" y="{y - 11:.1f}" width="28" height="22" rx="8" fill="{color}" stroke="{INK}" stroke-width="2.5"/>'
                f'<path d="M{x - 5:.1f} {y - 11:.1f}v9M{x + 4:.1f} {y - 11:.1f}v9" stroke="{INK}" stroke-width="2"/>'
                f'<path d="M{x - 14:.1f} {y:.1f}h-20M{x - 14:.1f} {y + 6:.1f}h-14" stroke="#fff" stroke-width="2" opacity=".7"/></g>')
        out.append(_pop(ctx, fist, x, y, i * .05, .15 + (15 - i) * .02, ctx.rnd.uniform(-30, 30)))
    for k in range(4):
        x = ctx.cx + (-95 if k % 2 else 95) + ctx.rnd.uniform(-20, 20)
        y = 60 + k * 58
        out.append(_pop(ctx, _word(ctx, word + "!", x, y, 24), x, y - 10, .1 + k * .15, .5, (-12 if k % 2 else 10)))
    return "".join(out)


def explosion(ctx, word="CLICK!", color="#ffb347", **_):
    out = []
    if word:
        out.append(_pop(ctx, _word(ctx, word, ctx.cx, 60, 26), ctx.cx, 50, 0, .35))
    burst = []
    for i in range(28):
        rr = 100 if i % 2 == 0 else 62
        a = i * math.pi / 14
        burst.append((ctx.cx + rr * math.cos(a), ctx.cy + rr * math.sin(a)))
    name = ctx.kf([(0, "opacity:1;transform:scale(0)"), (.25, "opacity:1;transform:scale(1.5)"), (.6, "opacity:1;transform:scale(1.7)"),
                   (.95, "opacity:0;transform:scale(2)")])
    out.append(f'<g {ctx.style(name, .4, (ctx.cx, ctx.cy))}><polygon points="{poly(burst)}" fill="{color}" stroke="{INK}" stroke-width="3"/>'
               f'<circle cx="{ctx.cx}" cy="{ctx.cy}" r="45" fill="#fff"/></g>')
    for i in range(12):
        a = ctx.rnd.uniform(0, 2 * math.pi)
        d = ctx.rnd.uniform(120, 200)
        chunk = f'<rect x="{ctx.cx - 4}" y="{ctx.cy - 4}" width="8" height="8" fill="{INK}"/>'
        out.append(_move(ctx, chunk, [(0, 0), (d * math.cos(a), d * math.sin(a))], .7, .45, spin=360, fade_in=.05,
                         origin=(ctx.cx, ctx.cy)))
    return "".join(out)


def zipper(ctx, color="#e0e0e0", **_):
    x0, y0, x1, y1 = 60, 30, 320, 270
    n = 22
    out = []
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    for k in range(n):
        t = k / (n - 1)
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        side = 1 if k % 2 else -1
        tooth = (f'<rect x="{x - 4:.1f}" y="{y - 7 + side * 5:.1f}" width="8" height="10" rx="1.5" fill="{color}" stroke="{INK}" '
                 f'stroke-width="1" transform="rotate({ang:.0f} {x:.1f} {y:.1f})"/>')
        name = ctx.kf([(0, "opacity:0"), (.05, "opacity:1;transform:none"), (.75, "opacity:1;transform:none"),
                       (1.0, f"opacity:1;transform:translate({side * -8 * math.sin(math.radians(ang)):.1f}px,{side * 8 * math.cos(math.radians(ang)):.1f}px)"),
                       (1.4, "opacity:0")])
        out.append(f"<g {ctx.style(name, t * .55)}>{tooth}</g>")
    slider = (f'<rect x="{x0 - 10}" y="{y0 - 14}" width="20" height="28" rx="5" fill="{GOLD}" stroke="{INK}" stroke-width="2" '
              f'transform="rotate({ang:.0f} {x0} {y0})"/>')
    out.append(_move(ctx, slider, [(0, 0), (x1 - x0, y1 - y0)], .6, 0, fade_in=.03))
    return "".join(out)


def bullets(ctx, color="#ffd27a", n=7, **_):
    out = []
    for i in range(n):
        y = ctx.rnd.uniform(40, 260)
        left = i % 2 == 0
        x0 = -40 if left else 420
        tx = ctx.cx + ctx.rnd.uniform(-60, 60) - x0
        b = (f'<g><path d="M{x0 + (-70 if left else 70)} {y:.1f}H{x0}" stroke="#fff" stroke-width="2" opacity=".6"/>'
             f'<rect x="{x0 - 9}" y="{y - 4:.1f}" width="18" height="8" rx="4" fill="{color}" stroke="{INK}" stroke-width="1.5"/></g>')
        out.append(_move(ctx, b, [(0, 0), (tx, ctx.rnd.uniform(-20, 20)), (tx * 1.6, ctx.rnd.uniform(-40, 40))], .7, i * .09,
                         fade_in=.03))
    return "".join(out)


def sfx(ctx, words=("ドドド",), color=GOLD, **_):
    out = []
    spots = [(ctx.cx - 70, 70), (ctx.cx + 80, 120), (ctx.cx - 60, 220), (ctx.cx + 60, 250), (ctx.cx, 40)]
    for k, w in enumerate(words):
        x, y = spots[k % len(spots)]
        out.append(_pop(ctx, _word(ctx, w, x, y, 26 if len(w) < 8 else 20, color), x, y - 10, k * .22, .7 - k * .1,
                        -10 if k % 2 else 8))
    return "".join(out)


def pages(ctx, color="#fff8ea", **_):
    out = []
    for i in range(8):
        a = i * 45 + ctx.rnd.uniform(-15, 15)
        x, y = ctx.cx + 110 * math.cos(math.radians(a)), ctx.cy + 100 * math.sin(math.radians(a))
        page = (f'<g><rect x="{x - 20:.1f}" y="{y - 26:.1f}" width="40" height="52" rx="2" fill="{color}" stroke="{INK}" stroke-width="2"/>'
                + "".join(f'<path d="M{x - 13:.1f} {y - 16 + j * 9:.1f}h26" stroke="#9a8f80" stroke-width="2"/>' for j in range(5)) + "</g>")
        out.append(_move(ctx, page, [(-(x - ctx.cx) * 2.2, -(y - ctx.cy) * 2.2), (0, 0), (0, 0), ((x - ctx.cx) * .6, 40)], 1.4,
                         i * .05, spin=ctx.rnd.choice([-1, 1]) * 200, origin=(x, y)))
    return "".join(out)


def void(ctx, color=INK, **_):
    pts = []
    for i in range(36):
        r = 105 + (10 if i % 2 else -6) + ctx.rnd.uniform(-6, 6)
        a = i * math.pi / 18
        pts.append((ctx.cx + r * math.cos(a), ctx.cy + r * math.sin(a)))
    name = ctx.kf([(0, "opacity:1;transform:scale(0)"), (.45, "opacity:1;transform:scale(1)"), (1.0, "opacity:1;transform:scale(1.05)"),
                   (1.4, "opacity:0;transform:scale(0)")])
    out = [f'<g {ctx.style(name, 0, (ctx.cx, ctx.cy))}><polygon points="{poly(pts)}" fill="{color}" stroke="#a26bff" stroke-width="4"/></g>']
    for i in range(18):
        a = ctx.rnd.uniform(0, 2 * math.pi)
        d = ctx.rnd.uniform(150, 220)
        dot = f'<circle cx="{ctx.cx + d * math.cos(a):.1f}" cy="{ctx.cy + d * math.sin(a):.1f}" r="4" fill="#d9c7ff"/>'
        out.append(_move(ctx, dot, [(0, 0), (-d * math.cos(a), -d * math.sin(a))], .8, .2 + i * .02, fade_in=.05))
    return "".join(out)


def shadow(ctx, color="#0a0612", **_):
    out = []
    for i in range(7):
        x0 = 50 + i * 47
        pts = [(x0, 310)] + [(x0 + ctx.rnd.uniform(-30, 30), 310 - k * 45) for k in range(1, 6)]
        out.append(_draw(ctx, _smooth(pts), color, 14, i * .05, .5, 'opacity=".85"'))
    name = ctx.kf([(0, "opacity:.9;transform:scaleX(0)"), (.4, "opacity:.9;transform:scaleX(1)"), (1.1, "opacity:.9;transform:scaleX(1)"),
                   (1.5, "opacity:0;transform:scaleX(1)")])
    out.append(f'<ellipse cx="{ctx.cx}" cy="285" rx="170" ry="26" fill="{color}" {ctx.style(name, 0, (ctx.cx, 285))}/>')
    return "".join(out)


def mirror(ctx, color="#d6f1ff", **_):
    out = []
    flash = ctx.kf([(0, "opacity:0"), (.08, "opacity:.9"), (.3, "opacity:0")])
    out.append(f'<circle cx="{ctx.cx}" cy="{ctx.cy}" r="140" fill="#fff" {ctx.style(flash, .05)}/>')
    for i in range(12):
        a = ctx.rnd.uniform(0, 2 * math.pi)
        s = ctx.rnd.uniform(14, 34)
        tri = poly([(ctx.cx, ctx.cy - s), (ctx.cx + s * .8, ctx.cy + s * .6), (ctx.cx - s * .7, ctx.cy + s * .4)])
        shard = f'<polygon points="{tri}" fill="{color}" fill-opacity=".75" stroke="#fff" stroke-width="1.5"/>'
        d = ctx.rnd.uniform(110, 190)
        out.append(_move(ctx, shard, [(0, 0), (d * math.cos(a), d * math.sin(a))], 1.0, .05, spin=ctx.rnd.uniform(-300, 300),
                         fade_in=.04, origin=(ctx.cx, ctx.cy)))
    return "".join(out)


def sand(ctx, color="#e3c48a", n=50, **_):
    out = []
    for i in range(n):
        a = ctx.rnd.uniform(0, 2 * math.pi)
        r = ctx.rnd.uniform(140, 230)
        x, y = ctx.cx + r * math.cos(a), ctx.cy + r * math.sin(a)
        mid = (ctx.cx + r * .5 * math.cos(a + 1.2) - x, ctx.cy + r * .5 * math.sin(a + 1.2) - y)
        g = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{ctx.rnd.uniform(1.8, 3.6):.1f}" fill="{color}"/>'
        out.append(_move(ctx, g, [(0, 0), mid, (ctx.cx - x, ctx.cy - y)], .9, ctx.rnd.uniform(0, .35)))
    return "".join(out)


def mist(ctx, color="#e8e8f0", **_):
    fid = f"{ctx.p}blur"
    ctx.defs.append(f'<filter id="{fid}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14"/></filter>')
    out = []
    for i in range(7):
        y = ctx.rnd.uniform(50, 260)
        x = ctx.rnd.uniform(-40, 340)
        cl = f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{ctx.rnd.uniform(70, 120):.0f}" ry="{ctx.rnd.uniform(28, 46):.0f}" fill="{color}" opacity=".55" filter="url(#{fid})"/>'
        out.append(_move(ctx, cl, [(-60, 0), (20, 0), (90, 0)], 1.6, i * .06))
    return "".join(out)


def rain(ctx, color="#9fd4ff", heavy=False, **_):
    out = []
    w, L = (3.5, 28) if heavy else (1.6, 18)
    for i in range(40 if not heavy else 26):
        x = ctx.rnd.uniform(20, 370)
        drop = f'<path d="M{x:.1f} -30l-4 {L}" stroke="{color}" stroke-width="{w}" stroke-linecap="round"/>'
        out.append(_move(ctx, drop, [(0, 0), (-40, 360)], .55, ctx.rnd.uniform(0, 1.0), fade_in=.02))
    if heavy:
        for i in range(6):
            x = ctx.rnd.uniform(60, 320)
            out.append(_pop(ctx, f'<ellipse cx="{x:.1f}" cy="288" rx="18" ry="5" fill="none" stroke="{color}" stroke-width="3"/>',
                            x, 288, .5 + i * .12, .2))
    return "".join(out)


def spores(ctx, color="#9be15d", n=42, **_):
    out = []
    for i in range(n):
        a = ctx.rnd.uniform(0, 2 * math.pi)
        d = ctx.rnd.uniform(60, 190)
        dot = f'<circle cx="{ctx.cx}" cy="{ctx.cy}" r="{ctx.rnd.uniform(2, 5):.1f}" fill="{color}" stroke="#fff" stroke-width=".6"/>'
        out.append(_move(ctx, dot, [(0, 0), (d * .6 * math.cos(a), d * .6 * math.sin(a)),
                                    (d * math.cos(a) + ctx.rnd.uniform(-20, 20), d * math.sin(a) - 30)],
                         1.2, ctx.rnd.uniform(0, .4), scale=(.4, 1.3)))
    return "".join(out)


def virus(ctx, color="#c070ff", **_):
    out = []
    for i in range(6):
        a = i * math.pi / 3
        x, y = ctx.cx + 70 * math.cos(a), ctx.cy + 70 * math.sin(a)
        cap = (f'<rect x="{x - 8:.1f}" y="{y - 14:.1f}" width="16" height="28" rx="8" fill="{color}" stroke="{INK}" stroke-width="2"/>'
               f'<path d="M{x - 8:.1f} {y:.1f}h16" stroke="{INK}" stroke-width="2"/>')
        out.append(_pop(ctx, cap, x, y, i * .06, .3, ctx.rnd.uniform(-40, 40)))
    return "".join(out) + spores(_Shift(ctx, .6), color=color, n=30)


def gravity(ctx, color="#c9b8ff", down=False, word="", **_):
    out = []
    for i in range(14):
        x = ctx.rnd.uniform(40, 340)
        s = ctx.rnd.uniform(6, 14)
        rock = f'<polygon points="{poly([(x - s, 0), (x, -s * .9), (x + s, -s * .2), (x + s * .5, s), (x - s * .6, s * .8)])}" fill="{color}" stroke="{INK}" stroke-width="1.5"/>'
        if down:
            out.append(_move(ctx, rock, [(0, -30), (0, 150), (0, 290)], .8, ctx.rnd.uniform(0, .5), spin=90, origin=(x, 0)))
        else:
            out.append(_move(ctx, rock, [(0, 300), (0, 160), (0, -30)], 1.2, ctx.rnd.uniform(0, .5), spin=360, origin=(x, 0)))
    for k in range(3):
        x = 70 + k * 120
        arrow = f'<path d="M{x} 130v40m-12 -12l12 12 12 -12" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round"/>'
        name = ctx.kf([(0, "opacity:1;transform:rotate(0)"), (.3, "opacity:1;transform:rotate(0)"),
                       (.6, f"opacity:1;transform:rotate({0 if down else 180}deg)"), (1.1, "opacity:0")])
        out.append(f"<g {ctx.style(name, k * .08, (x, 150))}>{arrow}</g>")
    if word:
        out.append(_pop(ctx, _word(ctx, word, ctx.cx, 50, 30), ctx.cx, 40, .2, .8))
    return "".join(out)


def dimension(ctx, **_):
    """Le drapeau : deux pans qui s'écartent comme une porte entre deux mondes."""
    out = []
    for side in (-1, 1):
        x = ctx.cx - 150 if side < 0 else ctx.cx
        flag = [f'<rect x="{x}" y="10" width="150" height="280" fill="#fff"/>']
        flag += [f'<rect x="{x}" y="{10 + k * 40}" width="150" height="20" fill="#c8102e"/>' for k in range(7)]
        if side < 0:
            flag.append(f'<rect x="{x}" y="10" width="80" height="110" fill="#1d3f8f"/>')
            flag += [f'<circle cx="{x + 12 + (k % 4) * 18}" cy="{24 + (k // 4) * 22}" r="3" fill="#fff"/>' for k in range(16)]
        name = ctx.kf([(0, "opacity:1;transform:translateX(0)"), (.35, "opacity:1;transform:translateX(0)"),
                       (1.0, f"opacity:1;transform:translateX({side * 175}px)"), (1.3, f"opacity:0;transform:translateX({side * 200}px)")])
        out.append(f"<g {ctx.style(name)}>{''.join(flag)}<rect x=\"{x}\" y=\"10\" width=\"150\" height=\"280\" fill=\"none\" "
                   f"stroke=\"{INK}\" stroke-width=\"3\"/></g>")
    return "".join(out)


def light(ctx, color="#fff6c8", walls=False, **_):
    out = []
    for i in range(14):
        a = i * 360 / 14
        beam = (f'<polygon points="{poly([(ctx.cx, ctx.cy), (ctx.cx + 260, ctx.cy - 14), (ctx.cx + 260, ctx.cy + 14)])}" fill="{color}" '
                f'opacity=".5" transform="rotate({a:.0f} {ctx.cx} {ctx.cy})"/>')
        name = ctx.kf([(0, "opacity:0;transform:scale(0) rotate(0)"), (.4, "opacity:1;transform:scale(1) rotate(15deg)"),
                       (1.1, "opacity:1;transform:scale(1) rotate(30deg)"), (1.5, "opacity:0;transform:scale(1.1) rotate(40deg)")])
        out.append(f"<g {ctx.style(name, i * .02, (ctx.cx, ctx.cy))}>{beam}</g>")
    if walls:
        for x in (ctx.cx - 130, ctx.cx + 110):
            w = f'<rect x="{x}" y="0" width="20" height="300" fill="#fffbe0"/><rect x="{x - 8}" y="0" width="36" height="300" fill="#fff6c8" opacity=".4"/>'
            name = ctx.kf([(0, "opacity:0;transform:scaleY(0)"), (.35, "opacity:1;transform:scaleY(1)"), (1.2, "opacity:1;transform:scaleY(1)"),
                           (1.6, "opacity:0;transform:scaleY(1)")])
            out.append(f"<g {ctx.style(name, .1, (x, 0))}>{w}</g>")
    flash = ctx.kf([(0, "opacity:0"), (.3, "opacity:.8"), (.6, "opacity:0")])
    out.append(f'<circle cx="{ctx.cx}" cy="{ctx.cy}" r="120" fill="#fff" {ctx.style(flash, .1)}/>')
    return "".join(out)


def slice_(ctx, color="#ffffff", **_):
    out = []
    for i, (a0, r) in enumerate(((-30, 120), (150, 100), (60, 140))):
        a1 = a0 + 120
        p0 = (ctx.cx + r * math.cos(math.radians(a0)), ctx.cy + r * math.sin(math.radians(a0)))
        p1 = (ctx.cx + r * math.cos(math.radians(a1)), ctx.cy + r * math.sin(math.radians(a1)))
        d = f"M{p0[0]:.1f} {p0[1]:.1f}A{r} {r} 0 0 1 {p1[0]:.1f} {p1[1]:.1f}"
        out.append(_draw(ctx, d, color, 7, i * .12, .35))
        out.append(_draw(ctx, d, "#a26bff", 2, i * .12 + .03, .35))
    return "".join(out)


def magnet(ctx, color="#b8c0cc", **_):
    out = []
    for i in range(44):
        a = ctx.rnd.uniform(0, 2 * math.pi)
        r0 = ctx.rnd.uniform(160, 240)
        r1 = ctx.rnd.uniform(60, 110)
        x, y = ctx.cx + r0 * math.cos(a), ctx.cy + r0 * math.sin(a)
        f = f'<path d="M{x - 5:.1f} {y:.1f}h10" stroke="{color}" stroke-width="2.5" stroke-linecap="round"/>'
        out.append(_move(ctx, f, [(0, 0), ((r1 - r0) * math.cos(a), (r1 - r0) * math.sin(a))], .8, ctx.rnd.uniform(0, .3),
                         spin=math.degrees(a), origin=(x, y)))
    return "".join(out)


def bubbles(ctx, color="#bfe8ff", balloon=False, n=16, **_):
    out = []
    for i in range(n):
        x = ctx.rnd.uniform(50, 330)
        r = ctx.rnd.uniform(8, 20) * (1.6 if balloon else 1)
        if balloon:
            c = ctx.rnd.choice(["#ff6b9a", "#ffd23f", "#6bd4ff", "#a26bff", "#7ae582"])
            b = (f'<g><path d="M{x:.1f} {300 + r:.1f}q-6 20 4 40" fill="none" stroke="#fff" stroke-width="1.2"/>'
                 f'<circle cx="{x:.1f}" cy="300" r="{r:.1f}" fill="{c}" stroke="{INK}" stroke-width="2"/>'
                 f'<ellipse cx="{x - r * .35:.1f}" cy="{300 - r * .4:.1f}" rx="{r * .25:.1f}" ry="{r * .15:.1f}" fill="#fff" opacity=".7"/></g>')
        else:
            b = (f'<g><circle cx="{x:.1f}" cy="300" r="{r:.1f}" fill="{color}" fill-opacity=".18" stroke="{color}" stroke-width="2"/>'
                 f'<ellipse cx="{x - r * .35:.1f}" cy="{300 - r * .4:.1f}" rx="{r * .3:.1f}" ry="{r * .18:.1f}" fill="#fff" opacity=".8"/></g>')
        rise = ctx.rnd.uniform(150, 280)
        out.append(_move(ctx, b, [(0, 0), (ctx.rnd.uniform(-20, 20), -rise * .6), (ctx.rnd.uniform(-30, 30), -rise)], 1.2,
                         ctx.rnd.uniform(0, .45), origin=(x, 300), scale=(.3 if balloon else .6, 1.1)))
    return "".join(out)


def goldspin(ctx, color=GOLD, **_):
    g = art.golden(ctx.cx, ctx.cy, 320, color, 1.6, .35, .95)
    name = ctx.kf([(0, "opacity:1;transform:rotate(0) scale(.2)"), (.8, "opacity:1;transform:rotate(540deg) scale(1)"),
                   (1.2, "opacity:1;transform:rotate(620deg) scale(1)"), (1.6, "opacity:0;transform:rotate(700deg) scale(1.1)")])
    return f"<g {ctx.style(name, 0, (ctx.cx, ctx.cy))}>{g}</g>"


def money(ctx, kind="bill", color="#7cc47f", **_):
    out = []
    for i in range(18):
        x = ctx.rnd.uniform(30, 350)
        if kind == "bill":
            it = (f'<g><rect x="{x - 18:.1f}" y="-40" width="36" height="18" rx="2" fill="{color}" stroke="#2d5a2e" stroke-width="1.5"/>'
                  f'<circle cx="{x:.1f}" cy="-31" r="5" fill="none" stroke="#2d5a2e" stroke-width="1.5"/></g>')
        elif kind == "card":
            it = (f'<g><rect x="{x - 12:.1f}" y="-48" width="24" height="34" rx="3" fill="#fff" stroke="{INK}" stroke-width="1.5"/>'
                  f'<polygon points="{poly([(x, -40), (x + 6, -31), (x, -22), (x - 6, -31)])}" fill="#d62828"/></g>')
        elif kind == "chip":
            it = (f'<g><circle cx="{x:.1f}" cy="-30" r="12" fill="{color}" stroke="{INK}" stroke-width="2"/>'
                  f'<circle cx="{x:.1f}" cy="-30" r="7" fill="none" stroke="#fff" stroke-width="2" stroke-dasharray="3 3"/></g>')
        else:  # feuille de ginkgo
            it = (f'<path d="M{x:.1f} -24l-14 -16q14 -12 28 0z" fill="{color}" stroke="#8a6d00" stroke-width="1.2"/>'
                  f'<path d="M{x:.1f} -24v10" stroke="#8a6d00" stroke-width="1.5"/>')
        fall = ctx.rnd.uniform(260, 340)
        out.append(_move(ctx, it, [(0, 0), (ctx.rnd.uniform(-30, 30), fall * .5), (ctx.rnd.uniform(-40, 40), fall)], 1.3,
                         ctx.rnd.uniform(0, .5), spin=ctx.rnd.uniform(-360, 360), origin=(x, -30), fade_in=.05))
    return "".join(out)


def shrink(ctx, color="#ffd1f0", **_):
    out = []
    for k in range(4):
        name = ctx.kf([(0, "opacity:0;transform:scale(1)"), (.1, "opacity:1;transform:scale(1)"), (.8, "opacity:.8;transform:scale(0)")])
        out.append(f'<circle cx="{ctx.cx}" cy="{ctx.cy}" r="160" fill="none" stroke="{color}" stroke-width="3" '
                   f'{ctx.style(name, k * .2, (ctx.cx, ctx.cy))}/>')
    star = f'<polygon points="{poly([(ctx.cx + (14 if i % 2 == 0 else 5) * math.cos(i * math.pi / 4), ctx.cy + (14 if i % 2 == 0 else 5) * math.sin(i * math.pi / 4)) for i in range(8)])}" fill="#fff"/>'
    out.append(_pop(ctx, star, ctx.cx, ctx.cy, .85, .2))
    return "".join(out)


def army(ctx, color="#9aa77b", swarm=False, **_):
    out = []
    for i in range(20):
        row, col = i // 5, i % 5
        x, y = 70 + col * 28 + row * 10, 200 + row * 22
        if swarm:
            u = f'<ellipse cx="{x}" cy="{y}" rx="8" ry="5" fill="{color}" stroke="{INK}" stroke-width="1.2"/><circle cx="{x + 7}" cy="{y - 2}" r="2" fill="{INK}"/>'
        else:
            u = (f'<g><rect x="{x - 4}" y="{y - 6}" width="8" height="12" rx="2" fill="{color}" stroke="{INK}" stroke-width="1"/>'
                 f'<circle cx="{x}" cy="{y - 9}" r="3.5" fill="{color}" stroke="{INK}" stroke-width="1"/>'
                 f'<path d="M{x + 4} {y - 3}h7" stroke="{INK}" stroke-width="2"/></g>')
        out.append(_move(ctx, u, [(-260, 0), (-120, -4), (0, 0), (0, 0)], 1.4, i * .03))
    return "".join(out)


def stickers(ctx, color="#ff6b9a", **_):
    out = []
    for i in range(7):
        a = ctx.rnd.uniform(0, 2 * math.pi)
        r = ctx.rnd.uniform(60, 130)
        x, y = ctx.cx + r * math.cos(a), ctx.cy + r * math.sin(a)
        heart = f'<path d="M{x:.1f} {y + 7:.1f}c-12 -8 -12 -18 -4 -20 4 -1 4 3 4 3s0 -4 4 -3c8 2 8 12 -4 20z" fill="{color}"/>'
        st = f'<g><rect x="{x - 18:.1f}" y="{y - 16:.1f}" width="36" height="32" rx="5" fill="#fff" stroke="{INK}" stroke-width="2"/>{heart}</g>'
        out.append(_pop(ctx, st, x, y, i * .1, .6, ctx.rnd.uniform(-25, 25)))
    return "".join(out)


def meteors(ctx, color="#ff8a3d", **_):
    out = []
    for i in range(7):
        x0 = ctx.rnd.uniform(220, 420)
        m = (f'<g><path d="M{x0:.1f} -40l60 -40" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity=".5"/>'
             f'<circle cx="{x0:.1f}" cy="-40" r="11" fill="#ffd27a" stroke="{color}" stroke-width="4"/></g>')
        out.append(_move(ctx, m, [(0, 0), (-260, 300)], .7, i * .14, fade_in=.03))
    return "".join(out)


def footprints(ctx, color="#e0e0e0", **_):
    out = []
    for k in range(10):
        t = k / 9
        x = 40 + t * (ctx.cx - 40)
        y = 280 - t * 120 + (8 if k % 2 else -8)
        fp = (f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="6" ry="10" fill="{color}" transform="rotate(60 {x:.1f} {y:.1f})"/>'
              f'<circle cx="{x + 9:.1f}" cy="{y - 6:.1f}" r="3" fill="{color}"/>')
        out.append(_pop(ctx, fp, x, y, k * .08, .7 - k * .05))
    return "".join(out)


def afterimage(ctx, **_):
    out = []
    for k, dx in enumerate((-180, -130, -80, -35)):
        name = ctx.kf([(0, f"opacity:0;transform:translateX({dx - 60}px)"), (.2, f"opacity:.35;transform:translateX({dx}px)"),
                       (.7, "opacity:.25;transform:translateX(0)"), (.9, "opacity:0;transform:translateX(0)")])
        out.append(f'<use href="#{ctx.img_id}" {ctx.style(name, k * .07)}/>')
    return "".join(out)


def slash(ctx, color="#ffffff", **_):
    out = []
    for i in range(3):
        y = 70 + i * 80
        d = f"M40 {y + 40}Q{ctx.cx} {y - 50} 340 {y + 10}"
        out.append(_draw(ctx, d, color, 6, i * .14, .25))
        out.append(_draw(ctx, d, "#a26bff", 2, i * .14 + .03, .25))
    return "".join(out)


def lock(ctx, color="#c9ced6", **_):
    x, y = ctx.cx, ctx.cy
    lk = (f'<g><path d="M{x - 26} {y - 10}v-24a26 26 0 0 1 52 0v24" fill="none" stroke="{color}" stroke-width="10"/>'
          f'<rect x="{x - 44}" y="{y - 12}" width="88" height="70" rx="10" fill="{color}" stroke="{INK}" stroke-width="3"/>'
          f'<circle cx="{x}" cy="{y + 16}" r="8" fill="{INK}"/><path d="M{x} {y + 18}v18" stroke="{INK}" stroke-width="6"/></g>')
    name = ctx.kf([(0, "opacity:1;transform:translateY(-280px)"), (.4, "opacity:1;transform:translateY(0)"),
                   (.5, "opacity:1;transform:translateY(-12px)"), (.6, "opacity:1;transform:translateY(0)"), (1.2, "opacity:1;transform:none"),
                   (1.5, "opacity:0;transform:none")])
    return f"<g {ctx.style(name)}>{lk}</g>" + _pop(ctx, _word(ctx, "GACHAN!", ctx.cx, 50, 26), ctx.cx, 40, .42, .6)


def heat(ctx, color="#ff7a3d", **_):
    out = []
    for i in range(9):
        y = 290 - i * 8
        d = "M30 {}".format(y) + "".join(f"q20 -12 40 0t40 0" for _ in range(4))
        name = ctx.kf([(0, "opacity:0;transform:translateY(0)"), (.2, "opacity:.9"), (1.2, "opacity:0;transform:translateY(-200px)")])
        out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="3" {ctx.style(name, i * .09)}/>')
    return "".join(out)


def glitch(ctx, color="#ff2e4d", **_):
    out = []
    for i in range(9):
        y = ctx.rnd.uniform(20, 270)
        h = ctx.rnd.uniform(6, 22)
        bar = f'<rect x="20" y="{y:.1f}" width="340" height="{h:.1f}" fill="{color}" opacity=".55"/>'
        frames = [(0, "opacity:0;transform:translateX(0)")]
        for k in range(1, 7):
            frames.append((k * .12, f"opacity:{1 if k % 2 else .2};transform:translateX({ctx.rnd.uniform(-60, 60):.0f}px)"))
        frames.append((1.0, "opacity:0;transform:translateX(0)"))
        out.append(f"<g {ctx.style(ctx.kf(frames), i * .04)}>{bar}</g>")
    return "".join(out)


def souls(ctx, color="#d9d2ff", **_):
    out = []
    for i in range(6):
        x = 70 + i * 50
        w = (f'<path d="M{x} 300c-14 -20 10 -30 -2 -52s14 -26 2 -46" fill="none" stroke="{color}" stroke-width="10" '
             f'stroke-linecap="round" opacity=".55"/><circle cx="{x + 2}" cy="196" r="12" fill="{color}" opacity=".7"/>')
        out.append(_move(ctx, w, [(0, 60), (ctx.rnd.uniform(-30, 30), -40), (ctx.rnd.uniform(-60, 60), -140)], 1.4, i * .08))
    return "".join(out)


def zero(ctx, color=GOLD, **_):
    out = []
    for k in range(5):
        name = ctx.kf([(0, "opacity:0;transform:scale(1.4)"), (.1, "opacity:1;transform:scale(1.4)"), (.9, "opacity:.9;transform:scale(0)")])
        out.append(f'<circle cx="{ctx.cx}" cy="{ctx.cy}" r="120" fill="none" stroke="{color}" stroke-width="4" '
                   f'{ctx.style(name, k * .14, (ctx.cx, ctx.cy))}/>')
    out.append(_pop(ctx, _word(ctx, "0", ctx.cx, ctx.cy + 22, 64), ctx.cx, ctx.cy, .75, .4))
    return "".join(out)


def discs(ctx, **_):
    out = []
    for i in range(6):
        a = i * 60 + ctx.rnd.uniform(-10, 10)
        x, y = ctx.cx + 115 * math.cos(math.radians(a)), ctx.cy + 100 * math.sin(math.radians(a))
        dsk = (f'<g><circle cx="{x:.1f}" cy="{y:.1f}" r="22" fill="#e8e8f2" stroke="{INK}" stroke-width="2"/>'
               f'<path d="M{x - 16:.1f} {y - 8:.1f}a18 18 0 0 1 20 -12" stroke="#ff9de6" stroke-width="4" fill="none"/>'
               f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{INK}"/></g>')
        out.append(_move(ctx, dsk, [(-(x - ctx.cx) * 2, -(y - ctx.cy) * 2), (0, 0), (0, 0), (-(x - ctx.cx) * .7, -(y - ctx.cy) * .7)],
                         1.3, i * .06, spin=360, origin=(x, y)))
    return "".join(out)


def grid(ctx, color="#ffb3d9", **_):
    out = []
    for k in range(7):
        x = 40 + k * 50
        out.append(_draw(ctx, f"M{x} 20V290", color, 2, k * .03, .7))
        y = 20 + k * 45
        out.append(_draw(ctx, f"M30 {y}H350", color, 2, k * .03 + .02, .7))
    out.append(_pop(ctx, f'<rect x="190" y="110" width="50" height="45" fill="{color}" opacity=".6"/>', 215, 132, .6, .5))
    return "".join(out)


def aura(ctx, color="#a26bff", **_):
    out = []
    for i in range(22):
        a = i * 2 * math.pi / 22
        d = (f"M{ctx.cx + 70 * math.cos(a):.1f} {ctx.cy + 70 * math.sin(a):.1f}"
             f"L{ctx.cx + 200 * math.cos(a):.1f} {ctx.cy + 200 * math.sin(a):.1f}")
        out.append(_draw(ctx, d, GOLD if i % 2 else color, 3, i * .015, .3))
    for k in range(2):
        name = ctx.kf([(0, "opacity:.9;transform:scale(.2)"), (.9, "opacity:0;transform:scale(1.3)")])
        out.append(f'<circle cx="{ctx.cx}" cy="{ctx.cy}" r="130" fill="none" stroke="{color}" stroke-width="6" '
                   f'{ctx.style(name, .1 + k * .3, (ctx.cx, ctx.cy))}/>')
    for k, (x, y) in enumerate(((ctx.cx - 110, 70), (ctx.cx + 115, 110), (ctx.cx - 100, 240))):
        out.append(_pop(ctx, ctx.D.text("ゴ", x, y, 34, color, INK, 3, anchor="middle", skew=-12), x, y - 12, .15 + k * .15, .6))
    return "".join(out)


def knives(ctx, n=9, **_):
    """Les couteaux de DIO : lancés, figés en l'air (le temps est arrêté), puis ils retombent."""
    out = []
    for i in range(n):
        y = 40 + i * (220 / (n - 1)) + ctx.rnd.uniform(-8, 8)
        x = ctx.cx + ctx.rnd.uniform(-70, 40)
        k = (f'<g transform="rotate({ctx.rnd.uniform(-12, 12):.0f} {x:.1f} {y:.1f})">'
             f'<polygon points="{poly([(x - 34, y), (x + 4, y - 5), (x + 4, y + 5)])}" fill="#e8eef5" stroke="{INK}" stroke-width="1.5"/>'
             f'<rect x="{x + 4:.1f}" y="{y - 6:.1f}" width="4" height="12" fill="{GOLD}" stroke="{INK}" stroke-width="1"/>'
             f'<rect x="{x + 8:.1f}" y="{y - 3.5:.1f}" width="18" height="7" rx="2" fill="#6b3d1f" stroke="{INK}" stroke-width="1"/></g>')
        name = ctx.kf([(0, "opacity:1;transform:translate(260px,0)"), (.3, "opacity:1;transform:translate(0,0)"),
                       (1.0, "opacity:1;transform:translate(0,0)"), (1.3, "opacity:1;transform:translate(-30px,60px) rotate(30deg)"),
                       (1.5, "opacity:0;transform:translate(-40px,90px)")])
        out.append(f"<g {ctx.style(name, i * .03, (x, y))}>{k}</g>")
    return "".join(out)


def gun(ctx, color="#ffd27a", **_):
    """Un coup de pistolet : flamme au canon, puis la balle (qui peut tourner en vol)."""
    mx, my = 30, 120
    flash = poly([(mx + (34 if i % 2 == 0 else 12) * math.cos(i * math.pi / 6), my + (34 if i % 2 == 0 else 12) * math.sin(i * math.pi / 6))
                  for i in range(12)])
    out = [_pop(ctx, f'<polygon points="{flash}" fill="#fff36b" stroke="#ff8a3d" stroke-width="3"/>', mx, my, 0, .15)]
    for i in range(3):
        b = (f'<g><path d="M{mx - 30} {my}H{mx}" stroke="#fff" stroke-width="2" opacity=".6"/>'
             f'<rect x="{mx - 9}" y="{my - 4}" width="18" height="8" rx="4" fill="{color}" stroke="{INK}" stroke-width="1.5"/></g>')
        out.append(_move(ctx, b, [(0, 0), (120, -40 + i * 40), (ctx.cx - mx + 10, -10 + i * 30)], .55, .08 + i * .1, fade_in=.02))
    return "".join(out)


def gasoline(ctx, **_):
    """L'essence qui gicle, l'allumette qu'on gratte, et tout s'embrase."""
    out = []
    for i in range(14):
        x = ctx.rnd.uniform(60, 320)
        drop = f'<ellipse cx="{x:.1f}" cy="-10" rx="4" ry="6" fill="#ffb21f" fill-opacity=".85" stroke="#8a5a00" stroke-width="1"/>'
        out.append(_move(ctx, drop, [(0, 0), (0, ctx.rnd.uniform(220, 300))], .45, ctx.rnd.uniform(0, .3), fade_in=.03))
    mx, my = ctx.cx + 60, 70
    match = (f'<g><rect x="{mx - 2}" y="{my}" width="4" height="46" fill="#e8c88a" stroke="{INK}" stroke-width="1"/>'
             f'<ellipse cx="{mx}" cy="{my}" rx="4" ry="6" fill="#d62828"/>'
             f'<path d="M{mx} {my - 2}c8 -8 4 -18 0 -24c-4 6 -8 16 0 24z" fill="#ffb21f"/></g>')
    out.append(_pop(ctx, match, mx, my + 20, .35, .35, 20))
    return "".join(out) + flames(_Shift(ctx, .75), n=14)


def emeralds(ctx, color="#3ddc84", n=14, **_):
    """Emerald Splash : une salve d'émeraudes."""
    out = []
    for i in range(n):
        a = ctx.rnd.uniform(-.5, .5)
        y0 = ctx.cy + ctx.rnd.uniform(-30, 30)
        gem = f'<polygon points="{poly([(ctx.cx, y0 - 7), (ctx.cx + 6, y0), (ctx.cx, y0 + 7), (ctx.cx - 6, y0)])}" fill="{color}" stroke="#eafff2" stroke-width="1.2"/>'
        d = ctx.rnd.uniform(160, 240)
        out.append(_move(ctx, gem, [(0, 0), (d * math.cos(a + math.pi), d * math.sin(a))], .6, .1 + i * .04, spin=180,
                         fade_in=.03, origin=(ctx.cx, y0)))
    out.append(_pop(ctx, _word(ctx, "EMERALD SPLASH!", ctx.cx, 46, 22, "#7dffb0"), ctx.cx, 36, .05, .6))
    return "".join(out)


def ankh(ctx, color="#ff6a1f", **_):
    """Crossfire Hurricane : une croix ansée de feu."""
    x, y = ctx.cx, ctx.cy
    shape = (f'<g fill="none" stroke="{color}" stroke-width="12" stroke-linecap="round">'
             f'<ellipse cx="{x}" cy="{y - 40}" rx="22" ry="28"/><path d="M{x} {y - 12}V{y + 70}M{x - 44} {y + 4}H{x + 44}"/></g>'
             f'<g fill="none" stroke="#ffe36b" stroke-width="4" stroke-linecap="round">'
             f'<ellipse cx="{x}" cy="{y - 40}" rx="22" ry="28"/><path d="M{x} {y - 12}V{y + 70}M{x - 44} {y + 4}H{x + 44}"/></g>')
    name = ctx.kf([(0, "opacity:0;transform:scale(.3)"), (.3, "opacity:1;transform:scale(1.1)"), (.45, "opacity:1;transform:scale(1)"),
                   (1.0, "opacity:1;transform:scale(1)"), (1.4, "opacity:0;transform:scale(1.6) translateX(80px)")])
    return f"<g {ctx.style(name, .2, (x, y))}>{shape}</g>"


def restore(ctx, color="#ff9de6", **_):
    """Crazy Diamond : les morceaux reviennent en place."""
    out = []
    for i in range(14):
        a = ctx.rnd.uniform(0, 2 * math.pi)
        s = ctx.rnd.uniform(12, 26)
        tri = poly([(ctx.cx, ctx.cy - s), (ctx.cx + s * .8, ctx.cy + s * .6), (ctx.cx - s * .7, ctx.cy + s * .4)])
        shard = f'<polygon points="{tri}" fill="{color}" fill-opacity=".7" stroke="#fff" stroke-width="1.5"/>'
        d = ctx.rnd.uniform(130, 200)
        out.append(_move(ctx, shard, [(d * math.cos(a), d * math.sin(a)), (0, 0)], .7, i * .02, spin=ctx.rnd.uniform(-360, 360),
                         origin=(ctx.cx, ctx.cy)))
    return "".join(out) + _pop(ctx, f'<circle cx="{ctx.cx}" cy="{ctx.cy}" r="60" fill="none" stroke="#fff" stroke-width="3"/>',
                               ctx.cx, ctx.cy, .7, .1)


class _Shift:
    """Le même contexte, décalé dans le temps (pour enchaîner deux effets)."""

    def __init__(self, ctx: Ctx, dt: float):
        self.__dict__.update(ctx.__dict__)
        self._ctx, self.t0 = ctx, ctx.t0 + dt

    def kf(self, frames, hidden="opacity:0"):
        old, self._ctx.t0 = self._ctx.t0, self.t0
        try:
            return self._ctx.kf(frames, hidden)
        finally:
            self._ctx.t0 = old

    def style(self, *a, **k):
        return self._ctx.style(*a, **k)


EFFECTS = {f.__name__.rstrip("_"): f for f in (
    strings, vines, hooks, fishing, flames, ice, water, lightning, timestop, rewind, rush, explosion, zipper, bullets, sfx,
    pages, void, shadow, mirror, sand, mist, rain, spores, virus, gravity, dimension, light, slice_, magnet, bubbles,
    goldspin, money, shrink, army, stickers, meteors, footprints, afterimage, slash, lock, heat, glitch, souls, zero, discs,
    grid, aura, knives, gun, gasoline, emeralds, ankh, restore)}
DURATION = 1.9  # durée d'un effet, en secondes


def render(spec, ctx: Ctx) -> str:
    """spec : "nom", {"type": "nom", ...paramètres} ou une liste des deux."""
    if not spec:
        spec = "aura"
    if isinstance(spec, list):
        return "".join(render(s, ctx) for s in spec)
    if isinstance(spec, str):
        spec = {"type": spec}
    params = {k: v for k, v in spec.items() if k != "type"}
    if "words" in params:
        params["words"] = tuple(params["words"])
    if "colors" in params:
        params["colors"] = tuple(params["colors"])
    delay = params.pop("delay", 0)  # pour enchaîner : l'effet principal, puis la rafale de poings
    return EFFECTS[spec["type"]](_Shift(ctx, delay) if delay else ctx, **params)
