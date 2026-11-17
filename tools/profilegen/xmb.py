"""Style PSP : le menu d'une console portable (barre à icônes, vagues lumineuses).

Chaque fonction renvoie un calque (defs, css, body) à la hauteur demandée ; dual.py le
superpose au calque manga du même panneau. Le fond change de couleur chaque mois.
"""
from __future__ import annotations

import math

from . import art
from .kit import (GRADE_AXES, GRADES, NOW, SWITCH_IN, UNIT, W, Font, icon, keyframes, num, on_loop, slug, wrap)

# un thème par mois : (haut du dégradé, bas, lueur)
MONTHS = {1: ("#9aa3ad", "#2e343b", "#ffffff"), 2: ("#c9a227", "#3a2c05", "#fff1b8"),
          3: ("#7fb03a", "#1d3009", "#eaffc9"), 4: ("#d77aa6", "#3f1428", "#ffe0ef"),
          5: ("#2f9a57", "#0b2e18", "#c9ffe0"), 6: ("#8a4fc7", "#21103a", "#ecd9ff"),
          7: ("#25a7a0", "#08302e", "#c9fffb"), 8: ("#2f6fd0", "#0a1e40", "#d6e6ff"),
          9: ("#5b48b5", "#160f35", "#e0dbff"), 10: ("#c9782a", "#3a1e06", "#ffe2c4"),
          11: ("#9a5a33", "#2a140a", "#ffe6d4"), 12: ("#c23b3b", "#3a0909", "#ffd6d6")}
TOP, BOT, GLOW = MONTHS[NOW.month]
WH = "#ffffff"
MONTH_NAME = NOW.strftime("%B").lower()


def mix(a: str, b: str, t: float) -> str:
    ca, cb = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


HAND = mix(TOP, BOT, .3)  # main opaque, teinte du mois


class Page:
    """Un calque du style PSP : fond du mois, polices, CSS."""

    def __init__(self, h: float, waves: bool = True, shade: float = 0, w: float = W, rx: float = 16):
        self.h, self.w = h, w
        self.R = Font("rounded-bold", "rb")
        self.M = Font("rounded", "rm")
        self.defs: list[str] = [
            f'<linearGradient id="bg" x1="0" y1="0" x2=".35" y2="1"><stop offset="0" stop-color="{TOP}"/>'
            f'<stop offset="1" stop-color="{BOT}"/></linearGradient>'
            f'<radialGradient id="lit" cx=".22" cy=".08" r=".9"><stop offset="0" stop-color="{GLOW}" stop-opacity=".22"/>'
            f'<stop offset="1" stop-color="{GLOW}" stop-opacity="0"/></radialGradient>'
            f'<clipPath id="card"><rect width="{w}" height="{h}" rx="{rx}"/></clipPath>'
            '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4" result="b"/>'
            '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>']
        self.css: list[str] = []
        self.b: list[str] = [f'<g clip-path="url(#card)"><rect width="{w}" height="{h}" fill="url(#bg)"/>'
                             f'<rect width="{w}" height="{h}" fill="url(#lit)"/>']
        if waves:
            self.b.append(self.waves(h))
        if shade:
            self.b.append(f'<rect width="{w}" height="{h}" fill="#000" opacity="{shade}"/>')

    def waves(self, h: float) -> str:
        """Trois rubans sinusoïdaux qui glissent ; la boucle est sans couture (on glisse d'une période)."""
        out = []
        for k, (amp, per, y0, thick, op, dur, ph) in enumerate([(26, 620, .56, 34, .10, 26, 0), (18, 480, .6, 18, .14, 19, 1.6),
                                                                (34, 760, .52, 60, .06, 34, 3.1)]):
            n = int((self.w + per) / 8) + 2
            top = [(i * 8, h * y0 + amp * math.sin(i * 8 / per * 2 * math.pi + ph)) for i in range(n)]
            bot = [(x, y + thick + 10 * math.sin(x / per * 4 * math.pi + ph)) for x, y in top]
            d = ("M" + " L".join(f"{x:.0f} {y:.1f}" for x, y in top) + " L"
                 + " L".join(f"{x:.0f} {y:.1f}" for x, y in reversed(bot)) + "Z")
            line = "M" + " L".join(f"{x:.0f} {y:.1f}" for x, y in top)
            self.css.append(f"@keyframes xw{k}{{to{{transform:translateX(-{per}px)}}}}.w{k}{{animation:xw{k} {dur}s linear infinite}}")
            out.append(f'<g class="w{k}"><path d="{d}" fill="{GLOW}" opacity="{op}"/>'
                       f'<path d="{line}" fill="none" stroke="{GLOW}" stroke-width="1.2" opacity="{op * 3:.2f}"/></g>')
        return "".join(out)

    def crumb(self, kind: str, title: str, sub: str, right: str = "", y: float = 45) -> None:
        """Le fil d'Ariane en haut d'un écran : icône, catégorie › sous-menu."""
        self.b.append(ico(kind, 44, y - 7, 28))
        self.b.append(self.R.text(title, 70, y, 21, WH))
        self.b.append(self.M.text(f"›  {sub}", 78 + self.R.width(title, 21), y, 15, WH, attrs=' opacity=".75"'))
        if right:
            self.b.append(self.M.text(right, W - 26, y, 13.5, WH, anchor="end", attrs=' opacity=".75"'))
        self.b.append(f'<rect x="24" y="{y + 15}" width="{W - 48}" height="1" fill="{WH}" opacity=".35"/>')

    def layer(self, extra_fonts: tuple = ()) -> tuple:
        css = ("@keyframes xrise{from{transform:translateY(12px);opacity:0}to{transform:none;opacity:1}}"
               ".rise{animation:xrise .5s ease-out both}"
               "@keyframes xbreathe{0%,100%{opacity:.10}50%{opacity:.2}}.breathe{animation:xbreathe 2.6s ease-in-out infinite}"
               + "".join(self.css))
        fonts = self.R.defs() + self.M.defs() + "".join(f.defs() for f in extra_fonts)
        return "".join(self.defs) + fonts, css, "".join(self.b) + "</g>"


