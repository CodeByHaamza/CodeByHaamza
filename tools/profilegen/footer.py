"""Le bas de page commun aux deux styles : la carte de stats GitHub (note, séries, langages).

C'est la carte qui était déjà sur le profil, reprise telle quelle (Catppuccin Mocha,
police mono) : elle ne change pas quand on passe d'un style à l'autre.
"""
from __future__ import annotations

from .kit import W, esc, write

C = {
    "bg": "#11111b", "panel": "#181825", "line": "#313244", "edge": "#1e1e2e",
    "text": "#cdd6f4", "sub": "#a6adc8", "dim": "#6c7086", "faint": "#45475a",
    "blue": "#89b4fa", "green": "#a6e3a1", "mauve": "#cba6f7", "peach": "#fab387",
    "red": "#f38ba8", "yellow": "#f9e2af", "teal": "#94e2d5",
}
MONO = ("ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,"
        "'Liberation Mono','DejaVu Sans Mono',monospace")


def head(w: float, h: float, title: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}" '
            f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>')


def panel(w: float, h: float, r: float = 8) -> str:
    return f'<rect x=".5" y=".5" width="{w - 1:.1f}" height="{h - 1:.1f}" rx="{r}" fill="{C["bg"]}" stroke="{C["edge"]}"/>'


def txt(x: float, y: float, s: str, fill: str = None, size: float = 13, weight: str = "400",
        anchor: str = "start", opacity: str = None) -> str:
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    o = f' opacity="{opacity}"' if opacity else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{MONO}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill or C["text"]}" xml:space="preserve"{a}{o}>{esc(s)}</text>')


def reveal_css(sel: str, count: int, dur: float = .42, step: float = .13, dx: float = 6) -> str:
    """Apparition en cascade, jouée une seule fois. L'état ÉCRIT est l'état final (visible) :
    sans animation (rendu sans CSS, mouvement réduit), le contenu reste lisible."""
    out = [f"@keyframes rise{{from{{opacity:0;transform:translate({dx}px,4px)}}to{{opacity:1;transform:none}}}}",
           f"{sel}{{opacity:1;animation:rise {dur}s ease-out both}}"]
    for i in range(count):
        out.append(f"{sel}:nth-of-type({i + 1}){{animation-delay:{i * step:.2f}s}}")
    out.append(f"@media(prefers-reduced-motion:reduce){{{sel}{{animation:none}}}}")
    return "".join(out)


def wipe(x: float, y: float, w: float, h: float, delay: float, dur: float) -> str:
    """Un cache couleur de fond qui glisse vers la droite. Écrit déjà écarté : sans animation, il n'est nulle part."""
    return (f'<rect class="wipe" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{C["bg"]}" '
            f'style="animation-delay:{delay:.2f}s;animation-duration:{dur:.2f}s"/>')


WIPE_CSS = ("@keyframes wipe{from{transform:translateX(0)}to{transform:translateX(102%)}}"
            ".wipe{transform:translateX(102%);animation:wipe linear both}"
            "@media(prefers-reduced-motion:reduce){.wipe{animation:none}}")


def prompt(x: float, y: float, cmd: str, user: str, host: str, size: float = 12.5) -> str:
    ch = size * 0.6
    parts = [(f"{user}@{host}", C["blue"]), (":", C["text"]), ("~", C["yellow"]), ("$ ", C["green"]), (cmd, C["text"])]
    out, cx = [], x
    for s, col in parts:
        out.append(txt(cx, y, s, col, size))
        cx += len(s) * ch
    return "".join(out)


