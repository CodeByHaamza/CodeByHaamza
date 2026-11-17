"""Superpose le calque PSP et le calque manga d'un panneau, et les fait basculer sur la boucle commune.

Trois transitions, toutes avec la steel ball :
  hero : l'écran recule jusqu'à la PSP, qui fait sa rotation dorée et devient la steel ball ;
         la balle s'ouvre en iris sur le manga. Au retour, l'encre se referme sur la balle,
         la balle redevient la PSP et on plonge dans son écran.
  wipe : une steel ball roule d'un bord à l'autre et découvre l'autre style derrière elle.
  flip : le bouton se retourne (pour les petits liens).

L'état écrit (sans animation) est le style PSP seul : c'est ce que voient les visiteurs qui
coupent les animations.
"""
from __future__ import annotations

from . import art, xmb
from .kit import (REDUCE, SHOW_MANGA, SWITCH_IN, SWITCH_OUT, T, data_uri, keyframes, on_loop, poly, prefix_layer,
                  svg_open, write)
from .manga import BALL, INK, SPOT

EASE = "animation-timing-function:cubic-bezier(.65,0,.35,1)"


def _write(name: str, w: float, h: float, title: str, desc: str, psp: tuple, mng: tuple,
           defs: str, css: str, body: str) -> None:
    pd, pcss, _ = psp
    md, mcss, _ = mng
    write(name, svg_open(w, h, title, desc) + "<defs>" + pd + md + defs + "</defs>"
          + f"<style>{pcss}{mcss}{css}{REDUCE}</style>" + body + "</svg>")


def swap_css() -> str:
    """Quel calque est montré, hors effets : le PSP est écrit visible, le manga écrit caché."""
    return (keyframes("x-pv", [(0, "opacity:1"), (12.95, "opacity:1"), (12.96, "opacity:0"), (27.04, "opacity:0"),
                               (27.05, "opacity:1"), (T, "opacity:1")])
            + keyframes("x-mv", [(0, "opacity:0"), (12.95, "opacity:0"), (12.96, "opacity:1"), (27.04, "opacity:1"),
                                 (27.05, "opacity:0"), (T, "opacity:0")])
            + on_loop("x-psp", "x-pv", "opacity:1;") + on_loop("x-manga", "x-mv", "opacity:0;"))


# ---------------------------------------------------------------- l'en-tête : zoom, rotation dorée, steel ball

