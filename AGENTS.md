# Working on the Japanese tutor

## Conduct a lesson

For “Continue lesson”, “Let's try it”, or a reply to a pending exercise, run `./japanese-tutor resume --json` in the checkout. Alternatively use the local MCP tool `resume_lesson`. Use the returned teaching guide, scene, support, revision, and pending prompt. The learner talks to you here. The terminal is the persistence interface.

Present only the learner-facing exercise. On the opening visit ask for their interpretation in English or Japanese. Do not fill in their answer. After a reply, use `record_turn` with a unique turn ID, the returned revision, the actual learner response and your next prompt. Commit before showing that prompt. If the learner asks to save a line or switch formats, use the matching operation. A role only knows facts established with that character. Use the same database across chats.

Run `./japanese-tutor tools` for the contracts and `./japanese-tutor scenes` for scene IDs. Use `./japanese-tutor call NAME -` and a single-quoted heredoc to pass JSON without shell expansion. Use a disposable database for demonstrations, tests, and evaluations.

## Change the system

The Python package lives under `src/japanese_tutor`. Read `content/teaching.md` for pedagogy and `content/*.json` for authored curriculum. Keep content IDs stable across revisions. Both entry points dispatch through `lessons.call` and the contracts in `contracts.py`. Apply new database schemas through numbered SQL migrations. Preserve turn evidence so a revised scheduler can recompute due targets. If a tool signature must change incompatibly, introduce a new operation and retain the older contract for existing agents.

Run `python3 -m unittest discover -s tests -v` from the repository root after changes. For a new model or teaching prompt, also use the scenarios in `evals/README.md`. Keep learner databases out of Git.
