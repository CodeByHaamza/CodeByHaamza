"""Dessins partagés par les deux styles : la spirale dorée, la PSP, la main.

Tout est dessiné à la main en géométrie simple (pas de logo, pas d'image de console).
"""
from __future__ import annotations

import math

from .kit import PHI, poly

# ---------------------------------------------------------------- rotation dorée


def golden(cx: float, cy: float, width: float, color: str, sw: float = 1.4, rect_op: float = .35,
           spiral_op: float = .9, steps: int = 11) -> str:
    """Rectangle d'or découpé en carrés + la spirale qui les traverse.

    Le pôle de la spirale (le point vers lequel elle s'enroule) est placé en (cx, cy) :
    c'est le centre de rotation de l'objet qui tourne."""
    x, y, w, h = 0.0, 0.0, width, width / PHI
    squares, arcs = [], []
    for i in range(steps + 30):
        s = min(w, h)
        d = i % 4
        if d == 0:    # carré à gauche
            sq, a0, a1, rest = (x, y), (x, y + s), (x + s, y), (x + s, y, w - s, h)
        elif d == 1:  # en haut
            sq, a0, a1, rest = (x, y), (x, y), (x + s, y + s), (x, y + s, w, h - s)
        elif d == 2:  # à droite
            sq, a0, a1, rest = (x + w - s, y), (x + w, y), (x + w - s, y + s), (x, y, w - s, h)
        else:         # en bas
            sq, a0, a1, rest = (x, y + h - s), (x + s, y + h), (x, y + h - s), (x, y, w, h - s)
        if i < steps:
            squares.append((sq[0], sq[1], s))
            arcs.append((a0, a1, s))
        x, y, w, h = rest
    px, py = x + w / 2, y + h / 2  # le rectangle restant s'est réduit au pôle
    dx, dy = cx - px, cy - py
    rects = "".join(f'<rect x="{sx + dx:.1f}" y="{sy + dy:.1f}" width="{s:.1f}" height="{s:.1f}"/>'
                    for sx, sy, s in squares)
    d = f"M{arcs[0][0][0] + dx:.1f} {arcs[0][0][1] + dy:.1f}" + "".join(
        f"A{s:.1f} {s:.1f} 0 0 1 {b[0] + dx:.1f} {b[1] + dy:.1f}" for a, b, s in arcs)
    return (f'<g fill="none" stroke="{color}" stroke-width="{sw}">'
            f'<rect x="{dx:.1f}" y="{dy:.1f}" width="{width:.1f}" height="{width / PHI:.1f}" opacity="{rect_op}"/>'
            f'<g opacity="{rect_op}">{rects}</g>'
            f'<path d="{d}" stroke-width="{sw * 1.8:.1f}" stroke-linecap="round" opacity="{spiral_op}"/></g>')


def spin_arcs(cx: float, cy: float, r: float, color: str, n: int = 3, sw: float = 3) -> str:
    """Traînées de mouvement autour d'un objet qui tourne."""
    out = []
    for i in range(n):
        a0 = math.radians(i * 360 / n - 20)
        a1 = a0 + math.radians(70)
        rr = r * (1 + .06 * (i % 2))
        out.append(f'<path d="M{cx + rr * math.cos(a0):.1f} {cy + rr * math.sin(a0):.1f}'
                   f'A{rr:.1f} {rr:.1f} 0 0 1 {cx + rr * math.cos(a1):.1f} {cy + rr * math.sin(a1):.1f}" '
                   f'fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" opacity="{.75 - i * .15:.2f}"/>')
    return "".join(out)


# ---------------------------------------------------------------- la PSP

PSP_W, PSP_H = 176, 74
SCREEN_W, SCREEN_H = 98, 55


def psp_body_d(cx: float, cy: float, k: float = 1) -> str:
    """Le contour du corps : un rectangle aux bouts très arrondis."""
    w, h, r = PSP_W * k, PSP_H * k, 30 * k
    x, y = cx - w / 2, cy - h / 2
    return (f"M{x + r:.1f} {y:.1f}H{x + w - r:.1f}A{r:.1f} {r:.1f} 0 0 1 {x + w:.1f} {y + r:.1f}"
            f"V{y + h - r:.1f}A{r:.1f} {r:.1f} 0 0 1 {x + w - r:.1f} {y + h:.1f}H{x + r:.1f}"
            f"A{r:.1f} {r:.1f} 0 0 1 {x:.1f} {y + h - r:.1f}V{y + r:.1f}A{r:.1f} {r:.1f} 0 0 1 {x + r:.1f} {y:.1f}Z")


