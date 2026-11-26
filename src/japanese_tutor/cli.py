import argparse
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from .contracts import TOOLS
from .curriculum import SCENES
from .lessons import call
from .mcp_server import serve
from .storage import connect, copy_database, default_path


def cli():
    parser = argparse.ArgumentParser(prog="japanese-tutor")
    parser.add_argument("--db", type=Path, help="Local learner database")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("start", help="Display the pending exercise")
    resume = commands.add_parser("resume", help="Read the lesson briefing")
    resume.add_argument("--json", action="store_true", help="Print the full agent briefing")
    commands.add_parser("tools", help="Show tool names and input schemas")
    commands.add_parser("scenes", help="List authored scenes")
    commands.add_parser("mcp", help="Start the MCP server on stdio")
    tool = commands.add_parser("call", help="Call an operation with JSON arguments")
    tool.add_argument("operation", choices=TOOLS)
    tool.add_argument("arguments", nargs="?", default="{}", help="JSON object, or - for stdin")
    commands.add_parser("backup").add_argument("destination", type=Path)
    commands.add_parser("restore").add_argument("source", type=Path)
    args = parser.parse_args()
    database = (args.db or default_path()).expanduser().resolve()
    if args.command in ("backup", "restore"):
        if args.command == "backup":
            copy_database(database, args.destination.expanduser().resolve())
        else:
            copy_database(args.source.expanduser().resolve(), database)
        return
    if args.command == "tools":
        result = {k: {"description": v[0], "inputSchema": v[1]} for k, v in TOOLS.items()}
    elif args.command == "scenes":
        result = {k: {"chapter": v["chapter"], "title": v["title"]} for k, v in SCENES.items()}
    else:
        with closing(connect(database)) as db:
            if args.command == "mcp":
                serve(db, sys.stdin, sys.stdout)
                return
            if args.command == "call":
                raw = sys.stdin.read() if args.arguments == "-" else args.arguments
                result = call(db, args.operation, json.loads(raw))
            else:
                result = call(db, "resume_lesson", {})
                if not getattr(args, "json", False):
                    scene, prompt = result["scene"], result["pending"]
                    name = scene["cast"].get(prompt["speaker"], {}).get("name", "Tutor")
                    print(f"{scene['title']}\n{scene['setting']}\n\n{name}: {prompt['text']}")
                    if result["revision"] == 0:
                        print("\nWhat do you think she said? A guess in English is welcome.")
                    return
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    try:
        cli()
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"japanese-tutor: {exc}", file=sys.stderr)
        return 1
    return 0