def stats_card(cfg: dict, st: dict) -> None:
    def num(n: int) -> str:
        return f"{n:,}".replace(",", " ")

    langs = [(n.lower(), v) for n, v in st["langs"]]
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

    s = [head(W, h, "My GitHub stats: rank, totals, streaks and languages"), panel(W, h),
         "<style>" + WIPE_CSS + "@keyframes pop{from{opacity:0;transform:scale(.82)}to{opacity:1;transform:none}}"
         ".pop{opacity:1;animation:pop .5s cubic-bezier(.2,1.4,.3,1) both}" + reveal_css(".rv", 12, step=.055) + "</style>"]
    i = cfg["identity"]
    s.append(prompt(pad, pad + 13, "git stats --self-hosted", i["handle"], i["host"]))
    s.append(txt(W - pad, pad + 13, "generated in-repo · no external service", C["faint"], 10, anchor="end"))

    def card(x: float, w: float, title: str) -> None:
        s.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{w:.1f}" height="{card_h:.1f}" rx="7" fill="{C["panel"]}" stroke="{C["edge"]}"/>')
        s.append(txt(x + 13, top + 19, title, C["faint"], 9.5))

    card(pad, lw, "OVERALL")
    cxr, cyr = pad + 52, top + 70
    s.append(f'<g class="pop"><circle cx="{cxr:.1f}" cy="{cyr:.1f}" r="31" fill="none" stroke="{C["line"]}" stroke-width="4"/>'
             f'<circle cx="{cxr:.1f}" cy="{cyr:.1f}" r="31" fill="none" stroke="{C["yellow"]}" stroke-width="4" '
             f'stroke-linecap="round" stroke-dasharray="{195 * 0.84:.0f} 400" transform="rotate(-90 {cxr:.1f} {cyr:.1f})"/>'
             + txt(cxr, cyr + 9, st["rank"], C["yellow"], 26, "700", "middle") + "</g>")
    s.append(txt(cxr, cyr + 31, "rank", C["faint"], 9.5, anchor="middle"))
    grid = [("commits", num(st["commits"])), ("stars", num(st["stars"])), ("PRs", num(st["prs"])),
            ("reviews", num(st["reviews"])), ("repos", num(st["repos"])), ("issues", num(st["issues"])),
            ("followers", num(st["followers"])), ("12-mo", num(st["total"]))]
    gx0, colw = pad + 104, (lw - 118) / 2
    for n, (k, v) in enumerate(grid):
        gx, gy = gx0 + (n % 2) * colw, top + 40 + (n // 2) * 21
        s.append('<g class="rv">' + txt(gx, gy, k, C["mauve"], 11.5) + txt(gx + colw - 16, gy, v, C["text"], 11.5, "700", anchor="end") + "</g>")

    card(rx, rw, "STREAK")
    s.append('<g class="pop" style="animation-delay:.12s">' + txt(rx + rw / 2, top + 72, str(st["cur"]), C["peach"], 42, "700", "middle") + "</g>")
    s.append(txt(rx + rw / 2, top + 90, "days, current", C["sub"], 10.5, anchor="middle"))
    s.append(f'<rect x="{rx + 20:.1f}" y="{top + 100:.1f}" width="{rw - 40:.1f}" height="1" fill="{C["edge"]}"/>')
    s.append('<g class="rv">' + txt(rx + 20, top + 115, "longest", C["mauve"], 11)
             + txt(rx + rw - 20, top + 115, f"{st['best']} days", C["text"], 11, "700", anchor="end") + "</g>")

    y = top + card_h + 10
    bar_x = pad + 13 * ch
    bar_w = W - bar_x - pad - 62
    for n, (name, pctv) in enumerate(langs):
        y += lh
        s.append(txt(pad, y, name, C["teal"], fs))
        s.append(f'<rect x="{bar_x:.1f}" y="{y - 8:.1f}" width="{bar_w:.1f}" height="7" rx="3.5" fill="{C["line"]}"/>')
        col = [C["blue"], C["yellow"], C["mauve"], C["green"], C["peach"], C["red"], C["teal"]][n % 7]
        s.append(f'<rect x="{bar_x:.1f}" y="{y - 8:.1f}" width="{max(bar_w * pctv / 100.0, 2):.1f}" height="7" rx="3.5" fill="{col}"/>')
        s.append(wipe(bar_x - .5, y - 9.5, bar_w + 2, 10, .3 + n * .1, .85))
        s.append(txt(W - pad, y, f"{pctv:.1f}%", C["sub"], 11.5, anchor="end"))
    s.append("</svg>")
    write("stats.svg", "".join(s))