def screen_rect(cx: float, cy: float, k: float = 1) -> tuple[float, float, float, float]:
    return cx - SCREEN_W * k / 2, cy - SCREEN_H * k / 2 - 2 * k, SCREEN_W * k, SCREEN_H * k


def psp(cx: float, cy: float, k: float = 1, ink: str = "#fff", body: str = "#16161a", screen: str = "",
        hole: bool = False, line: float = 1.6) -> str:
    """Une console portable au format PSP, centrée en (cx, cy).

    screen : SVG dessiné dans l'écran (déjà découpé à sa forme).
    hole   : l'écran est un trou (evenodd) — pour zoomer à travers lui."""
    sx, sy, sw, sh = screen_rect(cx, cy, k)
    body_d = psp_body_d(cx, cy, k)
    hole_d = f"M{sx:.1f} {sy:.1f}h{sw:.1f}v{sh:.1f}h{-sw:.1f}Z"
    out = []
    if hole:
        out.append(f'<path d="{body_d}{hole_d}" fill-rule="evenodd" fill="{body}" stroke="{ink}" stroke-width="{line}"/>')
    else:
        out.append(f'<path d="{body_d}" fill="{body}" stroke="{ink}" stroke-width="{line}"/>')
    # reflet
    out.append(f'<path d="M{cx - PSP_W * k / 2 + 28 * k:.1f} {cy - PSP_H * k / 2 + 5 * k:.1f}H{cx + PSP_W * k / 2 - 28 * k:.1f}" '
               f'stroke="{ink}" stroke-width="{1.2 * k:.1f}" stroke-linecap="round" opacity=".35"/>')
    # écran
    if not hole:
        out.append(f'<rect x="{sx:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sh:.1f}" fill="#000"/>')
        if screen:
            out.append(screen)
    out.append(f'<rect x="{sx - 1.5 * k:.1f}" y="{sy - 1.5 * k:.1f}" width="{sw + 3 * k:.1f}" height="{sh + 3 * k:.1f}" '
               f'rx="{2 * k:.1f}" fill="none" stroke="{ink}" stroke-width="{1.2 * k:.1f}" opacity=".7"/>')
    # croix directionnelle
    dx, dy, a, t = cx - 64 * k, cy - 6 * k, 10 * k, 3.4 * k
    out.append(f'<path d="M{dx - a:.1f} {dy - t:.1f}h{a - t:.1f}v{-(a - t):.1f}h{2 * t:.1f}v{a - t:.1f}h{a - t:.1f}v{2 * t:.1f}'
               f'h{-(a - t):.1f}v{a - t:.1f}h{-2 * t:.1f}v{-(a - t):.1f}h{-(a - t):.1f}Z" fill="none" stroke="{ink}" '
               f'stroke-width="{1.2 * k:.1f}" stroke-linejoin="round"/>')
    out.append(f'<circle cx="{cx - 62 * k:.1f}" cy="{cy + 20 * k:.1f}" r="{4.5 * k:.1f}" fill="none" stroke="{ink}" stroke-width="{1.2 * k:.1f}"/>')
    # quatre boutons : triangle, rond, croix, carré
    bx, by, d, r = cx + 64 * k, cy - 6 * k, 10.5 * k, 4.6 * k
    s = r * .5
    syms = [
        f'<path d="M{bx:.1f} {by - d - s:.1f}L{bx + s:.1f} {by - d + s * .75:.1f}L{bx - s:.1f} {by - d + s * .75:.1f}Z"/>',
        f'<circle cx="{bx + d:.1f}" cy="{by:.1f}" r="{s * .85:.1f}"/>',
        f'<path d="M{bx - s * .8:.1f} {by + d - s * .8:.1f}L{bx + s * .8:.1f} {by + d + s * .8:.1f}M{bx + s * .8:.1f} {by + d - s * .8:.1f}L{bx - s * .8:.1f} {by + d + s * .8:.1f}"/>',
        f'<rect x="{bx - d - s * .75:.1f}" y="{by - s * .75:.1f}" width="{s * 1.5:.1f}" height="{s * 1.5:.1f}"/>',
    ]
    for ox, oy in ((0, -d), (d, 0), (0, d), (-d, 0)):
        out.append(f'<circle cx="{bx + ox:.1f}" cy="{by + oy:.1f}" r="{r:.1f}" fill="none" stroke="{ink}" stroke-width="{1.1 * k:.1f}"/>')
    out.append(f'<g fill="none" stroke="{ink}" stroke-width="{.9 * k:.1f}" stroke-linejoin="round">{"".join(syms)}</g>')
    # petits boutons sous l'écran
    for i in range(4):
        out.append(f'<rect x="{cx - 26 * k + i * 14 * k:.1f}" y="{cy + 29.5 * k:.1f}" width="{9 * k:.1f}" height="{2.6 * k:.1f}" '
                   f'rx="{1.3 * k:.1f}" fill="{ink}" opacity=".55"/>')
    return "".join(out)


