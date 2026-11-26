import json
from pathlib import Path

CONTENT = Path(__file__).with_name("content")


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def load(name):
    return json.loads((CONTENT / (name + ".json")).read_text(encoding="utf-8"))


SCENES = load("scenes")
CHAPTERS = load("chapters")
CHARACTERS = load("characters")
MATERIALS = load("materials")
ACTIVITIES = load("activities")
TEACHING = (CONTENT / "teaching.md").read_text(encoding="utf-8")
for scene in SCENES.values():
    if (scene["chapter"] not in {c["number"] for c in CHAPTERS}
            or scene["opening"]["speaker"] not in scene["cast"]
            or set(scene["cast"]) - CHARACTERS.keys()
            or set(scene["targets"]) - MATERIALS.keys()):
        raise ValueError(f"Invalid scene: {scene['title']}")
for item in MATERIALS.values():
    if item["scene"] not in SCENES:
        raise ValueError(f"Unknown source scene: {item['scene']}")
