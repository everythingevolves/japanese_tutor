CREATE TABLE lesson (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    revision INTEGER NOT NULL,
    activity TEXT NOT NULL DEFAULT 'Continue lesson',
    scene TEXT NOT NULL,
    prompt TEXT NOT NULL,
    support INTEGER NOT NULL CHECK(support BETWEEN 1 AND 5)
);
CREATE TABLE turn (
    id TEXT PRIMARY KEY,
    revision INTEGER NOT NULL UNIQUE,
    occurred TEXT NOT NULL,
    scene TEXT NOT NULL,
    prompt TEXT NOT NULL,
    request TEXT NOT NULL
);
CREATE TABLE observation (
    id INTEGER PRIMARY KEY,
    turn_id TEXT NOT NULL REFERENCES turn(id),
    material TEXT NOT NULL,
    skill TEXT NOT NULL,
    outcome TEXT NOT NULL,
    UNIQUE(turn_id, material, skill)
);
CREATE INDEX observation_target ON observation(material, skill);
CREATE TABLE memory (
    turn_id TEXT NOT NULL REFERENCES turn(id),
    witness TEXT NOT NULL,
    fact TEXT NOT NULL,
    PRIMARY KEY(turn_id, witness, fact)
);
CREATE TABLE saved (
    id TEXT PRIMARY KEY,
    line TEXT NOT NULL,
    source TEXT NOT NULL,
    turn_id TEXT REFERENCES turn(id),
    speaker TEXT NOT NULL
);

CREATE TABLE activity_change (
    id TEXT PRIMARY KEY,
    revision INTEGER NOT NULL,
    request TEXT NOT NULL
);