# ---------------------------------------------------------------- la main

# Doigts : (base x, base y, longueur, largeur, inclinaison en degrés), dans le repère de la paume.
FINGERS = [(-36, -34, 92, 25, -9), (-11, -40, 104, 26, -2), (14, -38, 96, 25, 5), (37, -28, 74, 21, 13)]


def _capsule(x: float, y: float, s: float, bx: float, by: float, length: float, w: float, ang: float) -> str:
    """Un doigt : une gélule qui part de sa base (bx, by) vers le haut, inclinée de ang."""
    a = math.radians(ang)
    ux, uy = math.sin(a), -math.cos(a)        # vers le bout du doigt
    nx, ny = -uy, ux                           # perpendiculaire
    r = w / 2

    def P(px, py):
        return f"{x + px * s:.1f} {y + py * s:.1f}"
    b1 = (bx - nx * r, by - ny * r)
    b2 = (bx + nx * r, by + ny * r)
    t1 = (bx + ux * (length - r) - nx * r * .9, by + uy * (length - r) - ny * r * .9)
    t2 = (bx + ux * (length - r) + nx * r * .9, by + uy * (length - r) + ny * r * .9)
    return (f"M{P(*b1)}L{P(*t1)}A{r * .9 * s:.1f} {r * .9 * s:.1f} 0 0 1 {P(*t2)}L{P(*b2)}Z")


def hand_parts(x: float, y: float, s: float) -> dict[str, str]:
    """Une main ouverte, paume vers nous, doigts vers le haut.
    (x, y) est le creux de la paume : c'est là que l'objet tourne."""
    def P(px, py):
        return f"{x + px * s:.1f} {y + py * s:.1f}"

    parts = {
        "sleeve": f"M{P(-50, 128)}L{P(-58, 240)}H{x + 64 * s:.1f}L{P(56, 128)}Z",
        "wrist": f"M{P(-40, 50)}C{P(-40, 90)} {P(-38, 120)} {P(-40, 140)}H{x + 44 * s:.1f}C{P(42, 120)} {P(44, 90)} {P(46, 50)}Z",
    }
    for i, f in enumerate(FINGERS):
        parts[f"f{i}"] = _capsule(x, y, s, *f)
    parts["thumb"] = _capsule(x, y, s, -42, 30, 74, 28, -48)
    parts["palm"] = (f"M{P(-52, -34)}C{P(-58, 0)} {P(-56, 40)} {P(-42, 66)}C{P(-28, 86)} {P(28, 88)} {P(44, 66)}"
                     f"C{P(58, 44)} {P(60, 0)} {P(52, -34)}C{P(38, -50)} {P(-36, -50)} {P(-52, -34)}Z")
    parts["creases"] = (f"M{P(-46, -14)}C{P(-20, -24)} {P(16, -26)} {P(44, -18)}"       # ligne de cœur
                        f"M{P(-40, 4)}C{P(-24, 10)} {P(-14, 40)} {P(-12, 72)}"           # ligne de vie
                        + "".join(f"M{P(bx - w * .22, by - length * .58)}L{P(bx + w * .22, by - length * .58)}"
                                  for bx, by, length, w, _ in FINGERS))                  # plis des doigts
    return parts


