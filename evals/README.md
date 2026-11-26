# Evaluating a teaching agent

Use a separate temporary database for each scenario. Point the agent's launcher or MCP process at it via JAPANESE_TUTOR_DB. Run each scenario in a fresh chat and preserve the model name, teaching guide version, transcript and observed tool results when comparing teaching changes.

| Scenario | Learner actions | Inspect |
| --- | --- | --- |
| New learner | Continue the lesson. Guess only “good morning.” Ask for help on the remaining question. | Agent gives you a chance to try, recognizes partial understanding and explains 初めて in context. Check which item and support were recorded. |
| Returning to the café | Tell 美香 in character that you like coffee. Visit the station, then return in a new chat. | 美香 can recall the preference. The station attendant has no such memory. The pending prompt survives. |
| Saturday invitation | Ask to practice making plans. Decline Saturday and propose Sunday. Ask the friend about the plan after a handoff. | Only the agreed details are recalled. An invitation and a confirmed plan are different events. |
| Pattern discovery | Ask for a grammar deep dive about を. Try the pattern with an unfamiliar verb. | Agent presents examples, waits for your inference and checks transfer with a fresh combination. |
| Advanced listening | Load the fictional Chapter 5 scenario using the command below. Resume, ask to revisit the saved line, then discuss whether the characters will meet again. | Agent finds the timestamp and keeps the conversation natural. It distinguishes audio, transcript-assisted comprehension and spontaneous production. |

To load the advanced example, select an unused path and run `python3 evals/load_film.py /path/to/new.sqlite3`. The fixture simulates a prior listening exchange. It contains no recording.

Score each session from 0 (absent), 1 (partial), or 2 (consistent) on four dimensions: level-appropriate Japanese and scaffolding, meaningful learner choice, evidence grounded in actual responses, and continuity of character knowledge and lesson state. Record one specific example for each score. For database invariants, run the automated tests as well.
