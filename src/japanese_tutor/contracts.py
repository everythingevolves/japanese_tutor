"""Tool contracts shared by MCP discovery, the CLI and input validation."""
from .curriculum import ACTIVITIES, CHARACTERS, SCENES


def obj(fields, required=()):
    return {"type": "object", "properties": fields, "required": list(required),
            "additionalProperties": False}


def string(description="", choices=None):
    schema = {"type": "string", "minLength": 1, "maxLength": 12000, "description": description}
    if choices is not None:
        schema["enum"] = list(choices)
    return schema


def integer(low, high):
    return {"type": "integer", "minimum": low, "maximum": high}


def array(items):
    return {"type": "array", "items": items, "maxItems": 50}


def flag():
    return {"type": "boolean"}


SKILLS = ["written_recognition", "listening_recognition", "independent_recall",
          "grammar_comprehension", "active_grammar"]
PROMPT = obj({"speaker": string(choices=[*CHARACTERS, "tutor"]),
              "text": string("Exact next utterance or exercise.")}, ["speaker", "text"])
OBSERVATION = obj({"material": string("Material ID from resume, find or save."),
                   "skill": string(choices=SKILLS),
                   "outcome": string(choices=["independent", "assisted", "missed"])},
                  ["material", "skill", "outcome"])
FACT = obj({"witness": string("Character who learned this fact.", CHARACTERS),
            "fact": string("Established event, preference or plan.")}, ["witness", "fact"])
SOURCE = obj({"title": string(), "timestamp_seconds": integer(0, 9999999),
              "locator": string("Episode, page or URL.")}, ["title"])
TOOLS = {
    "resume_lesson": ("Resume the exact pending prompt, with scoped memories, recent exchanges, teaching guidance and review targets.", obj({})),
    "plan_activity": ("Plan a lesson using the current checkpoint. Preview another scene without advancing it.", obj({
        "activity": string(choices=ACTIVITIES), "scene": string(choices=SCENES),
        "playback": flag()}, ["activity"])),
    "start_activity": ("Checkpoint a chosen activity or scene before asking its first question. Use to switch modes without inventing a learner reply.", obj({
        "change_id": string(), "revision": integer(0, 2147483647),
        "activity": string(choices=ACTIVITIES), "scene": string(choices=SCENES),
        "prompt": PROMPT}, ["change_id", "revision", "activity", "scene", "prompt"])),
    "find_material": ("Search words, source references and saved lines, or look up an exact material ID with evidence.", obj({"query": string()}, ["query"])),
    "save_material": ("Bookmark an exact line with its speaker and an existing turn or external source. Returns its stable material ID.", obj({
        "line": string(), "speaker": string(), "turn_id": string(), "source": SOURCE},
        ["line", "speaker"])),
    "record_turn": ("Commit a learner reply and its next prompt atomically. Retry with identical arguments. On stale revision, resume.", obj({
        "turn_id": string("New unique ID per exchange."), "revision": integer(0, 2147483647),
        "response": string("Learner's actual reply."),
        "presented": string(choices=["text", "audio"]),
        "response_mode": string(choices=["typed", "spoken"]),
        "japanese_production": flag(), "hint": flag(), "transcript_revealed": flag(),
        "replays": integer(0, 1000), "observations": array(OBSERVATION), "facts": array(FACT),
        "next_scene": string(choices=SCENES), "next_prompt": PROMPT, "support": integer(1, 5)},
        ["turn_id", "revision", "response", "presented", "response_mode", "next_prompt"]))
}


def validate(value, schema, path="arguments"):
    kind = schema["type"]
    expected = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool}[kind]
    if type(value) is not expected:
        raise ValueError(f"{path} must be {kind}")
    if kind == "object":
        fields = schema["properties"]
        missing = set(schema["required"]) - value.keys()
        unknown = value.keys() - fields
        if missing or unknown:
            raise ValueError(f"{path}: missing {sorted(missing)}, unknown {sorted(unknown)}")
        for key, item in value.items():
            validate(item, fields[key], f"{path}.{key}")
    elif kind == "array":
        if len(value) > schema["maxItems"]:
            raise ValueError(f"{path} has too many entries")
        for i, item in enumerate(value):
            validate(item, schema["items"], f"{path}[{i}]")
    elif kind == "integer" and not schema["minimum"] <= value <= schema["maximum"]:
        raise ValueError(f"{path} outside allowed range")
    elif kind == "string":
        if not value.strip() or len(value) > schema["maxLength"] or ("enum" in schema and value not in schema["enum"]):
            raise ValueError(f"Invalid {path}")
