from .curriculum import CHARACTERS


def cast_briefing(db, scene):
    cast = {}
    for witness in scene["cast"]:
        memories = db.execute("""SELECT m.fact, m.turn_id FROM memory m
            JOIN turn t ON t.id=m.turn_id WHERE witness=?
            ORDER BY t.revision DESC LIMIT 20""", (witness,))
        cast[witness] = {**CHARACTERS[witness], "memories": [dict(r) for r in memories]}
    return cast


def remember(db, turn_id, scene, facts):
    for entry in facts:
        if entry["witness"] not in scene["cast"]:
            raise ValueError("Witness was absent from the exchange")
        db.execute("INSERT INTO memory VALUES (?, ?, ?)", (turn_id, entry["witness"], entry["fact"]))
