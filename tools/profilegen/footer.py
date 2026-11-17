"""Le bas de page commun, au look GitHub « vanilla » : il ne bascule pas avec les deux styles.

Couleurs et police de GitHub, en deux fichiers (clair et sombre) que le README sert avec
<picture> : c'est le thème GitHub du visiteur qui choisit. Animations jouées une fois au
chargement, depuis un état écrit final : compteurs qui défilent comme un odomètre, anneau de
la note qui se remplit, barres qui poussent, calendrier qui s'allume semaine par semaine.
"""
from __future__ import annotations

import math
from datetime import date

from .kit import REDUCE, W, esc, num, write

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
PALETTES = {
    "light": "--bg:#ffffff;--fg:#1f2328;--mu:#59636e;--bd:#d1d9e0;--ac:#0969da;--tr:#eff2f5;--fire:#fb8f44;"
             "--l0:#eff2f5;--l1:#aceebb;--l2:#4ac26b;--l3:#2da44e;--l4:#116329",
    "dark": "--bg:#0d1117;--fg:#f0f6fc;--mu:#9198a1;--bd:#3d444d;--ac:#4493f8;--tr:#21262d;--fire:#f0883e;"
            "--l0:#151b23;--l1:#033a16;--l2:#196c2e;--l3:#2ea043;--l4:#56d364",
}


def theme(mode: str) -> str:
    return ("svg{" + PALETTES[mode] + "}"
            ".bg{fill:var(--bg)}.bd{stroke:var(--bd)}.fg{fill:var(--fg)}.mu{fill:var(--mu)}.ac{fill:var(--ac)}"
            ".sac{stroke:var(--ac)}.str{stroke:var(--tr)}.ftr{fill:var(--tr)}.fire{fill:var(--fire)}.sfire{stroke:var(--fire)}"
            ".smu{stroke:var(--mu)}" + "".join(f".l{i}{{fill:var(--l{i})}}" for i in range(5)) + f"text{{font-family:{FONT}}}")

LANG_COLORS = {"JavaScript": "#f1e05a", "Python": "#3572A5", "HTML": "#e34c26", "PHP": "#4F5D95", "CSS": "#663399",
               "TypeScript": "#3178c6", "Java": "#b07219", "C": "#555555", "Shell": "#89e051", "Dockerfile": "#384d54",
               "Other": "#8b949e"}


def t(x, y, s, cls="fg", size=14, weight=400, anchor="start", extra="") -> str:
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" font-size="{size}" font-weight="{weight}"{a}{extra}>{esc(s)}</text>'


# ---------------------------------------------------------------- l'odomètre

class Odo:
    """Des nombres dont chaque chiffre défile jusqu'à sa valeur. L'état écrit est le chiffre final."""

    def __init__(self):
        self.n = 0
        self.defs: list[str] = []

    def number(self, s: str, x: float, y: float, size: float, cls: str = "fg", weight: int = 600,
               anchor: str = "end", delay: float = 0) -> str:
        dig, sep = size * .62, size * .32
        widths = [dig if c.isdigit() else sep for c in s]
        total = sum(widths)
        x0 = x - total if anchor == "end" else x - total / 2 if anchor == "middle" else x
        lh = size * 1.25
        self.n += 1
        cid = f"odo{self.n}"
        self.defs.append(f'<clipPath id="{cid}"><rect x="{x0 - 2:.1f}" y="{y - size:.1f}" width="{total + 4:.1f}" '
                         f'height="{size * 1.3:.1f}"/></clipPath>')
        out, cx, col = [f'<g clip-path="url(#{cid})">'], x0, 0
        for c, wdt in zip(s, widths):
            mid = cx + wdt / 2
            if c.isdigit():
                d = int(c)
                steps = 10 + d
                strip = "".join(t(mid, y + k * lh, str(k % 10), cls, size, weight, "middle") for k in range(steps + 1))
                out.append(f'<g class="roll" style="transform:translateY({-steps * lh:.1f}px);'
                           f'animation-delay:{delay + col * .07:.2f}s">{strip}</g>')
                col += 1
            else:
                out.append(t(mid, y, c, cls, size, weight, "middle"))
            cx += wdt
        out.append("</g>")
        return "".join(out)