# ---------------------------------------------------------------- icônes au trait

def ico(kind: str, cx: float, cy: float, s: float, op: float = 1, color: str = WH) -> str:
    st = (f'fill="none" stroke="{color}" stroke-width="{max(2.0, s * .07):.1f}" stroke-linecap="round" '
          f'stroke-linejoin="round" opacity="{op}"')
    h = s / 2
    if kind == "user":
        return (f'<g {st}><circle cx="{cx}" cy="{cy - h * .32:.1f}" r="{h * .36:.1f}"/>'
                f'<path d="M{cx - h * .72:.1f} {cy + h * .78:.1f}Q{cx - h * .7:.1f} {cy + h * .12:.1f} {cx} {cy + h * .12:.1f}'
                f'Q{cx + h * .7:.1f} {cy + h * .12:.1f} {cx + h * .72:.1f} {cy + h * .78:.1f}"/></g>')
    if kind == "gear":
        pts = " ".join(f"{cx + h * (.82 if (i // 2) % 2 == 0 else .62) * math.cos(i * math.pi / 16):.1f},"
                       f"{cy + h * (.82 if (i // 2) % 2 == 0 else .62) * math.sin(i * math.pi / 16):.1f}" for i in range(32))
        return f'<g {st}><polygon points="{pts}"/><circle cx="{cx}" cy="{cy}" r="{h * .26:.1f}"/></g>'
    if kind == "folder":
        return (f'<g {st}><path d="M{cx - h * .85:.1f} {cy - h * .5:.1f}h{h * .6:.1f}l{h * .14:.1f} {h * .16:.1f}h{h * 1.1:.1f}'
                f'v{h * 1.1:.1f}h{-h * 1.7:.1f}z"/><path d="M{cx - h * .85:.1f} {cy - h * .18:.1f}h{h * 1.7:.1f}"/></g>')
    if kind == "pad":
        return (f'<g {st}><rect x="{cx - h * .9:.1f}" y="{cy - h * .45:.1f}" width="{h * 1.8:.1f}" height="{h * .9:.1f}" rx="{h * .45:.1f}"/>'
                f'<path d="M{cx - h * .5:.1f} {cy}h{h * .34:.1f}M{cx - h * .33:.1f} {cy - h * .17:.1f}v{h * .34:.1f}"/>'
                f'<circle cx="{cx + h * .4:.1f}" cy="{cy - h * .1:.1f}" r="1.5"/><circle cx="{cx + h * .56:.1f}" cy="{cy + h * .1:.1f}" r="1.5"/></g>')
    if kind == "book":
        return (f'<g {st}><path d="M{cx} {cy - h * .5:.1f}Q{cx - h * .5:.1f} {cy - h * .78:.1f} {cx - h * .9:.1f} {cy - h * .55:.1f}'
                f'v{h * 1.2:.1f}Q{cx - h * .5:.1f} {cy + h * .45:.1f} {cx} {cy + h * .72:.1f}Q{cx + h * .5:.1f} {cy + h * .45:.1f} '
                f'{cx + h * .9:.1f} {cy + h * .65:.1f}v{-h * 1.2:.1f}Q{cx + h * .5:.1f} {cy - h * .78:.1f} {cx} {cy - h * .5:.1f}'
                f'v{h * 1.22:.1f}"/></g>')
    if kind == "globe":
        return (f'<g {st}><circle cx="{cx}" cy="{cy}" r="{h * .8:.1f}"/><ellipse cx="{cx}" cy="{cy}" rx="{h * .34:.1f}" ry="{h * .8:.1f}"/>'
                f'<path d="M{cx - h * .8:.1f} {cy}h{h * 1.6:.1f}"/></g>')
    if kind == "chip":
        return (f'<g {st}><rect x="{cx - h * .55:.1f}" y="{cy - h * .55:.1f}" width="{h * 1.1:.1f}" height="{h * 1.1:.1f}" rx="3"/>'
                + "".join(f'<path d="M{cx - h * .3 + i * h * .3:.1f} {cy - h * .55:.1f}v{-h * .25:.1f}M{cx - h * .3 + i * h * .3:.1f} '
                          f'{cy + h * .55:.1f}v{h * .25:.1f}"/>' for i in range(3)) + "</g>")
    if kind == "server":
        return (f'<g {st}>' + "".join(f'<rect x="{cx - h * .8:.1f}" y="{cy - h * .7 + i * h * .5:.1f}" width="{h * 1.6:.1f}" '
                                       f'height="{h * .4:.1f}" rx="3"/>' for i in range(3)) + "</g>")
    if kind == "lock":
        return (f'<g {st}><rect x="{cx - h * .6:.1f}" y="{cy - h * .1:.1f}" width="{h * 1.2:.1f}" height="{h * .9:.1f}" rx="3"/>'
                f'<path d="M{cx - h * .35:.1f} {cy - h * .1:.1f}v{-h * .3:.1f}a{h * .35:.1f} {h * .35:.1f} 0 0 1 {h * .7:.1f} 0v{h * .3:.1f}"/></g>')
    if kind == "trophy":
        return (f'<g {st}><path d="M{cx - h * .5:.1f} {cy - h * .7:.1f}h{h:.1f}v{h * .55:.1f}a{h * .5:.1f} {h * .5:.1f} 0 0 1 {-h:.1f} 0z"/>'
                f'<path d="M{cx - h * .5:.1f} {cy - h * .55:.1f}h{-h * .3:.1f}a{h * .3:.1f} {h * .3:.1f} 0 0 0 {h * .32:.1f} {h * .45:.1f}'
                f'M{cx + h * .5:.1f} {cy - h * .55:.1f}h{h * .3:.1f}a{h * .3:.1f} {h * .3:.1f} 0 0 1 {-h * .32:.1f} {h * .45:.1f}'
                f'M{cx} {cy + h * .35:.1f}v{h * .3:.1f}M{cx - h * .35:.1f} {cy + h * .72:.1f}h{h * .7:.1f}"/></g>')
    if kind == "dot":
        return f'<circle cx="{cx}" cy="{cy}" r="{s * .12:.1f}" fill="{color}" opacity="{op}"/>'
    return ""


