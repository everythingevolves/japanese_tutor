from collections import defaultdict
from datetime import datetime, timedelta, timezone

from . import material


def utcnow():
    return datetime.now(timezone.utc)


def observe(db, args):
    audio = args["presented"] == "audio"
    transcript = args.get("transcript_revealed", False)
    if not audio and (transcript or args.get("replays", 0)):
        raise ValueError("Audio delivery is required for replays or transcript reveal")
    for item in args.get("observations", []):
        material.get(db, item["material"])
        skill, outcome = item["skill"], item["outcome"]
        if skill == "listening_recognition" and not audio:
            raise ValueError("Listening evidence requires audio delivery")
        if skill == "written_recognition" and audio and not transcript:
            raise ValueError("Reading evidence requires visible text")
        if outcome == "independent" and (args.get("hint") or
                (skill == "listening_recognition" and (transcript or args.get("replays")))):
            raise ValueError("Record assisted performance when support was used")
        if skill in ("active_grammar", "independent_recall") and outcome != "missed" and not args.get("japanese_production"):
            raise ValueError("Production evidence requires a Japanese response")
        db.execute("INSERT INTO observation(turn_id,material,skill,outcome) VALUES (?,?,?,?)",
                   (args["turn_id"], item["material"], skill, outcome))


def due(db, scene, now=None):
    now = now or utcnow()
    rows = db.execute("""SELECT o.material, o.skill, o.outcome, t.occurred FROM observation o
        JOIN turn t ON t.id=o.turn_id ORDER BY t.revision""")
    streak = defaultdict(int)
    targets = {}
    for row in rows:
        key = row["material"], row["skill"]
        independent = row["outcome"] == "independent"
        streak[key] = streak[key] + 1 if independent else 0
        days = min(60, 2 ** min(streak[key], 6)) if independent else 1
        when = datetime.fromisoformat(row["occurred"]) + timedelta(days=days)
        if when <= now:
            targets[key] = when
        else:
            targets.pop(key, None)
    ranked = sorted(targets, key=lambda k: (k[0] not in scene["targets"], targets[k], k))
    return [{"material": material.get(db, k[0]), "skill": k[1], "due": targets[k].isoformat()}
            for k in ranked[:2]]