def hero(name: str, w: float, h: float, title: str, desc: str, psp: tuple, mng: tuple) -> None:
    psp, mng = prefix_layer(psp, "p-"), prefix_layer(mng, "m-")
    k = 1.6
    cx, cy = w / 2, h / 2
    sx, sy, sw, sh = art.screen_rect(cx, cy, k)
    scx, scy = sx + sw / 2, sy + sh / 2
    br = 60  # rayon de la steel ball
    defs = (f'<linearGradient id="x-xbg" x1="0" y1="0" x2=".35" y2="1"><stop offset="0" stop-color="{xmb.TOP}"/>'
            f'<stop offset="1" stop-color="{xmb.BOT}"/></linearGradient>'
            f'<clipPath id="x-ballclip"><circle cx="{scx:.1f}" cy="{scy:.1f}" r="{br}"/></clipPath>'
            f'<mask id="x-hole" maskUnits="userSpaceOnUse" x="0" y="0" width="{w}" height="{h}">'
            f'<rect width="{w}" height="{h}" fill="#fff"/>'
            f'<g class="x-geo"><rect x="{sx:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sh:.1f}" fill="#000"/></g>'
            f'<g class="x-iris"><circle cx="{scx:.1f}" cy="{scy:.1f}" r="{br * 10}" fill="#000"/></g></mask>')

    def tr(rot, sc):
        return f"transform:rotate({rot}deg) scale({sc})"
    css = (swap_css()
           # la PSP : on recule (7.4 → 1), rotation dorée en rapetissant, puis l'inverse au retour
           + keyframes("x-geo", [(0, tr(0, 7.4)), (12.0, tr(0, 7.4) + ";" + EASE), (12.7, tr(0, 1)), (13.2, tr(360, .35)),
                                 (13.21, tr(360, 0)), (26.79, tr(-360, 0)), (26.8, tr(-360, .35)), (27.3, tr(0, 1) + ";" + EASE),
                                 (T, tr(0, 7.4))])
           + on_loop("x-geo", "x-geo", f"transform-origin:{scx:.1f}px {scy:.1f}px;{tr(0, 7.4)};")
           # l'iris autour de la steel ball
           + keyframes("x-iris", [(0, "transform:scale(0)"), (13.2, "transform:scale(0);animation-timing-function:ease-in"),
                                  (SHOW_MANGA, "transform:scale(1)"), (SWITCH_OUT, "transform:scale(1);animation-timing-function:ease-out"),
                                  (26.8, "transform:scale(.1)"), (26.81, "transform:scale(0)"), (T, "transform:scale(0)")])
           + on_loop("x-iris", "x-iris", f"transform-origin:{scx:.1f}px {scy:.1f}px;transform:scale(0);")
           + keyframes("x-ball", [(0, "transform:scale(0)"), (12.7, "transform:scale(0)"), (13.2, "transform:scale(1)"),
                                  (13.6, "transform:scale(1)"), (SHOW_MANGA, "transform:scale(0)"), (26.4, "transform:scale(0)"),
                                  (26.8, "transform:scale(1)"), (27.0, "transform:scale(1)"), (27.3, "transform:scale(0)"),
                                  (T, "transform:scale(0)")])
           + on_loop("x-ball", "x-ball", f"transform-origin:{scx:.1f}px {scy:.1f}px;transform:scale(0);")
           + f"@keyframes x-spin{{to{{transform:rotate(360deg)}}}}"
           f".x-roll{{transform-origin:{scx:.1f}px {scy:.1f}px;animation:x-spin .618s linear infinite}}"
           f".x-gold{{transform-origin:{scx:.1f}px {scy:.1f}px;animation:x-spin 3.236s linear infinite reverse}}"
           # le calque de transition n'existe que pendant les deux bascules
           + keyframes("x-ov", [(0, "opacity:0"), (11.99, "opacity:0"), (SWITCH_IN, "opacity:1"), (SHOW_MANGA, "opacity:1"),
                                (14.01, "opacity:0"), (25.99, "opacity:0"), (SWITCH_OUT, "opacity:1"), (27.99, "opacity:1"),
                                (T, "opacity:0")])
           + on_loop("x-ov", "x-ov", "opacity:0;")
           + keyframes("x-bgx", [(0, "opacity:1"), (25.99, "opacity:1"), (SWITCH_OUT, "opacity:0"), (T, "opacity:0")])
           + on_loop("x-bgx", "x-bgx")
           + keyframes("x-bgi", [(0, "opacity:0"), (25.99, "opacity:0"), (SWITCH_OUT, "opacity:1"), (T, "opacity:1")])
           + on_loop("x-bgi", "x-bgi", "opacity:0;"))
    body = (f'<g class="x-psp">{psp[2]}</g><g class="x-manga">{mng[2]}</g>'
            f'<g class="x-ov">'
            f'<rect class="x-bgx" width="{w}" height="{h}" rx="16" fill="url(#x-xbg)" mask="url(#x-hole)"/>'
            f'<rect class="x-bgi" width="{w}" height="{h}" rx="14" fill="{INK}" mask="url(#x-hole)"/>'
            f'<g class="x-geo">{art.psp(cx, cy, k, "#fff", "#141418", hole=True)}</g>'
            f'<g class="x-ball"><g class="x-gold">{art.golden(scx, scy, 330, "#fff", 1.4, .25, .8)}</g>'
            f'<g class="x-roll"><image href="{data_uri(BALL)}" x="{scx - br:.1f}" y="{scy - br:.1f}" width="{2 * br}" '
            f'height="{2 * br}" clip-path="url(#x-ballclip)"/>{art.spin_arcs(scx, scy, br + 16, "#fff", 3, 3)}</g></g>'
            f'</g>')
    _write(name, w, h, title, desc, psp, mng, defs, css, body)


# ---------------------------------------------------------------- les panneaux : une steel ball qui roule