def battery(x: float, y: float) -> str:
    return (f'<rect x="{x}" y="{y}" width="30" height="14" rx="3" fill="none" stroke="{WH}" stroke-width="1.6"/>'
            f'<rect x="{x + 30}" y="{y + 4}" width="3" height="6" rx="1" fill="{WH}"/>'
            + "".join(f'<rect x="{x + 3 + i * 8.5}" y="{y + 3}" width="7" height="8" rx="1" fill="{WH}"/>' for i in range(3)))


# ---------------------------------------------------------------- 1. le menu d'accueil

def hero(cfg: dict, H: float) -> tuple:
    items = cfg["menu"]
    p = Page(H)
    R, M = p.R, p.M
    p.b.append(M.text(f"{NOW.day:02d}/{NOW.month:02d}  {NOW.hour}:{NOW.minute:02d}", W - 76, 38, 17, WH, anchor="end"))
    p.b.append(battery(W - 62, 25))
    cats = [("gear", "stack"), ("user", "Hamza"), ("folder", "projects"), ("chip", "setup"),
            ("pad", "games"), ("book", "manga"), ("globe", "links")]
    sel, xs, yr = 1, 214, 104
    for i, (k, label) in enumerate(cats):
        x = xs + (i - sel) * 104 + (24 if i > sel else 0)
        if i == sel:
            p.b.append(f'<g filter="url(#glow)">{ico(k, x, yr, 64)}</g>')
            p.b.append(R.text(label, x, yr + 58, 22, WH, anchor="middle"))
        else:
            p.b.append(ico(k, x, yr, 42, .72))
    # la sélection descend d'un élément toutes les 3 s (sans animation : le premier reste sélectionné)
    n = len(items)
    step = min(60, (H - 250) / n)
    y0 = 214
    frames = "".join(f"{i * 100 / n + .01:.2f}%,{(i + 1) * 100 / n - 3:.2f}%{{transform:translateY({i * step:.0f}px)}}"
                     for i in range(n))
    p.css.append(f"@keyframes xsel{{{frames}100%{{transform:none}}}}.sel{{animation:xsel {n * 3}s cubic-bezier(.5,0,.3,1) infinite 1.4s}}")
    p.b.append(f'<g class="sel"><rect x="{xs - 40}" y="{y0 - 28}" width="560" height="48" rx="10" fill="{WH}" opacity=".14" class="breathe"/>'
               f'<g filter="url(#glow)">{ico("dot", xs - 16, y0 - 6, 44)}</g></g>')
    for j, (t, sub) in enumerate(items):
        y = y0 + j * step
        p.b.append(f'<g class="rise" style="animation-delay:{.3 + j * .08:.2f}s">' + ico("dot", xs - 16, y - 6, 30, .55)
                   + R.text(t, xs + 6, y - 1, 18, WH) + M.text(sub, xs + 6, y + 16, 12.5, WH, attrs=' opacity=".72"') + "</g>")
    p.b.append(M.text(f"theme: {MONTH_NAME} · the colour changes every month", W - 24, H - 16, 11, WH,
                      anchor="end", attrs=' opacity=".55"'))
    return p.layer()