CSS = ("@keyframes roll{from{transform:translateY(0)}}.roll{animation:roll 1.8s cubic-bezier(.15,.75,.2,1) both}"
       "@keyframes ring{from{stroke-dashoffset:var(--c)}}.ring{animation:ring 1.6s cubic-bezier(.3,.8,.3,1) both}"
       "@keyframes grow{from{transform:scaleX(0)}}.grow{animation:grow .7s cubic-bezier(.3,.8,.3,1) both}"
       "@keyframes pop{from{opacity:0;transform:translateY(5px)}}.pop{animation:pop .45s ease-out both}"
       "@keyframes flick{0%,100%{transform:scale(1)}50%{transform:scale(1.08,.94)}}.flick{animation:flick 1.2s ease-in-out infinite}")


# ---------------------------------------------------------------- petites icônes (dessinées ici)

def ic(kind: str, x: float, y: float) -> str:
    """Icône 16 px dont le coin haut-gauche est (x, y)."""
    g = f'<g transform="translate({x:.1f} {y:.1f})" fill="none" class="smu" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
    if kind == "star":
        pts = " ".join(f"{8 + (7 if i % 2 == 0 else 3.2) * math.cos(math.radians(-90 + i * 36)):.1f},"
                       f"{8.5 + (7 if i % 2 == 0 else 3.2) * math.sin(math.radians(-90 + i * 36)):.1f}" for i in range(10))
        return g + f'<polygon points="{pts}"/></g>'
    if kind == "commit":
        return g + '<circle cx="8" cy="8" r="3"/><path d="M1 8h4M11 8h4"/></g>'
    if kind == "pr":
        return g + '<circle cx="4" cy="3.5" r="1.8"/><circle cx="4" cy="12.5" r="1.8"/><circle cx="12" cy="12.5" r="1.8"/><path d="M4 5.3v5.4M12 10.7V6.5a2 2 0 0 0-2-2H7M8.5 2.8 7 4.5l1.5 1.7"/></g>'
    if kind == "issue":
        return g + '<circle cx="8" cy="8" r="6.5"/><circle cx="8" cy="8" r="1.2" class="mu"/></g>'
    if kind == "review":
        return g + '<path d="M1.5 8s2.4-4.5 6.5-4.5S14.5 8 14.5 8s-2.4 4.5-6.5 4.5S1.5 8 1.5 8z"/><circle cx="8" cy="8" r="2"/></g>'
    if kind == "pulse":
        return g + '<path d="M1 8h3l2-5 4 10 2-5h3"/></g>'
    return ""


def flame(cx: float, cy: float, s: float) -> str:
    return (f'<g class="flick" style="transform-origin:{cx:.0f}px {cy + 6 * s:.0f}px">'
            f'<path class="fire" d="M{cx:.1f} {cy - 9 * s:.1f}C{cx + 7 * s:.1f} {cy - 3 * s:.1f} {cx + 7 * s:.1f} {cy + 7 * s:.1f} '
            f'{cx:.1f} {cy + 7 * s:.1f}C{cx - 7 * s:.1f} {cy + 7 * s:.1f} {cx - 6 * s:.1f} {cy - 1 * s:.1f} {cx - 2 * s:.1f} {cy - 3 * s:.1f}'
            f'C{cx - 1 * s:.1f} {cy:.1f} {cx + 1 * s:.1f} {cy + 1 * s:.1f} {cx + 2 * s:.1f} {cy - 1 * s:.1f}'
            f'C{cx + 3 * s:.1f} {cy - 4 * s:.1f} {cx + 1 * s:.1f} {cy - 6 * s:.1f} {cx:.1f} {cy - 9 * s:.1f}Z"/></g>')


def fmt_day(d: str | None) -> str:
    if not d:
        return "—"
    x = date.fromisoformat(d)
    return f"{x.strftime('%b')} {x.day}, {x.year}"


def rng(a: str | None, b: str | None, today: str) -> str:
    if not a:
        return "—"
    return f"{fmt_day(a)} – " + ("Present" if b == today else fmt_day(b))


def card(x, y, w, h) -> str:
    return f'<rect x="{x + .5:.1f}" y="{y + .5:.1f}" width="{w - 1:.1f}" height="{h - 1:.1f}" rx="6" class="bg bd"/>'


# ---------------------------------------------------------------- 1. la carte de stats

