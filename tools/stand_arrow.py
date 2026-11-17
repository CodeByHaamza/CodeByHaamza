#!/usr/bin/env python3
"""Lancé par .github/workflows/stand-arrow.yml quand un visiteur ouvre une issue « arrow… ».

Tire un Stand au hasard, l'ajoute à data/stand-users.json, met à jour le bloc du README et
écrit la réponse dans comment.md (le workflow la poste puis ferme l'issue).
Une flèche par visiteur et par jour (UTC). Du contenu de l'issue, seuls le numéro et le login
de l'auteur sont lus : le titre et le texte ne sont jamais interprétés.
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from profilegen import arrow  # noqa: E402
from profilegen.kit import ROOT  # noqa: E402


def main() -> None:
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    issue = event["issue"]
    user = issue["user"]["login"]
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", user):  # un login GitHub, rien d'autre
        raise SystemExit(f"login inattendu : {user!r}")
    today = datetime.now(timezone.utc).date().isoformat()
    stands = {s["id"]: s for s in arrow.load_stands()}
    log = arrow.load_log()

    already = next((r for r in log if r["user"].lower() == user.lower() and r["date"] == today), None)
    if already:
        s = stands[already["stand"]]
        body = (f"🏹 @{user}, the Arrow already chose you today: **{' → '.join(x['name'] for x in s['stages'])}**.\n\n"
                "One arrow per visitor per day. Come back tomorrow!")
    else:
        s = random.SystemRandom().choice(list(stands.values()))
        log.append({"user": user, "stand": s["id"], "date": today, "issue": issue["number"]})
        arrow.LOG.write_text(json.dumps(log, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        readme = ROOT / "README.md"
        text = readme.read_text(encoding="utf-8")
        text = re.sub(re.escape(arrow.START) + r".*?" + re.escape(arrow.END), lambda m: arrow.readme_block(log), text, flags=re.S)
        readme.write_text(text, encoding="utf-8")
        arrow.build_card(s["id"])  # la carte animée de ce Stand, faite au moment du tirage
        stages = s["stages"]
        chain = " → ".join(x["name"] for x in stages)
        lines = [f"🏹 **@{user}, the Stand Arrow pierced you!**", "",
                 f"Your Stand is **{chain}** (Part {s['part']}, first awakened by {s['user']}).", ""]
        lines += [f"> **{x['name']}**: {x['text']}" for x in stages]
        lines += ["", f"![{chain}]({arrow.card_url(s['id'])})", "",
                  f"You're now on the Stand users board: https://github.com/{os.environ.get('GITHUB_REPOSITORY_OWNER', 'CodeByHaamza')}",
                  "", "Come back tomorrow for another arrow."]
        body = "\n".join(lines)
    (ROOT / "comment.md").write_text(body + "\n", encoding="utf-8")
    print(body)


if __name__ == "__main__":
    main()
