import hashlib
import json

from .curriculum import MATERIALS, dump


def get(db, key):
    if key in MATERIALS:
        return {"id": key, **MATERIALS[key]}
    row = db.execute("SELECT * FROM saved WHERE id=?", (key,)).fetchone()
    if row:
        return {**dict(row), "source": json.loads(row["source"])}
    raise ValueError(f"Unknown material: {key}")


def find_material(db, query):
    keys = [*MATERIALS, *(r[0] for r in db.execute("SELECT id FROM saved ORDER BY rowid DESC"))]
    matches = []
    for key in keys:
        item = get(db, key)
        if query.casefold() in dump(item).casefold():
            rows = db.execute("""SELECT o.turn_id, o.skill, o.outcome, t.occurred
                FROM observation o JOIN turn t ON t.id=o.turn_id
                WHERE o.material=? ORDER BY t.revision DESC LIMIT 12""", (key,))
            matches.append({**item, "recent_evidence": [dict(r) for r in rows]})
            if len(matches) >= 15:
                break
    return {"materials": matches}


def save_material(db, line, speaker, turn_id=None, source=None):
    if not (source or turn_id):
        raise ValueError("Supply a source or a turn_id")
    if turn_id:
        turn = db.execute("SELECT scene, prompt, request FROM turn WHERE id=?", (turn_id,)).fetchone()
        if not turn:
            raise ValueError("Unknown source turn")
        prompt = json.loads(turn["prompt"])
        response = json.loads(turn["request"])["response"]
        if not ((speaker == prompt["speaker"] and line in prompt["text"])
                or (speaker == "learner" and line in response)):
            raise ValueError("Line and speaker must match the source turn")
        source = {"scene": turn["scene"], **(source or {})}
    payload = dump([line, speaker, turn_id, source])
    key = "saved." + hashlib.sha256(payload.encode()).hexdigest()[:24]
    db.execute("INSERT OR IGNORE INTO saved VALUES (?, ?, ?, ?, ?)",
               (key, line, dump(source), turn_id, speaker))
    return get(db, key)
