"""Application operations. CLI and MCP both dispatch here."""
import json
import sqlite3

from . import learning, material, story
from .contracts import TOOLS, validate
from .curriculum import ACTIVITIES, CHAPTERS, MATERIALS, SCENES, TEACHING, dump
from .storage import transaction


def scene_briefing(db, scene_id):
    scene = SCENES[scene_id]
    return {"id": scene_id, "title": scene["title"], "chapter": CHAPTERS[scene["chapter"] - 1],
            "setting": scene["setting"], "cast": story.cast_briefing(db, scene),
            "targets": [{"id": k, **MATERIALS[k]} for k in scene["targets"]]}


def resume_lesson(db):
    row = db.execute("SELECT * FROM lesson WHERE id=1").fetchone()
    scene = row["scene"]
    recent = db.execute("""SELECT id, prompt, request FROM turn WHERE scene=?
        ORDER BY revision DESC LIMIT 3""", (scene,)).fetchall()
    return {"revision": row["revision"], "support": row["support"], "activity": row["activity"],
            "scene": scene_briefing(db, scene), "pending": json.loads(row["prompt"]),
            "recent": [{"turn_id": r["id"], "prompt": json.loads(r["prompt"]),
                        "response": json.loads(r["request"])["response"]} for r in reversed(recent)],
            "review": learning.due(db, SCENES[scene]), "teaching_guide": TEACHING}


def plan_activity(db, activity, scene=None, playback=False):
    current = db.execute("SELECT scene, prompt, support FROM lesson WHERE id=1").fetchone()
    scene = scene or current["scene"]
    audio = activity == "Listening lesson"
    bookmarks = db.execute("SELECT id, line, source FROM saved ORDER BY rowid DESC LIMIT 3")
    return {"activity": activity, "scene": scene_briefing(db, scene),
            "prompt": json.loads(current["prompt"]) if scene == current["scene"] else SCENES[scene]["opening"],
            "support": current["support"], "blocks": [{"task": b, "minutes": m} for b, m in ACTIVITIES[activity]],
            "delivery": "audio" if audio and playback else "playback_required" if audio else "text",
            "review": learning.due(db, SCENES[scene]),
            "recent_bookmarks": [{"id": r["id"], "line": r["line"], "source": json.loads(r["source"])}
                                 for r in bookmarks]}


def start_activity(db, change_id, revision, activity, scene, prompt):
    encoded = dump([revision, activity, scene, prompt])
    previous = db.execute("SELECT revision, request FROM activity_change WHERE id=?", (change_id,)).fetchone()
    if previous:
        if previous["request"] != encoded:
            raise ValueError("Change ID already used with different arguments")
        return {"revision": previous["revision"]}
    if prompt["speaker"] not in ["tutor", *SCENES[scene]["cast"]]:
        raise ValueError("Speaker is absent from the chosen scene")
    changed = db.execute("""UPDATE lesson SET revision=revision+1, activity=?, scene=?, prompt=?
        WHERE id=1 AND revision=?""", (activity, scene, dump(prompt), revision))
    if not changed.rowcount:
        raise ValueError("Stale revision. Resume before switching activity.")
    db.execute("INSERT INTO activity_change VALUES (?, ?, ?)", (change_id, revision + 1, encoded))
    return {"revision": revision + 1}


def record_turn(db, **args):
    turn_id = args["turn_id"]
    encoded = dump(args)
    with transaction(db):
        previous = db.execute("SELECT revision, request FROM turn WHERE id=?", (turn_id,)).fetchone()
        if previous:
            if previous["request"] != encoded:
                raise ValueError("Turn ID already used with different arguments")
            return {"turn_id": turn_id, "revision": previous["revision"]}
        current = db.execute("SELECT * FROM lesson WHERE id=1").fetchone()
        if args["revision"] != current["revision"]:
            raise ValueError("Stale revision. Resume the lesson and reconcile the new checkpoint.")
        next_scene = args.get("next_scene", current["scene"])
        prompt = args["next_prompt"]
        if prompt["speaker"] not in ["tutor", *SCENES[next_scene]["cast"]]:
            raise ValueError("Next speaker is absent from the next scene")
        revision = current["revision"] + 1
        db.execute("INSERT INTO turn VALUES (?,?,?,?,?,?)",
                   (turn_id, revision, learning.utcnow().isoformat(), current["scene"], current["prompt"], encoded))
        learning.observe(db, args)
        story.remember(db, turn_id, SCENES[current["scene"]], args.get("facts", []))
        db.execute("UPDATE lesson SET revision=?, scene=?, prompt=?, support=? WHERE id=1",
                   (revision, next_scene, dump(prompt), args.get("support", current["support"])))
        return {"turn_id": turn_id, "revision": revision}


OPERATIONS = {"start_activity": start_activity, "resume_lesson": resume_lesson, "plan_activity": plan_activity,
              "record_turn": record_turn, "find_material": material.find_material,
              "save_material": material.save_material}


def call(db, name, arguments):
    if name not in TOOLS:
        raise ValueError(f"Unknown operation: {name}")
    validate(arguments, TOOLS[name][1])
    try:
        if name == "record_turn":
            return record_turn(db, **arguments)
        with transaction(db):
            return OPERATIONS[name](db, **arguments)
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"Conflicting or repeated lesson data: {exc}") from exc
