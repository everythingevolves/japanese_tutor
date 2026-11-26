"""Create a fictional advanced learner in a new database for agent evaluations."""
import argparse
import json
import sys
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from japanese_tutor.lessons import call
from japanese_tutor.storage import connect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    path = parser.parse_args().database
    path.touch(exist_ok=False)
    with closing(connect(path)) as db:
        steps = json.loads((ROOT / "tests/fixtures/film.json").read_text())
        for name, args in steps:
            if name == "record_turn":
                args["observations"][0]["material"] = bookmark
            result = call(db, name, args)
            if name == "save_material":
                bookmark = result["id"]
        print(call(db, "resume_lesson", {})["pending"]["text"])


if __name__ == "__main__":
    main()
