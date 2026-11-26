# Japanese immersion tutor

A local lesson engine for a teaching agent. The agent conducts the conversation. Python and SQLite keep the pending question, story, saved language and learning history across chats. Python 3.9 or newer is sufficient. The checkout launcher has no third-party runtime dependencies.

## Try the first lesson

Open a chat with an agent that can use this checkout and say **Continue my Japanese lesson**. In a terminal, `./japanese-tutor start` previews the current exercise and `./japanese-tutor resume --json` shows the agent's full briefing. Reply in the agent chat. The CLI also accepts explicit tool calls for testing and scripted lessons.

Your first visit opens at 美香’s café. Reply in English or Japanese, guess individual words, or ask for a reading. Once you reply, the agent records the exchange and saves its next question. In a new chat, “Continue lesson” picks up at that question.

## Connect an agent

For an MCP client that supports local stdio servers, configure the absolute path to the checkout launcher as the command and `["mcp"]` as the arguments. For example, substitute the real checkout path in this client configuration.

```json
{
  "mcpServers": {
    "japanese-tutor": {
      "command": "/absolute/path/to/japanese_tutor/japanese-tutor",
      "args": ["mcp"]
    }
  }
}
```

The server supports the 2025-06-18 MCP tools protocol. A shell-capable agent can use the same functions through the CLI. All paths below are relative to the checkout.

```sh
./japanese-tutor scenes
./japanese-tutor tools
./japanese-tutor call plan_activity '{"activity":"Listening lesson","playback":false}'
./japanese-tutor call find_material '{"query":"好き"}'
```

| Operation | Purpose |
| --- | --- |
| `resume_lesson` | Read the checkpoint, cast memories, recent exchanges, support, and due targets. |
| `plan_activity` | Preview a scene or lesson format. Includes suggested blocks and required delivery. |
| `start_activity` | Switch the active scene, format, and prompt without creating learning evidence. |
| `record_turn` | Save an actual reply, observations, witnessed facts and next prompt in one transaction. |
| `save_material` | Bookmark exact language with a speaker and either a source turn or external reference. |
| `find_material` | Search by wording, meaning, source, or ID and retrieve recent evidence. |

For a turn bookmark, use the character ID (e.g. `mika`) or `learner` as the speaker. External sources can carry a title, episode or URL, and timestamp in seconds. Successful writes return the committed revision or saved material ID. A repeated identical turn ID returns its original receipt. On a stale revision, resume and reconcile before issuing a new write.

## Curriculum and delivery

Five authored chapters span the neighborhood café, making plans, travel problems, friendships and open discussion of media. Agents can expand the scenes through conversation. Text lessons target 15–25 minutes. Listening plans cover 45 minutes of review, dialogue, sentence variations, shadowing and conversation. Audio delivery and speech input require a voice-capable host. A playback flag describes a client capability. Learning evidence is recorded only after the learner responds to an actual presentation.

## Storage and backups

The checkout defaults to `.local/learner.sqlite3`, ignored by Git. An installed package uses `~/.local/share/japanese-tutor/learner.sqlite3`. To share a specific database across clients, set `JAPANESE_TUTOR_DB` or pass `--db PATH` before a command. Each database tracks one learner.

```sh
./japanese-tutor backup ~/japanese-tutor-backup.sqlite3
./japanese-tutor --db .local/restored.sqlite3 restore ~/japanese-tutor-backup.sqlite3
./japanese-tutor --db .local/restored.sqlite3 resume --json
```

Backup and restore create a new destination and preserve the source. Only publish fictional fixtures and authored content.

## Verify a change

```sh
python3 -m unittest discover -s tests -v
```

Tests use temporary learners and exercise the CLI, MCP server, chapter changes, retries, evidence validation, references and restore. The advanced fixture under `tests/fixtures` models a fictional learner listening to a line and discussing it with a friend in Chapter 5. See `evals/README.md` for teaching evaluations.