def stats_card(cfg: dict, st: dict) -> None:
    odo = Odo()
    b = []
    today = st["weeks"][-1]["contributionDays"][-1]["date"]
    name = cfg["identity"]["handle"].capitalize()

    # -- stats + note
    y0, h1 = 0, 228
    b.append(card(0, y0, W, h1))
    b.append(t(25, y0 + 38, f"{name}'s GitHub Stats", "ac", 18, 600))
    b.append(t(W - 25, y0 + 37, "last 12 months · refreshed every night", "mu", 12, 400, "end"))
    rows = [("star", "Total Stars Earned", st["stars"]), ("commit", "Total Commits", st["commits"]),
            ("pr", "Total PRs", st["prs"]), ("issue", "Total Issues", st["issues"]),
            ("review", "Code Reviews", st["reviews"]), ("pulse", "Contributions", st["total"])]
    for i, (k, label, v) in enumerate(rows):
        y = y0 + 76 + i * 25
        b.append(f'<g class="pop" style="animation-delay:{i * .08:.2f}s">' + ic(k, 25, y - 13)
                 + t(50, y, label + ":", "fg", 14, 600) + odo.number(num(v), 420, y, 14, "fg", 700, "end", .2 + i * .08) + "</g>")
    rx, ry, rr = 640, y0 + 132, 52
    circ = 2 * math.pi * rr
    off = circ * (1 - st["score"])
    b.append(f'<circle cx="{rx}" cy="{ry}" r="{rr}" fill="none" class="str" stroke-width="7"/>')
    b.append(f'<circle cx="{rx}" cy="{ry}" r="{rr}" fill="none" class="sac ring" stroke-width="7" stroke-linecap="round" '
             f'stroke-dasharray="{circ:.1f}" stroke-dashoffset="{off:.1f}" style="--c:{circ:.1f}px" '
             f'transform="rotate(-90 {rx} {ry})"/>')
    b.append(t(rx, ry + 12, st["rank"], "fg", 34, 700, "middle"))
    b.append(t(rx, ry + rr + 30, "rank", "mu", 12, 400, "middle"))

    # -- séries (comme github-readme-streak-stats)
    y1, h2 = h1 + 16, 196
    b.append(card(0, y1, W, h2))
    cw = W / 3
    for i in (1, 2):
        b.append(f'<line x1="{cw * i:.1f}" y1="{y1 + 28}" x2="{cw * i:.1f}" y2="{y1 + h2 - 28}" class="bd"/>')
    rg = st["ranges"]
    cols = [(st["total"], "Total Contributions", rng(rg["first"], today, today), "fg"),
            (st["cur"], "Current Streak", rng(*rg["cur"], today), "fire"),
            (st["best"], "Longest Streak", rng(*rg["best"], today), "fg")]
    for i, (v, label, sub, cls) in enumerate(cols):
        cx = cw * i + cw / 2
        if i == 1:
            cy = y1 + 80
            b.append(f'<circle cx="{cx:.1f}" cy="{cy}" r="40" fill="none" class="sfire" stroke-width="5"/>')
            b.append(f'<rect x="{cx - 13:.1f}" y="{cy - 56}" width="26" height="26" class="bg"/>' + flame(cx, cy - 42, 1.15))
            b.append(odo.number(str(v), cx, cy + 10, 28, "fg", 700, "middle", .3))
            b.append(t(cx, y1 + 150, label, "fire", 14, 700, "middle"))
            b.append(t(cx, y1 + 172, sub, "mu", 12, 400, "middle"))
        else:
            b.append(odo.number(num(v), cx, y1 + 92, 28, "fg", 700, "middle", .2 + i * .1))
            b.append(t(cx, y1 + 124, label, "fg", 14, 400, "middle"))
            b.append(t(cx, y1 + 146, sub, "mu", 12, 400, "middle"))

    # -- langages
    y2 = y1 + h2 + 16
    langs = st["langs"]
    rows_l = math.ceil(len(langs) / 3)
    h3 = 104 + rows_l * 24
    b.append(card(0, y2, W, h3))
    b.append(t(25, y2 + 38, "Most Used Languages", "ac", 18, 600))
    bx, by, bw = 25, y2 + 58, W - 50
    b.append(f'<clipPath id="lbar"><rect x="{bx}" y="{by}" width="{bw}" height="10" rx="5"/></clipPath>')
    b.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="10" rx="5" class="ftr"/><g clip-path="url(#lbar)">')
    x = bx
    for i, (n, v) in enumerate(langs):
        wseg = bw * v / 100
        b.append(f'<rect class="grow" x="{x:.1f}" y="{by}" width="{wseg + .5:.1f}" height="10" fill="{LANG_COLORS.get(n, "#8b949e")}" '
                 f'style="transform-origin:{x:.1f}px 0;animation-delay:{.3 + i * .12:.2f}s"/>')
        x += wseg
    b.append("</g>")
    for i, (n, v) in enumerate(langs):
        lx = 25 + (i % 3) * (bw / 3)
        ly = by + 40 + (i // 3) * 24
        b.append(f'<g class="pop" style="animation-delay:{.5 + i * .08:.2f}s">'
                 f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{LANG_COLORS.get(n, "#8b949e")}"/>'
                 + f'<text x="{lx + 16:.1f}" y="{ly:.1f}" class="fg" font-size="13" font-weight="600">{esc(n)}'
                 f'<tspan class="mu" font-weight="400" dx="6">{v:.1f}%</tspan></text>' + "</g>")
    H = y2 + h3
    defs = "".join(odo.defs)
    title = (f"{name}'s GitHub stats: rank {st['rank']}, {num(st['stars'])} stars, {num(st['commits'])} commits, "
             f"{num(st['prs'])} PRs, {num(st['issues'])} issues, {num(st['reviews'])} reviews, {num(st['total'])} contributions; "
             f"current streak {st['cur']} days, longest {st['best']} days; languages: "
             + ", ".join(f"{n} {v:.0f}%" for n, v in langs))
    for mode in PALETTES:
        write(f"stats-{mode}.svg", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:.0f}" width="{W}" height="{H:.0f}" '
              f'role="img"><title>{esc(title)}</title><defs>{defs}</defs><style>{theme(mode)}{CSS}{REDUCE}</style>'
              + "".join(b) + "</svg>")