# ---------------------------------------------------------------- 2. un lien

def link_size(l: dict) -> tuple[float, float]:
    return Font("rounded-bold", "rb").width(l["label"], 15) + (64 if l.get("icon") else 40), 40


def link(l: dict, w: float, h: float) -> tuple:
    p = Page(h, waves=False, w=w, rx=h / 2)
    lw, lh = link_size(l)
    x0, y0 = (w - lw) / 2, (h - lh) / 2
    p.b.append(f'<rect x="{x0 + 1:.1f}" y="{y0 + 1:.1f}" width="{lw - 2:.0f}" height="{lh - 2}" rx="{(lh - 2) / 2}" fill="none" '
               f'stroke="{WH}" stroke-opacity=".55"/>'
               f'<rect x="{x0 + 4:.1f}" y="{y0 + 3:.1f}" width="{lw - 8:.0f}" height="{lh / 2 - 4:.0f}" rx="{lh / 4}" fill="{WH}" opacity=".13"/>')
    x = x0 + 20
    if l.get("icon"):
        p.b.append(icon(l["icon"], x + 10, h / 2, 18, WH))
        x += 28
    p.b.append(p.R.text(l["label"], x, h / 2 + 5.5, 15, WH))
    return p.layer()


# ---------------------------------------------------------------- 3. la main qui fait tourner la PSP

