"""A local tools-only MCP server, JSON-RPC over newline-delimited stdio."""
import json
import sys
from contextlib import closing

from .contracts import TOOLS
from .curriculum import dump
from .lessons import call
from .storage import connect

VERSION = "2025-06-18"


def error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(db, message):
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return error(None, -32600, "Invalid request")
    if "id" not in message:
        return None
    rid, method = message["id"], message["method"]
    params = message.get("params", {})
    if type(params) is not dict:
        return error(rid, -32602, "Expected object parameters")
    if method == "initialize":
        result = {"protocolVersion": VERSION, "capabilities": {"tools": {}},
                  "serverInfo": {"name": "japanese-tutor", "version": "0.1.0"},
                  "instructions": "Call resume_lesson first. Read its teaching_guide before presenting the pending prompt."}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [{"name": n, "description": desc, "inputSchema": schema}
                            for n, (desc, schema) in TOOLS.items()]}
    elif method == "tools/call":
        name = params.get("name")
        if not isinstance(name, str) or name not in TOOLS:
            return error(rid, -32602, "Unknown tool")
        try:
            data = call(db, name, params.get("arguments", {}))
            result = {"content": [{"type": "text", "text": dump(data)}], "structuredContent": data}
        except ValueError as exc:
            result = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
    else:
        return error(rid, -32601, "Method not found")
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def serve(db, incoming, outgoing):
    for line in incoming:
        try:
            reply = handle(db, json.loads(line))
        except json.JSONDecodeError:
            reply = error(None, -32700, "Invalid JSON")
        except Exception as exc:
            print(f"MCP error: {exc}", file=sys.stderr)
            reply = error(None, -32603, "Internal server error")
        if reply is not None:
            print(dump(reply), file=outgoing, flush=True)


def main():
    with closing(connect()) as db:
        serve(db, sys.stdin, sys.stdout)


if __name__ == "__main__":
    main()