def wipe(name: str, w: float, h: float, title: str, desc: str, psp: tuple, mng: tuple) -> None:
    psp, mng = prefix_layer(psp, "p-"), prefix_layer(mng, "m-")
    off_l, off_r = -(w + 330), w + 330
    r = min(34, h * .3)
    reveal = poly([(-200, -10), (w + 200, -10), (w + 80, h + 10), (-320, h + 10)])
    defs = (art.ball_defs("x-sb")
            + f'<mask id="x-reveal" maskUnits="userSpaceOnUse" x="{-w - 800}" y="-20" width="{3 * w + 1600}" height="{h + 40}">'
            f'<g class="x-wipe"><polygon points="{reveal}" fill="#fff"/></g></mask>')

    def tx(v):
        return f"transform:translateX({v:.0f}px)"
    css = (keyframes("x-wipe", [(0, tx(off_l)), (12.3, tx(off_l) + ";" + EASE), (13.3, tx(0)), (26.3, tx(0) + ";" + EASE),
                                (27.3, tx(off_r)), (27.31, tx(off_l)), (T, tx(off_l))])
           + on_loop("x-wipe", "x-wipe", tx(off_l) + ";")
           + keyframes("x-in", [(0, "opacity:0"), (12.29, "opacity:0"), (12.3, "opacity:1"), (13.3, "opacity:1"), (13.31, "opacity:0"),
                                (T, "opacity:0")])
           + on_loop("x-in", "x-in", "opacity:0;")
           + keyframes("x-out", [(0, "opacity:0"), (26.29, "opacity:0"), (26.3, "opacity:1"), (27.3, "opacity:1"), (27.31, "opacity:0"),
                                 (T, "opacity:0")])
           + on_loop("x-out", "x-out", "opacity:0;")
           + "@keyframes x-spin{to{transform:rotate(360deg)}}")
    # la bande d'encre (vers le manga) et la bande de lumière (vers le PSP), qui suivent le bord
    ink = (f'<polygon points="{poly([(w + 150, -10), (w + 260, -10), (w + 140, h + 10), (w + 30, h + 10)])}" fill="{INK}"/>'
           f'<polygon points="{poly([(w + 260, -10), (w + 280, -10), (w + 160, h + 10), (w + 140, h + 10)])}" fill="{SPOT}"/>')
    light = (f'<polygon points="{poly([(-290, -10), (-170, -10), (-290, h + 10), (-410, h + 10)])}" fill="{xmb.GLOW}" opacity=".35"/>'
             f'<polygon points="{poly([(-230, -10), (-196, -10), (-316, h + 10), (-350, h + 10)])}" fill="#fff"/>')

    def ball(x):
        css_ = f"transform-origin:{x:.0f}px {h / 2:.0f}px;animation:x-spin .3s linear infinite"
        return f'<g style="{css_}">{art.ball_vector(x, h / 2, r, "x-sb")}</g>'
    body = (f'<g class="x-psp-under">{psp[2]}</g><g mask="url(#x-reveal)">{mng[2]}</g>'
            f'<g class="x-wipe"><g class="x-in">{ink}{ball(w + 140 + r * .4)}</g>'
            f'<g class="x-out">{light}{ball(-260)}</g></g>')
    _write(name, w, h, title, desc, psp, mng, defs, css, body)


# ---------------------------------------------------------------- les liens : le bouton se retourne

def flip(name: str, w: float, h: float, title: str, psp: tuple, mng: tuple) -> None:
    psp, mng = prefix_layer(psp, "p-"), prefix_layer(mng, "m-")
    o = f"transform-origin:{w / 2:.0f}px {h / 2:.0f}px;"
    css = (keyframes("x-fp", [(0, "transform:scaleY(1)"), (12.6, "transform:scaleY(1)"), (12.9, "transform:scaleY(0)"),
                              (26.9, "transform:scaleY(0)"), (27.2, "transform:scaleY(1)"), (T, "transform:scaleY(1)")])
           + on_loop("x-fp", "x-fp", o)
           + keyframes("x-fm", [(0, "transform:scaleY(0)"), (12.9, "transform:scaleY(0)"), (13.2, "transform:scaleY(1)"),
                                (26.6, "transform:scaleY(1)"), (26.9, "transform:scaleY(0)"), (T, "transform:scaleY(0)")])
           + on_loop("x-fm", "x-fm", o + "transform:scaleY(0);"))
    body = f'<g class="x-fp">{psp[2]}</g><g class="x-fm">{mng[2]}</g>'
    _write(name, w, h, title, "", psp, mng, "", css, body)