def portal(cfg: dict, H: float) -> tuple:
    p = Page(H)
    D = Font("dela", "dg")
    R, M = p.R, p.M
    cx, cy, k, hs = 232, 186, .74, .95  # (cx, cy) : centre de rotation, au creux de la paume
    sx, sy, sw, sh = art.screen_rect(cx, cy, k)
    p.defs.append(f'<clipPath id="scr"><rect x="{sx:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sh:.1f}"/></clipPath>')
    p.css.append(f".gold{{transform-origin:{cx}px {cy}px;animation:xspin 16.18s linear infinite reverse}}"
                 f".spin{{transform-origin:{cx}px {cy}px;animation:xspin 1.618s linear infinite}}"
                 "@keyframes xspin{to{transform:rotate(360deg)}}")
    p.b.append(f'<g class="gold">{art.golden(cx, cy, 440, GLOW, 1.2, .22, .55)}</g>')
    p.b.append(f'<g filter="url(#glow)">{art.hand(cx, cy + 4 * hs, hs, HAND, WH, 2.4)}</g>')
    p.b.append(art.palm_shadow(cx, cy + 4 * hs, hs, 66, "#000", .3))
    # l'écran de la PSP montre déjà la planche manga : on sait ce qui arrive
    mini = [f'<g clip-path="url(#scr)"><rect x="{sx:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sh:.1f}" fill="#f7f4ec"/>']
    for i in range(28):
        a = i * math.pi * 2 / 28
        c, s = math.cos, math.sin
        mini.append(f'<path d="M{cx + 60 * c(a):.1f} {sy + sh / 2 + 60 * s(a):.1f}L{cx + 16 * c(a + .03):.1f} '
                    f'{sy + sh / 2 + 11 * s(a + .03):.1f}L{cx + 16 * c(a - .03):.1f} {sy + sh / 2 + 11 * s(a - .03):.1f}Z" fill="#111"/>')
    mini.append(D.text("HAMZA", cx, sy + sh / 2 + 5, 15, "#111", "#fff", 2.5, anchor="middle", skew=-10))
    mini.append(D.text("ゴゴ", cx + 26, sy + 12, 8, "#8a3cff", "#111", .8, anchor="middle"))
    mini.append("</g>")
    p.b.append(f'<g class="spin">{art.spin_arcs(cx, cy, 84, WH, 3, 3)}' + art.psp(cx, cy, k, WH, "#141418", "".join(mini)) + "</g>")
    x0 = 470
    p.b.append(f'<circle cx="{x0 + 20}" cy="70" r="20" fill="none" stroke="{WH}" stroke-width="2.4" filter="url(#glow)"/>'
               f'<path d="M{x0 + 20} 59L{x0 + 30} 76H{x0 + 10}Z" fill="none" stroke="{WH}" stroke-width="2.4" stroke-linejoin="round"/>')
    p.b.append(M.text("auto switch", x0 + 52, 76, 16, WH, attrs=' opacity=".85"'))
    p.b.append(R.text("Golden Rotation", x0, 136, 32, WH))
    p.b.append(M.text("φ = 1.6180339887…  one turn every 1.618 s", x0, 164, 14, WH, attrs=' opacity=".8"'))
    for i, line in enumerate(["Every 12 seconds this whole page", "turns into a manga chapter, and back."]):
        p.b.append(M.text(line, x0, 206 + i * 22, 16, WH))
    # compte à rebours jusqu'à la bascule
    y = 286
    p.b.append(M.text("next: manga chapter", x0, y - 12, 13, WH, attrs=' opacity=".75"'))
    p.b.append(f'<rect x="{x0}" y="{y}" width="330" height="6" rx="3" fill="#000" opacity=".35"/>')
    p.css.append(keyframes("xcd", [(0, "transform:scaleX(0)"), (SWITCH_IN, "transform:scaleX(1)"), (28, "transform:scaleX(1)")])
                 + on_loop("cd", "xcd", f"transform-origin:{x0}px {y}px;"))
    p.b.append(f'<rect class="cd" x="{x0}" y="{y}" width="330" height="6" rx="3" fill="{WH}"/>')
    return p.layer(extra_fonts=(D,))


# ---------------------------------------------------------------- 4. informations système (le setup)

def system_height(cfg: dict) -> float:
    pc, srv = cfg["machines"][0], cfg["machines"][1]
    return 120 + max(len(pc["specs"]), len(srv["specs"]) + 5) * 27 + 20