# ---------------------------------------------------------------- 2. le calendrier de contributions

def calendar(st: dict) -> None:
    weeks = st["weeks"]
    counts = sorted(d["contributionCount"] for wk in weeks for d in wk["contributionDays"] if d["contributionCount"])
    q = [counts[int(len(counts) * f)] for f in (.25, .5, .75)] if counts else [1, 2, 3]

    def level(c):
        return 0 if c == 0 else 1 if c <= q[0] else 2 if c <= q[1] else 3 if c <= q[2] else 4
    cell, gap = 12, 3
    step = cell + gap
    x0, y0 = 50, 62
    H = y0 + 7 * step + 50
    b = [card(0, 0, W, H), t(25, 36, f"{num(st['total'])} contributions in the last year", "fg", 16, 600)]
    for i, lbl in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        b.append(t(x0 - 8, y0 + i * step + 10, lbl, "mu", 11, 400, "end"))
    last_month = None
    for wi, wk in enumerate(weeks):
        x = x0 + wi * step
        first = wk["contributionDays"][0]["date"]
        m = first[5:7]
        if m != last_month and wi < len(weeks) - 2:
            b.append(t(x, y0 - 10, date.fromisoformat(first).strftime("%b"), "mu", 11))
            last_month = m
        b.append(f'<g class="pop" style="animation-delay:{.2 + wi * .022:.3f}s">')
        for d in wk["contributionDays"]:
            dow = (date.fromisoformat(d["date"]).weekday() + 1) % 7  # dimanche en haut, comme sur GitHub
            b.append(f'<rect x="{x}" y="{y0 + dow * step}" width="{cell}" height="{cell}" rx="2" class="l{level(d["contributionCount"])}"/>')
        b.append("</g>")
    ly = y0 + 7 * step + 28
    lx = W - 25 - 5 * step - 34
    b.append(t(lx - 8, ly + 10, "Less", "mu", 11, 400, "end"))
    for i in range(5):
        b.append(f'<rect x="{lx + i * step}" y="{ly}" width="{cell}" height="{cell}" rx="2" class="l{i}"/>')
    b.append(t(lx + 5 * step + 4, ly + 10, "More", "mu", 11))
    b.append(t(25, ly + 10, f"best day: {num(max(counts) if counts else 0)} contributions", "mu", 11))
    for mode in PALETTES:
        write(f"calendar-{mode}.svg", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
              f'role="img"><title>{esc(num(st["total"]))} contributions in the last year</title>'
              f"<style>{theme(mode)}{CSS}{REDUCE}</style>" + "".join(b) + "</svg>")