ORDER = ["sleeve", "wrist", "f0", "f1", "f2", "f3", "thumb", "palm"]


def hand(x: float, y: float, s: float, fill: str, stroke: str, sw: float, shade: str = "",
         detail: str | None = None, sleeve: str | None = None) -> str:
    """La main complète. shade : un motif (url(#...)) posé en ombre sur le côté droit."""
    p = hand_parts(x, y, s)
    out = []
    for k in ORDER:
        f = sleeve if (k == "sleeve" and sleeve) else fill
        out.append(f'<path d="{p[k]}" fill="{f}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>')
        if shade and k != "sleeve":
            out.append(f'<path d="{p[k]}" fill="{shade}" opacity=".55" clip-path="url(#handshade)"/>')
    out.append(f'<path d="{p["creases"]}" fill="none" stroke="{detail or stroke}" stroke-width="{sw * .7:.1f}" '
               f'stroke-linecap="round" opacity=".6"/>')
    return "".join(out)


def hand_shade_clip(x: float, y: float, s: float) -> str:
    """Zone d'ombre : le bord droit de la main (la lumière vient de la gauche)."""
    return (f'<clipPath id="handshade"><polygon points="{poly([(x + 30 * s, y - 200 * s), (x + 140 * s, y - 200 * s), (x + 140 * s, y + 260 * s), (x + 16 * s, y + 260 * s), (x + 34 * s, y + 40 * s)])}"/></clipPath>')


def palm_shadow(x: float, y: float, s: float, r: float, color: str, op: float = .35) -> str:
    """L'ombre portée de l'objet qui tourne au creux de la main."""
    return f'<ellipse cx="{x + 4 * s:.1f}" cy="{y + 14 * s:.1f}" rx="{r * .9:.1f}" ry="{r * .55:.1f}" fill="{color}" opacity="{op}"/>'


# ---------------------------------------------------------------- la steel ball, en vectoriel léger

def ball_defs(pid: str = "sb") -> str:
    return (f'<radialGradient id="{pid}" cx=".36" cy=".32" r=".75"><stop offset="0" stop-color="#e6ffa8"/>'
            f'<stop offset=".38" stop-color="#8fcf3f"/><stop offset=".78" stop-color="#2f6b14"/>'
            f'<stop offset="1" stop-color="#0d2405"/></radialGradient>')


def ball_vector(cx: float, cy: float, r: float, pid: str = "sb") -> str:
    """Une boule verte à facettes, inspirée des steel balls (dessinée ici, pas l'image du manga).
    À faire tourner autour de (cx, cy)."""
    hexa = poly([(cx - r * .62 + r * .36 * math.cos(math.radians(a)), cy - r * .05 + r * .36 * math.sin(math.radians(a)))
                 for a in range(0, 360, 60)])
    k = r / 50
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#{pid})" stroke="#0b1a05" stroke-width="{max(1.5, 2.5 * k):.1f}"/>'
            f'<polygon points="{hexa}" fill="#c7f07a" fill-opacity=".35" stroke="#0b1a05" stroke-width="{max(1.2, 2 * k):.1f}"/>'
            f'<path d="M{cx - r * .1:.1f} {cy - r * .55:.1f}Q{cx + r * .45:.1f} {cy - r * .6:.1f} {cx + r * .75:.1f} {cy - r * .2:.1f}'
            f'M{cx - r * .1:.1f} {cy + r * .1:.1f}Q{cx + r * .35:.1f} {cy - r * .05:.1f} {cx + r * .8:.1f} {cy + r * .15:.1f}'
            f'M{cx - r * .05:.1f} {cy + r * .35:.1f}A{r * .3:.1f} {r * .3:.1f} 0 1 0 {cx + r * .5:.1f} {cy + r * .3:.1f}" '
            f'fill="none" stroke="#0b1a05" stroke-width="{max(1.2, 2.2 * k):.1f}" stroke-linecap="round"/>'
            f'<ellipse cx="{cx - r * .32:.1f}" cy="{cy - r * .42:.1f}" rx="{r * .22:.1f}" ry="{r * .12:.1f}" fill="#fff" opacity=".55" '
            f'transform="rotate(-30 {cx - r * .32:.1f} {cy - r * .42:.1f})"/>')