def system(cfg: dict, H: float) -> tuple:
    pc, srv = cfg["machines"][0], cfg["machines"][1]
    p = Page(H, shade=.18)
    R, M = p.R, p.M
    p.crumb("gear", "Settings", "System Information", "2 machines")

    def column(x, w, kind, m, y0):
        p.b.append(ico(kind, x + 14, y0 - 6, 24))
        p.b.append(R.text(f"{m['user']}@{m['host']}", x + 36, y0, 16, WH))
        y = y0 + 34
        for i, (k, v) in enumerate(m["specs"]):
            p.b.append(f'<g class="rise" style="animation-delay:{i * .05:.2f}s">'
                       + (M.text(k, x, y, 13.5, WH, attrs=' opacity=".65"') if k else "")
                       + R.text(v, x + w, y, 13.5, WH, anchor="end") + "</g>")
            p.b.append(f'<rect x="{x}" y="{y + 9}" width="{w}" height="1" fill="{WH}" opacity=".12"/>')
            y += 27
        return y

    column(40, 380, "chip", pc, 98)
    y = column(460, 360, "server", srv, 98) + 18
    p.b.append(ico("lock", 474, y - 5, 22))
    p.b.append(R.text("in the lab, private for now", 496, y, 14, WH))
    for i, line in enumerate(wrap(cfg["private_note"], 44)):
        p.b.append(M.text(line, 460, y + 26 + i * 20, 13, WH, attrs=' opacity=".75"'))
    p.b.append(M.text(cfg["gym"], 460, y + 72, 12, WH, attrs=' opacity=".6"'))
    return p.layer()


# ---------------------------------------------------------------- 5. le stack

def stack(cfg: dict, H: float) -> tuple:
    cats = cfg["stack"]
    p = Page(H, shade=.18)
    R, M = p.R, p.M
    p.crumb("gear", "Settings", "Stack", f"{sum(len(c['items']) for c in cats)} tools")
    step = (H - 110) / len(cats)
    for r, c in enumerate(cats):
        y = 100 + step / 2 + r * step
        p.b.append(f'<g class="rise" style="animation-delay:{r * .06:.2f}s">')
        p.b.append(R.text(c["cat"], 40, y, 14.5, WH))
        x = 190
        for label, slug_ in c["items"]:
            ic = icon(slug_, x + 9, y - 5, 17, WH) if slug_ else ""
            tw = M.width(label, 13.5)
            p.b.append(f'<rect x="{x - 8}" y="{y - 21}" width="{tw + (34 if ic else 16):.0f}" height="30" rx="15" fill="{WH}" opacity=".10"/>')
            if ic:
                p.b.append(ic + M.text(label, x + 24, y, 13.5, WH))
                x += tw + 44
            else:
                p.b.append(M.text(label, x, y, 13.5, WH, attrs=' opacity=".8"'))
                x += tw + 26
        p.b.append("</g>")
    return p.layer()


# ---------------------------------------------------------------- 6. trophées (les six notes de A à E)

MEDAL = {4: ("#e8f1ff", "platinum"), 3: ("#f2c94c", "gold"), 2: ("#c7cdd3", "silver"), 1: ("#cf8b52", "bronze"), 0: (None, "")}


def trophies(cfg: dict, st: dict, H: float) -> tuple:
    p = Page(H, shade=.18)
    R, M = p.R, p.M
    p.crumb("pad", "Game", "Trophies", "last 12 months · A is best")
    n = len(GRADE_AXES)
    step = (H - 92) / n
    for i, ((en, _jp, key, th), g) in enumerate(zip(GRADE_AXES, st["grades"])):
        y = 92 + i * step + step / 2
        col, metal = MEDAL[g]
        p.b.append(f'<g class="rise" style="animation-delay:{i * .07:.2f}s">')
        if col:
            p.b.append(f'<circle cx="62" cy="{y - 4:.1f}" r="19" fill="{col}" opacity=".22"/>' + ico("trophy", 62, y - 4, 26, 1, col))
        else:
            p.b.append(ico("trophy", 62, y - 4, 26, .35))
        p.b.append(R.text(en.capitalize(), 98, y - 6, 16, WH))
        p.b.append(M.text(f"{num(st[key])} {UNIT[key]}" + (f" · {metal} trophy" if metal else ""), 98, y + 13, 12.5, WH,
                          attrs=' opacity=".72"'))
        # barre vers la note suivante
        lo = th[g - 1] if g > 0 else 0
        hi = th[g] if g < 4 else None
        frac = 1 if hi is None else max(0.04, min(1, (st[key] - lo) / max(1, hi - lo)))
        p.b.append(f'<rect x="470" y="{y - 8:.1f}" width="260" height="6" rx="3" fill="#000" opacity=".35"/>'
                   f'<rect x="470" y="{y - 8:.1f}" width="{260 * frac:.1f}" height="6" rx="3" fill="{col or WH}"/>')
        nxt = "max grade" if hi is None else f"{GRADES[g + 1]} at {num(hi)}"
        p.b.append(M.text(nxt, 470, y + 13, 11, WH, attrs=' opacity=".6"'))
        p.b.append(f'<circle cx="{W - 60}" cy="{y - 5:.1f}" r="18" fill="none" stroke="{WH}" stroke-width="2" opacity=".85"/>'
                   + R.text(GRADES[g], W - 60, y + 2, 20, WH, anchor="middle"))
        p.b.append("</g>")
        if i < n - 1:
            p.b.append(f'<rect x="40" y="{y + step / 2 - 1:.1f}" width="{W - 80}" height="1" fill="{WH}" opacity=".1"/>')
    return p.layer()


