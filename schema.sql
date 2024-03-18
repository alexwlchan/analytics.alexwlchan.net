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
   [referrer] TEXT,
   [normalised_referrer] TEXT,
   [is_bot] BOOLEAN NOT NULL,
   [is_me] BOOLEAN NOT NULL
);
