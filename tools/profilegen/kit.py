"""Briques communes : chemins, polices en tracés, petits helpers SVG, données GitHub.

Bibliothèque standard uniquement : c'est ce qui tourne chaque nuit dans le workflow.
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "gen"
ICONS = ROOT / "assets" / "icons"
DATA = ROOT / "data"
W = 860  # largeur de rendu d'un README GitHub

REPO_URL = "https://github.com/CodeByHaamza/CodeByHaamza"
PROFILE_URL = "https://github.com/CodeByHaamza"
MANGA_URL = f"{REPO_URL}/blob/main/MANGA.md"

# Heure de génération. PROFILE_NOW (ISO 8601) la fige, pour des rendus reproductibles.
NOW = (datetime.fromisoformat(os.environ["PROFILE_NOW"]) if os.environ.get("PROFILE_NOW")
       else datetime.now(timezone.utc))

PHI = (1 + 5 ** .5) / 2
REDUCE = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
SANS = "'Segoe UI','Helvetica Neue',Helvetica,Arial,sans-serif"
SERIF = "Georgia,'Times New Roman',serif"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ---------------------------------------------------------------- polices en tracés

_FONTS: dict[str, dict] = {}
MISSING: set[str] = set()


class Font:
    """Texte dessiné en tracés (data/fonts/<nom>.json, fait par tools/build_fonts.py).

    Chaque glyphe est défini une fois dans <defs> puis réutilisé avec <use> :
    un titre ne pèse que ses lettres distinctes. Une instance par SVG (le préfixe
    évite les collisions d'id entre polices d'un même fichier)."""

    def __init__(self, name: str, prefix: str):
        if name not in _FONTS:
            _FONTS[name] = json.loads((DATA / "fonts" / f"{name}.json").read_text(encoding="utf-8"))
        f = _FONTS[name]
        self.upm, self.g, self.p, self.name = f["unitsPerEm"], f["glyphs"], prefix, name
        self.used: set[str] = set()

    def _glyph(self, ch: str) -> tuple[str, dict]:
        if ch in self.g:
            return ch, self.g[ch]
        if ch.strip():
            MISSING.add(f"{self.name}:{ch}")
        return " ", self.g[" "]

    def width(self, s: str, size: float, track: float = 0) -> float:
        return sum(self._glyph(c)[1]["adv"] for c in s) * size / self.upm + track * max(len(s) - 1, 0)

    def fit(self, s: str, size: float, maxw: float, track: float = 0, floor: float = 8) -> float:
        """La plus grande taille <= size qui tient dans maxw."""
        while size > floor and self.width(s, size, track) > maxw:
            size -= .5
        return size

    def text(self, s: str, x: float, y: float, size: float, fill: str, stroke: str | None = None,
             sw: float = 0, anchor: str = "start", track: float = 0, skew: float = 0, attrs: str = "") -> str:
        k = size / self.upm
        w = self.width(s, size, track)
        x -= w / 2 if anchor == "middle" else w if anchor == "end" else 0
        uses, cx = [], 0.0
        for ch in s:
            key, gl = self._glyph(ch)
            if gl["d"]:
                self.used.add(key)
                uses.append(f'<use href="#{self.p}{ord(key):x}" x="{cx:.0f}"/>')
            cx += gl["adv"] + track / k
        st = (f' stroke="{stroke}" stroke-width="{sw / k:.0f}" stroke-linejoin="round" paint-order="stroke"'
              if stroke else "")
        sk = f" skewX({skew})" if skew else ""
        return (f'<g{attrs} transform="translate({x:.1f} {y:.1f}){sk} scale({k:.5f} {-k:.5f})" fill="{fill}"{st}>'
                + "".join(uses) + "</g>")

    def vtext(self, s: str, x: float, y: float, size: float, fill: str, gap: float = 1.0, **kw) -> str:
        """Écriture verticale (de haut en bas), un glyphe par ligne, centré sur x."""
        out = []
        for i, ch in enumerate(s):
            yy = y + i * size * gap
            t = self.text(ch, x, yy, size, fill, anchor="middle", **kw)
            if ch in "ー—…「」":  # ces signes se tournent en écriture verticale
                t = f'<g transform="rotate(90 {x:.1f} {yy - size * .36:.1f})">{t}</g>'
            out.append(t)
        return "".join(out)

    def defs(self) -> str:
        return "".join(f'<path id="{self.p}{ord(c):x}" d="{self.g[c]["d"]}"/>' for c in sorted(self.used))


# ---------------------------------------------------------------- helpers SVG

def svg_open(w: float, h: float, title: str, desc: str = "") -> str:
    d = f"<desc>{esc(desc)}</desc>" if desc else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" '
            f'height="{h:.0f}" role="img"><title>{esc(title)}</title>{d}')


def txt(x: float, y: float, s: str, fill: str, size: float = 13, weight: int = 600, anchor: str = "start",
        italic: bool = False, family: str = SANS, attrs: str = "") -> str:
    it = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}"{it}{attrs}>{esc(s)}</text>')


def wrap(text: str, max_chars: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > max_chars:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    return lines


def poly(pts) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def dots(pid: str, color: str, step: float = 6, r: float = 1.25, angle: float = 45) -> str:
    """Motif de trame (points)."""
    return (f'<pattern id="{pid}" width="{step}" height="{step}" patternUnits="userSpaceOnUse" '
            f'patternTransform="rotate({angle})"><circle cx="{step / 2}" cy="{step / 2}" r="{r}" fill="{color}"/></pattern>')


_ICONS: dict[str, str] = {}


def icon(slug: str | None, cx: float, cy: float, s: float, fill: str) -> str:
    """Un logo simple-icons (viewBox 24) de côté s, centré en (cx, cy)."""
    if not slug:
        return ""
    if slug == "__pygame":  # absent de simple-icons : triangle de lecture
        x, y = cx - s / 2, cy - s / 2
        return (f'<path fill="{fill}" d="M{x + s * .2:.1f} {y + s * .12:.1f}L{x + s * .9:.1f} {cy:.1f}'
                f'L{x + s * .2:.1f} {y + s * .88:.1f}Z"/>')
    if slug not in _ICONS:
        f = ICONS / f"{slug}.svg"
        _ICONS[slug] = " ".join(re.findall(r'<path[^>]*\sd="([^"]+)"', f.read_text(encoding="utf-8"))) if f.exists() else ""
    if not _ICONS[slug]:
        return ""
    return (f'<g fill="{fill}" transform="translate({cx - s / 2:.1f},{cy - s / 2:.1f}) scale({s / 24:.4f})">'
            f'<path d="{_ICONS[slug]}"/></g>')


def data_uri(path: Path, mime: str = "image/png") -> str:
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


WRITTEN: set[str] = set()  # les SVG écrits pendant cette génération


def write(name: str, svg: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(svg, encoding="utf-8")
    WRITTEN.add(name)


def save(name: str, parts: list[str]) -> None:
    write(name, "".join(parts) + "</svg>")


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.replace("œ", "oe").replace("Œ", "Oe"))
    return re.sub(r"[^a-z0-9]+", "-", s.encode("ascii", "ignore").decode().lower()).strip("-")


def num(n: int) -> str:
    return f"{n:,}"


# ---------------------------------------------------------------- données GitHub

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


def load_cfg() -> dict:
    return json.loads((DATA / "profile.json").read_text(encoding="utf-8"))


def load_gh() -> dict:
    f = DATA / "gh-raw.json"
    if not f.exists():
        raise SystemExit("data/gh-raw.json absent — lance avec --fetch")
    return json.loads(f.read_text(encoding="utf-8"))["data"]["user"]


def rank(commits: int, prs: int, issues: int, reviews: int, stars: int, followers: int) -> str:
    """Rang lettre, même esprit que github-readme-stats : une moyenne pondérée
    de percentiles, pas une note absolue."""
    def pct(v, med):
        return 1.0 / (1.0 + (med / max(v, 1)) ** 0.5)
    s = (pct(commits, 250) * .30 + pct(prs, 50) * .20 + pct(issues, 25) * .10
         + pct(reviews, 20) * .10 + pct(stars, 50) * .20 + pct(followers, 25) * .10)
    for lim, name in ((.92, "S"), (.82, "A+"), (.70, "A"), (.58, "B+"), (.45, "B"), (.30, "C+")):
        if s >= lim:
            return name
    return "C"


def streaks(weeks: list[dict]) -> tuple[int, int]:
    """(série en cours, plus longue série). Un dernier jour vide ne casse pas la série."""
    days = [d for wk in weeks for d in wk["contributionDays"]]
    best = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] > 0 else 0
        best = max(best, run)
    cur = 0
    for d in reversed(days):
        if d["contributionCount"] > 0:
            cur += 1
        elif cur == 0:
            continue
        else:
            break
    return cur, best


def languages(repos: list[dict], top: int = 6) -> list[tuple[str, float]]:
    tot: dict[str, int] = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            tot[e["node"]["name"]] = tot.get(e["node"]["name"], 0) + e["size"]
    allsum = sum(tot.values()) or 1
    ranked = sorted(tot.items(), key=lambda kv: -kv[1])
    out = [(n, v * 100.0 / allsum) for n, v in ranked[:top]]
    rest = sum(v for _, v in ranked[top:]) * 100.0 / allsum
    if rest > 0.4:
        out.append(("Other", rest))
    return out


def stats(cfg: dict, gh: dict) -> dict:
    """Toutes les grandeurs dont les deux styles ont besoin, calculées une fois."""
    cc = gh["contributionsCollection"]
    cal = cc["contributionCalendar"]
    repos = gh["repositories"]["nodes"]
    org_stars = sum(p.get("stars", 0) for p in cfg["projects"] if p.get("kind") == "org")
    cur, best = streaks(cal["weeks"])
    nlangs = len({e["node"]["name"] for r in repos for e in r["languages"]["edges"]})
    s = dict(commits=cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
             prs=cc["totalPullRequestContributions"], issues=cc["totalIssueContributions"],
             reviews=cc["totalPullRequestReviewContributions"],
             stars=sum(r["stargazerCount"] for r in repos) + org_stars,
             followers=gh["followers"]["totalCount"], total=cal["totalContributions"],
             repos=gh["repositories"]["totalCount"], cur=cur, best=best, nlangs=nlangs,
             langs=languages(repos), updated={r["name"]: r["updatedAt"][:10] for r in repos})
    s["rank"] = rank(s["commits"], s["prs"], s["issues"], s["reviews"], s["stars"], s["followers"])
    return s
