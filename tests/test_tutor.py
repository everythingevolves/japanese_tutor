import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from japanese_tutor import learning
from japanese_tutor.curriculum import SCENES
from japanese_tutor.lessons import call
from japanese_tutor.storage import connect, copy_database


class TutorTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "learner.sqlite3"
        self.db = connect(self.path)
        self.addCleanup(self.db.close)

    def call(self, name, **args):
        return call(self.db, name, args)

    def exchange(self, **changes):
        args = dict(turn_id="intro", revision=0, presented="text", response_mode="typed",
                    response="Good morning. Is this my first time?",
                    observations=[{"material": "first-time", "skill": "written_recognition",
                                   "outcome": "independent"}],
                    next_prompt={"speaker": "mika", "text": "コーヒーは好きですか？"})
        return dict(args, **changes)

    def test_fresh_chat_retry_and_conflict(self):
        self.assertEqual(self.call("resume_lesson")["recent"], [])
        args = self.exchange()
        self.assertEqual(self.call("record_turn", **args), self.call("record_turn", **args))
        with closing(connect(self.path)) as other:
            briefing = call(other, "resume_lesson", {})
            self.assertEqual(briefing["pending"], args["next_prompt"])
            self.assertEqual(briefing["support"], 1)
            self.assertEqual(briefing["scene"]["cast"]["mika"]["memories"], [])
            with self.assertRaisesRegex(ValueError, "Stale"):
                call(other, "record_turn", dict(args, turn_id="another-chat"))
            with self.assertRaisesRegex(ValueError, "different"):
                call(other, "record_turn", dict(args, response="different"))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM observation").fetchone()[0], 1)

    def test_cafe_return_and_scoped_memories(self):
        self.call("record_turn", **self.exchange())
        self.call("record_turn", **self.exchange(turn_id="coffee", revision=1, response="はい、好きです。",
            observations=[], facts=[{"witness":"mika", "fact":"Likes coffee."}], next_scene="weekend",
            next_prompt=SCENES["weekend"]["opening"]))
        self.assertEqual(self.call("resume_lesson")["scene"]["cast"]["yui"]["memories"], [])
        plan = self.call("plan_activity", activity="Continue lesson", scene="cafe.return")
        self.assertEqual(plan["scene"]["cast"]["mika"]["memories"][0]["turn_id"], "coffee")
        switch = dict(change_id="return", revision=2, scene="cafe.return",
                      activity="Continue lesson", prompt=plan["prompt"])
        self.assertEqual(self.call("start_activity", **switch), self.call("start_activity", **switch))
        self.assertEqual(self.call("resume_lesson")["scene"]["id"], "cafe.return")

    def test_atomic_rejection(self):
        for changes in [
            {"observations":[{"material":"first-time","skill":"listening_recognition","outcome":"independent"}]},
            {"facts":[{"witness":"yui","fact":"Secret"}]},
            {"observations":[{"material":"missing","skill":"written_recognition","outcome":"missed"}]},
            {"hint":True}, {"support":0}, {"revision":False}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.call("record_turn", **self.exchange(**changes))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM turn").fetchone()[0], 0)
        self.assertEqual(self.call("resume_lesson")["revision"], 0)

    def test_saved_line_and_review(self):
        self.call("record_turn", **self.exchange())
        fields = dict(line="おはようございます！", speaker="mika", turn_id="intro")
        bookmark = self.call("save_material", **fields)
        self.assertEqual(self.call("save_material", **fields), bookmark)
        self.assertEqual(self.call("find_material", query=bookmark["id"])["materials"][0]["source"]["scene"], "cafe.first")
        with self.assertRaises(ValueError):
            self.call("save_material", **dict(fields, line="A made up line"))
        self.assertEqual(learning.due(self.db, SCENES["cafe.first"]), [])
        due = learning.due(self.db, SCENES["cafe.first"], learning.utcnow() + timedelta(days=3))
        self.assertEqual([d["skill"] for d in due], ["written_recognition"])

    def test_advanced_media_fixture_and_restore(self):
        steps = json.loads((ROOT / "tests/fixtures/film.json").read_text())
        for name, args in steps:
            if name == "record_turn":
                args["observations"][0]["material"] = bookmark["id"]
            result = self.call(name, **args)
            if name == "save_material":
                bookmark = result
        backup = self.path.with_name("backup.db")
        restored = self.path.with_name("restored.db")
        copy_database(self.path, backup)
        copy_database(backup, restored)
        with self.assertRaises(FileExistsError):
            copy_database(backup, restored)
        with closing(connect(restored)) as db:
            state = call(db, "resume_lesson", {})
            self.assertEqual((state["scene"]["chapter"]["number"], state["activity"]), (5, "Listening lesson"))
            self.assertEqual(state["pending"], steps[-1][1]["next_prompt"])
            match = call(db, "find_material", {"query":"河原の約束"})["materials"][0]
            self.assertEqual(match["source"]["timestamp_seconds"], 72)
            self.assertEqual(match["recent_evidence"][0]["skill"], "listening_recognition")

    def test_all_chapters_and_shortcuts(self):
        for scene in SCENES:
            self.assertEqual(self.call("plan_activity", scene=scene, activity="Free conversation")["scene"]["id"], scene)
        plan = self.call("plan_activity", activity="Listening lesson")
        self.assertEqual(plan["delivery"], "playback_required")
        self.assertEqual(sum(block["minutes"] for block in plan["blocks"]), 45)
        self.assertEqual(self.call("plan_activity", activity="Listening lesson", playback=True)["delivery"], "audio")

    def test_cli_and_mcp_processes(self):
        cmd = [str(ROOT / "japanese-tutor"), "--db", str(self.path)]
        cli = json.loads(subprocess.check_output(cmd + ["resume", "--json"]))
        requests = [
            {"id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1"}}},
            {"method":"notifications/initialized"},
            {"id":2,"method":"tools/list"},
            {"id":3,"method":"tools/call","params":{"name":"record_turn","arguments":self.exchange()}},
            {"id":4,"method":"tools/call","params":{"name":"resume_lesson"}},
            {"id":5,"method":"tools/call","params":{"name":"record_turn","arguments":{}}}]
        lines = "".join(json.dumps(dict(jsonrpc="2.0", **req)) + "\n" for req in requests)
        output = subprocess.check_output(cmd + ["mcp"], input=lines, text=True)
        replies = [json.loads(line)["result"] for line in output.splitlines()]
        self.assertEqual(replies[0]["protocolVersion"], "2025-06-18")
        self.assertIn("record_turn", [t["name"] for t in replies[1]["tools"]])
        self.assertEqual(cli["revision"], 0)
        self.assertEqual(replies[2]["structuredContent"]["revision"], 1)
        same = json.loads(subprocess.check_output(cmd + ["resume", "--json"]))
        self.assertEqual(same, replies[3]["structuredContent"])
        self.assertTrue(replies[4]["isError"])


if __name__ == "__main__":
    unittest.main()
