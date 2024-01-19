CREATE TABLE IF NOT EXISTS [events] (
   [id] TEXT PRIMARY KEY NOT NULL,
   [date] TEXT NOT NULL,
   [url] TEXT NOT NULL,
   [title] TEXT NOT NULL,
   [session_id] TEXT NOT NULL,
   [country] TEXT,
   [host] TEXT NOT NULL,
   [path] TEXT NOT NULL,
   [query] TEXT,
   [width] INTEGER NOT NULL,
   [height] INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS [session_identifiers] (
    [hash_id] TEXT PRIMARY KEY NOT NULL,
    [session_id] TEXT NOT NULL,
    [expires] INTEGER NOT NULL
)