# ---------------------------------------------------------------- 7. projets (données sauvegardées)

TECH = {"Grimoire du Cœur": "github", "Persona_GRUB_Themes": "python", "personadle": "php",
        "kagami": "mediapipe", "jojo-arena": "python", "p2is-relecture": "javascript",
        "ViscoCrowd": "numpy", "five_nights_at_fabron": "openjdk"}
TILE = ["#ff4d6d", "#4dabff", "#ffb84d", "#7c5cff", "#2fd3a7", "#ff7a3d", "#9aa3ad", "#c86bff"]


def monogram(name: str) -> str:
    """Deux lettres pour la vignette : les initiales des mots en majuscule, sinon des mots, sinon le début."""
    words = name.replace("_", " ").replace("-", " ").split()
    caps = [w[0] for w in words if w[0].isupper()]
    if len(caps) >= 2:
        return "".join(caps[:2])
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return name[:2].upper()


def projects_head(cfg: dict, H: float) -> tuple:
    p = Page(H, waves=False, shade=.18)
    p.crumb("folder", "Projects", "Saved Data Utility", f"{len(cfg['projects']) + len(cfg['uni'])} items · tap one to open it",
            y=H / 2 + 2)
    return p.layer()


def project_row(cfg: dict, st: dict, i: int, pr: dict, H: float) -> tuple:
    team = pr in cfg["uni"]
    q = Page(H, waves=False, shade=.22)
    R, M = q.R, q.M
    c = TILE[i % len(TILE)]
    q.defs.append(f'<linearGradient id="t" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c}"/>'
                  f'<stop offset="1" stop-color="{BOT}"/></linearGradient>')
    th = H - 20
    x, y, w = 24, 10, th * 1.8
    q.b.append(f'<rect x="{x}" y="{y}" width="{w:.0f}" height="{th}" rx="7" fill="url(#t)"/>'
               f'<rect x="{x}" y="{y}" width="{w:.0f}" height="{th * .45:.0f}" rx="7" fill="#fff" opacity=".13"/>'
               + R.text(monogram(pr["name"]), x + 12, y + th - 11, 24, WH) + icon(TECH.get(pr["name"]), x + w - 18, y + 18, 18, WH)
               + f'<rect x="{x}" y="{y}" width="{w:.0f}" height="{th}" rx="7" fill="none" stroke="#fff" stroke-opacity=".5"/>')
    tx = x + w + 20
    cy = H / 2
    q.b.append(R.text(pr["name"], tx, cy - 9, 17, WH))
    q.b.append(M.text(pr["desc"], tx, cy + 9, 13, WH, attrs=' opacity=".9"'))
    q.b.append(M.text(pr["meta"], tx, cy + 25, 10.5, WH, attrs=' opacity=".6"'))
    date = st["updated"].get(pr["name"])
    right = ("school team-up" if team else "organisation") if not date else "updated " + date.replace("-", "/")
    if pr.get("stars"):
        q.b.append(R.text(f"★ {pr['stars']}", W - 28, cy - 9, 17, WH, anchor="end"))
    q.b.append(M.text(right, W - 28, cy + 25, 10.5, WH, anchor="end", attrs=' opacity=".6"'))
    return q.layer()


# ---------------------------------------------------------------- 8. en-tête des jeux

def games_head(cfg: dict, H: float) -> tuple:
    p = Page(H, waves=False, shade=.18)
    p.crumb("pad", "Game", "Favourites", f"{len(cfg['games'])} titles · Steam", y=H / 2 + 2)
    return p.layer()
